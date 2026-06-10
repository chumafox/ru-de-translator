import pyaudio
import numpy as np


def test_pyaudio():
    print("Testing pyaudio...")
    sample_rate = 24000
    duration = 2.0
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)

    audio_data = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paFloat32, channels=1, rate=sample_rate, output=True)

    stream.write(audio_data.tobytes())
    stream.stop_stream()
    stream.close()
    p.terminate()
    print("PyAudio test done.")


if __name__ == "__main__":
    test_pyaudio()
