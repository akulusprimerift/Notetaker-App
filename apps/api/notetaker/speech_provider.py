"""Local-only speech adapter. Provision models separately; inference never downloads."""
import hashlib
import io
import math
import wave
from pathlib import Path
from time import perf_counter


class SpeechFailure(Exception):
    def __init__(self, code, retryable=True):
        super().__init__(code)
        self.code, self.retryable = code, retryable


def owned_words(segments, window, rate):
    """Half-open ownership by word midpoint removes context overlap without text deduplication."""
    output = []
    for segment in segments:
        words = []
        for word in segment.words or []:
            if not all(math.isfinite(v) for v in (word.start, word.end, word.probability)):
                raise SpeechFailure('speech_output_invalid', False)
            start = window.context_start + round(word.start*rate)
            end = window.context_start + round(word.end*rate)
            if end <= start: continue
            if not window.context_start <= start < end <= window.context_end+rate//10:
                raise SpeechFailure('speech_output_invalid', False)
            middle = (start+end)/2
            if window.core_start <= middle < window.core_end:
                words.append((word.word, max(start,window.core_start), min(end,window.core_end),float(word.probability)))
        if words:
            text = ''.join(w[0] for w in words).strip()
            if not text: continue
            output.append({'text':text,'start_sample':words[0][1],'end_sample':words[-1][2],
                'confidence':{'kind':'uncalibrated_score','value':sum(w[3] for w in words)/len(words)}})
    return output


def validate_result(result, window):
    if result.get('outcome') not in ('speech','silence','uncertain') or not isinstance(result.get('segments'),list):
        raise SpeechFailure('speech_output_invalid',False)
    segments = result['segments']
    if len(segments)>1000 or (result['outcome']=='speech' and not segments) or (result['outcome']=='silence' and segments):
        raise SpeechFailure('speech_output_invalid',False)
    previous = window.core_start
    for segment in segments:
        start,end=segment.get('start_sample'),segment.get('end_sample')
        text=segment.get('text')
        confidence=segment.get('confidence',{})
        value=confidence.get('value')
        if (type(start) is not int or type(end) is not int or not previous<=start<end<=window.core_end
            or not isinstance(text,str) or not text.strip() or len(text)>12000
            or confidence.get('kind') not in ('unavailable','uncalibrated_score')
            or (confidence.get('kind')=='unavailable' and value is not None)
            or (confidence.get('kind')=='uncalibrated_score' and (type(value) not in (int,float) or not math.isfinite(value) or not 0<=value<=1))):
            raise SpeechFailure('speech_output_invalid',False)
        previous=end
    return result


class WhisperProvider:
    def __init__(self, settings):
        self.settings=settings
        self.model=None

    def load(self):
        path=Path(self.settings.speech_model_path)
        if not all((path/name).is_file() for name in ('model.bin','config.json','tokenizer.json')):
            raise SpeechFailure('model_unavailable')
        if self.model is None:
            from faster_whisper import WhisperModel
            try:
                self.model=WhisperModel(str(path.resolve()), device='cpu', compute_type='int8',
                    cpu_threads=self.settings.speech_threads, num_workers=1, local_files_only=True)
                with (path/'model.bin').open('rb') as model_file:
                    digest=hashlib.file_digest(model_file,'sha256').hexdigest()
                import faster_whisper, ctranslate2
                self.metadata={'provider':'faster-whisper','version':faster_whisper.__version__,
                    'runtime_version':ctranslate2.__version__,'model_sha256':digest,
                    'device':'cpu','compute_type':'int8','threads':self.settings.speech_threads,
                    'language':'en','beam_size':5,'word_timestamps':True,'vad_filter':True,
                    'condition_on_previous_text':False}
            except Exception as exc:
                raise SpeechFailure('model_unavailable') from exc

    def transcribe(self, audio, window, rate, on_preview=None):
        started=perf_counter(); self.load()
        try:
            segments,_=self.model.transcribe(io.BytesIO(audio),language='en',beam_size=5,
                temperature=0,word_timestamps=True,vad_filter=True,condition_on_previous_text=False)
            selected=[]
            for segment in segments:
                selected.extend(owned_words([segment],window,rate))
                if on_preview and selected:
                    on_preview('\n'.join(part['text'] for part in selected))
        except SpeechFailure: raise
        except Exception as exc: raise SpeechFailure('speech_inference_failed') from exc
        with wave.open(io.BytesIO(audio),'rb') as wav:
            pcm=wav.readframes(wav.getnframes())
        import array,sys
        amplitudes=array.array('h',pcm)
        if sys.byteorder!='little':amplitudes.byteswap()
        seams=[cut for cut in (window.core_start,window.core_end) if window.context_start<cut<window.context_end]
        boundary_review=any(max((abs(v) for v in amplitudes[max(0,cut-window.context_start-rate//50):
            min(len(amplitudes),cut-window.context_start+rate//50)]),default=0)>64 for cut in seams)
        # Only digital silence is asserted here. VAD rejection of noise/quiet speech is uncertain.
        outcome='speech' if selected else 'silence' if not any(pcm) else 'uncertain'
        if boundary_review or any(s['confidence']['value']<0.6 for s in selected): outcome='uncertain'
        return validate_result({'outcome':outcome,'segments':selected,
            'metadata':{**self.metadata,'elapsed_seconds':round(perf_counter()-started,3),
                'boundary_review':boundary_review,'window_policy':
                    'live-6s-core-2s-context-v2' if getattr(window, 'live', False) else 'pause-aware-24s-core-2s-context-v1',
                'audio_seconds':(window.context_end-window.context_start)/rate}},window)
