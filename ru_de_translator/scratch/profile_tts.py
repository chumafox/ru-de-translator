"""Detailed profiling of the TTS pipeline to find bottlenecks."""
import time
import sys
import numpy as np

def profile_tts():
    # Step 1: Import timing
    t0 = time.perf_counter()
    from mlx_audio.tts.utils import load
    import pyaudio
    t_import = time.perf_counter() - t0
    print(f"[1] Import mlx_audio + pyaudio: {t_import*1000:.1f} ms")

    # Step 2: Model load timing
    t0 = time.perf_counter()
    model = load("mlx-community/Qwen3-TTS-12Hz-1.7B-Base-bf16")
    t_load = time.perf_counter() - t0
    print(f"[2] Model load (cold): {t_load*1000:.1f} ms")

    # Step 3: PyAudio init timing
    t0 = time.perf_counter()
    p = pyaudio.PyAudio()
    sample_rate = 24000
    stream = p.open(format=pyaudio.paFloat32, channels=1, rate=sample_rate, output=True)
    t_pyaudio = time.perf_counter() - t0
    print(f"[3] PyAudio init + open stream: {t_pyaudio*1000:.1f} ms")

    text = "Guten Morgen."
    print(f"\nGenerating: '{text}'")

    # Step 4: Generation + streaming playback
    t_gen_start = time.perf_counter()
    ttfb = None
    chunk_count = 0
    total_samples = 0
    chunk_times = []

    for result in model.generate(
        text=text,
        voice="Chelsie",
        temperature=0.9,
        stream=True,
        streaming_interval=0.32
    ):
        t_chunk = time.perf_counter()
        if ttfb is None:
            ttfb = t_chunk - t_gen_start
            print(f"[4] TTFB (first chunk): {ttfb*1000:.1f} ms")

        if result.audio is not None:
            audio_data = np.array(result.audio, copy=False).astype(np.float32)
            samples = len(audio_data)
            total_samples += samples
            
            t_write_start = time.perf_counter()
            stream.write(audio_data.tobytes())
            t_write = time.perf_counter() - t_write_start
            
            chunk_times.append({
                'chunk': chunk_count,
                'samples': samples,
                'duration_s': samples / sample_rate,
                'write_ms': t_write * 1000,
                'elapsed_ms': (t_chunk - t_gen_start) * 1000,
            })
            chunk_count += 1

    t_gen_total = time.perf_counter() - t_gen_start
    
    # Step 5: Close
    t0 = time.perf_counter()
    stream.stop_stream()
    stream.close()
    p.terminate()
    t_close = time.perf_counter() - t0

    total_audio_duration = total_samples / sample_rate
    
    print(f"\n--- Chunk Details ---")
    for c in chunk_times:
        print(f"  Chunk {c['chunk']}: {c['samples']} samples ({c['duration_s']*1000:.0f}ms audio), "
              f"write blocked {c['write_ms']:.1f}ms, elapsed {c['elapsed_ms']:.0f}ms")

    print(f"\n--- Summary ---")
    print(f"Total chunks: {chunk_count}")
    print(f"Total samples: {total_samples}")
    print(f"Total audio duration: {total_audio_duration:.2f}s")
    print(f"TTFB: {ttfb*1000:.1f}ms")
    print(f"Generation+playback: {t_gen_total*1000:.1f}ms")
    print(f"Stream close: {t_close*1000:.1f}ms")
    print(f"RTF (gen+play / audio): {t_gen_total / total_audio_duration:.2f}x")
    
    total_write_time = sum(c['write_ms'] for c in chunk_times)
    print(f"Total stream.write() time: {total_write_time:.1f}ms")
    print(f"Time NOT in write (pure generation): {t_gen_total*1000 - total_write_time:.1f}ms")

if __name__ == "__main__":
    profile_tts()
