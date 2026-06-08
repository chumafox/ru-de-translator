from mlx_audio.tts.utils import load
import numpy as np

def test():
    model = load("mlx-community/Qwen3-TTS-12Hz-1.7B-Base-bf16")
    gen = model.generate("Hallo, Welt!", stream=True)
    
    for i, res in enumerate(gen):
        if res.audio is not None:
            arr = np.array(res.audio, copy=False)
            print(f"Chunk {i}: dtype={arr.dtype}, shape={arr.shape}, min={arr.min()}, max={arr.max()}")
            break

if __name__ == "__main__":
    test()
