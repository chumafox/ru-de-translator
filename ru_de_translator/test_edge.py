import asyncio
from tts import TTSEngine


async def test_tts():
    print("Initializing Edge TTS...")
    engine = TTSEngine({"tts_provider": "edge_tts"})
    print("Testing Edge TTS playback through SOCKS5 proxy...")
    await engine.speak("Wie kann ich dahin kommen?")
    print("Audio should have played successfully!")


if __name__ == "__main__":
    asyncio.run(test_tts())
