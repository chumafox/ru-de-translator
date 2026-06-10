import numpy as np
import sounddevice as sd
import time


def test_sine():
    sample_rate = 24000
    duration = 2.0
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)

    # Generate 440 Hz sine wave (A4)
    audio_data = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

    print("Playing 1D sine wave via sounddevice...")
    stream = sd.OutputStream(samplerate=sample_rate, channels=1, dtype="float32")
    stream.start()
    stream.write(audio_data)
    stream.stop()
    stream.close()

    time.sleep(0.5)

    print("Playing 2D sine wave via sounddevice...")
    stream = sd.OutputStream(samplerate=sample_rate, channels=1, dtype="float32")
    stream.start()
    stream.write(audio_data.reshape(-1, 1))
    stream.stop()
    stream.close()

    print("Sine wave test done.")


if __name__ == "__main__":
    test_sine()
