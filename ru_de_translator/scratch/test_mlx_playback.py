import time
import sys

from mlx_audio.tts.utils import load
import sounddevice as sd
import numpy as np


def test_playback():
    print("Loading model...")
    model = load("mlx-community/Qwen3-TTS-12Hz-1.7B-Base-bf16")
    print("Model loaded.")

    text = "Guten Tag! Das ist ein Test der lokalen Text-zu-Sprache-Engine. Ich hoffe, Sie können mich gut hören."
    print(f"Generating for text: {text}")

    sample_rate = 24000
    # Start the sounddevice output stream
    stream = sd.OutputStream(samplerate=sample_rate, channels=1, dtype="float32")
    stream.start()

    try:
        t0 = time.perf_counter()
        first_chunk = True

        for result in model.generate(
            text=text,
            voice="Chelsie",
            temperature=0.9,
            stream=True,
            streaming_interval=0.32,
        ):
            if first_chunk:
                ttfb = time.perf_counter() - t0
                print(f"TTFB: {ttfb * 1000:.1f}ms")
                first_chunk = False

            if result.audio is not None:
                audio_data = np.array(result.audio, copy=False)
                stream.write(audio_data)
                sys.stdout.write(".")
                sys.stdout.flush()

        print("\nFinished generation.")
    finally:
        # Stop and close the stream
        stream.stop()
        stream.close()


if __name__ == "__main__":
    test_playback()
