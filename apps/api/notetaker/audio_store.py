"""Private verified audio files beside the SQLite library."""
from .local_audio_store import LocalAudioStore


class AudioStore(LocalAudioStore):
    def __init__(self, settings):
        super().__init__(settings.audio_directory)
