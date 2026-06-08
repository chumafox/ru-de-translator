import torch
import soundfile as sf
from qwen_tts import Qwen3TTSModel
import time

def test():
    print("Loading model...")
    t0 = time.time()
    # Using the smaller 0.6B model for speed on CPU/MPS
    model = Qwen3TTSModel.from_pretrained(
        "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice", 
        device_map="cpu", 
        dtype=torch.float32
    )
    t1 = time.time()
    print(f"Model loaded in {t1-t0:.2f}s")
    
    print("Generating speech...")
    wavs, sr = model.generate_custom_voice(
        text="Ich liebe es, jeden Tag in Python zu programmieren.",
        language="German",
        speaker="default"
    )
    t2 = time.time()
    print(f"Speech generated in {t2-t1:.2f}s")
    
    sf.write("output.wav", wavs[0], sr)
    print("Saved to output.wav")

if __name__ == "__main__":
    test()
