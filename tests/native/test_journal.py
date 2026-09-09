import pytest
from notetaker_native.journal import Journal


def test_restart_retains_unacknowledged_audio_and_fences_bad_receipts(tmp_path):
    path = tmp_path/'journal.db'
    journal = Journal(path)
    journal.start('lecture', {'id':'run', 'capture_epoch':3, 'sample_rate':16000}, 'grant')
    first = journal.append('run', b'\0\0'*16000)
    second = journal.append('run', b'\1\0'*123)
    restored = Journal(path)
    assert len(restored.pending('run')) == 2
    for key in first:
        changed = {**first, 'storage_state':'verified', key:None}
        with pytest.raises(RuntimeError, match='retained'):
            restored.acknowledge(first, changed)
    assert len(restored.pending('run')) == 2
    restored.acknowledge(first, {**first, 'storage_state':'verified'})
    assert [i for i,_ in restored.pending('run')] == [second]
    assert restored.seal('run')['final_sample_count'] == 16123
    restored.gap('run','microphone_lost')
    assert Journal(path).seal('run')['gaps'] == [{'reason':'microphone_lost','after_sample':16123,'unknown_extent':True}]
    restored.stop('run')
    with pytest.raises(RuntimeError, match='closed'):
        restored.append('run', b'\0\0')
    restored.purge('lecture')
    assert restored.pending('run') == [] and restored.runs() == []
