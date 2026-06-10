import asyncio
import logging
import subprocess

logging.basicConfig(level=logging.DEBUG)
from ru_de_translator.tts import TTSEngine


async def test():
    tts = TTSEngine({"tts_provider": "edge_tts"})
    print("Speaking...")
    await tts.speak("Eins, zwei, drei")
    print("Practicing...")

    # Manually mimic what practice does but capture stderr
    for i in range(3):
        print(f"Play {i + 1}")
        proc = subprocess.Popen(
            ["ffplay", "-i", "pipe:0", "-nodisp", "-autoexit"],
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
        )
        for chunk in tts._last_audio_chunks:
            proc.stdin.write(chunk)
        proc.stdin.close()
        stderr = proc.stderr.read()
        proc.wait()
        if b"Invalid" in stderr or b"Error" in stderr:
            print(f"Error in {i + 1}:", stderr.decode())
        else:
            print(f"Success in {i + 1}")


asyncio.run(test())
