import miniaudio
import numpy as np
import time

def test_miniaudio():
    print("Testing miniaudio...")
    sample_rate = 24000
    duration = 2.0
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    
    # Generate 440 Hz sine wave
    audio_data = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    
    device = miniaudio.PlaybackDevice(
        sample_rate=sample_rate, 
        nchannels=1, 
        output_format=miniaudio.SampleFormat.FLOAT32
    )
    
    device.start()
    device.send(audio_data.tobytes())
    time.sleep(duration + 0.1)
    device.close()
    print("Miniaudio test done.")

if __name__ == "__main__":
    test_miniaudio()
