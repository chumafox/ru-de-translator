import pytest

import ru_de_translator.tts as tts_module
from ru_de_translator.tts import TTSEngine


class FakeStdin:
    def __init__(self):
        self.data = bytearray()
        self.closed = False

    def write(self, data):
        self.data.extend(data)

    def flush(self):
        pass

    def close(self):
        self.closed = True


class FakeProcess:
    def __init__(self):
        self.stdin = FakeStdin()

    def poll(self):
        return 0 if self.stdin.closed else None

    def terminate(self):
        self.stdin.close()

    def kill(self):
        self.stdin.close()


@pytest.mark.asyncio
async def test_edge_audio_is_reused_from_lru_cache(monkeypatch):
    synthesis_count = 0
    processes = []

    class FakeCommunicate:
        def __init__(self, text, voice):
            nonlocal synthesis_count
            synthesis_count += 1

        async def stream(self):
            yield {"type": "audio", "data": b"mp3-data"}

    def spawn():
        process = FakeProcess()
        processes.append(process)
        return process

    monkeypatch.setattr(tts_module.edge_tts, "Communicate", FakeCommunicate)
    monkeypatch.setattr(TTSEngine, "_spawn_ffplay_mp3", staticmethod(spawn))

    engine = TTSEngine({"tts_provider": "edge_tts", "edge_voice": "test-voice"})
    await engine.speak("Hallo")
    await engine.speak("Hallo")

    assert synthesis_count == 1
    assert len(processes) == 2
    assert bytes(processes[1].stdin.data) == b"mp3-data"
    assert engine._last_audio_type == "mp3"
