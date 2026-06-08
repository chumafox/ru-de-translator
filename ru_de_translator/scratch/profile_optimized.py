"""Test optimized TTS with producer-consumer pipeline.

Problem: stream.write() blocks for the duration of each audio chunk,
serializing generation and playback. 

Solution: Generate in one thread, play in another via a queue.
This lets generation run ahead while playback is blocking.
"""
import time
import queue
import threading
import numpy as np

def profile_optimized():
    t0 = time.perf_counter()
    from mlx_audio.tts.utils import load
    import pyaudio
    t_import = time.perf_counter() - t0
    print(f"[1] Import: {t_import*1000:.1f} ms")

    t0 = time.perf_counter()
    model = load("mlx-community/Qwen3-TTS-12Hz-1.7B-Base-bf16")
    t_load = time.perf_counter() - t0
    print(f"[2] Model load: {t_load*1000:.1f} ms")

    text = "Guten Morgen."
    sample_rate = 24000
    print(f"\nGenerating (optimized pipeline): '{text}'")

    audio_queue = queue.Queue(maxsize=8)
    playback_done = threading.Event()
    total_played_samples = [0]
    play_start_time = [None]

    def player_thread():
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paFloat32, channels=1,
                        rate=sample_rate, output=True)
        while True:
            data = audio_queue.get()
            if data is None:
                break
            if play_start_time[0] is None:
                play_start_time[0] = time.perf_counter()
            stream.write(data)
            total_played_samples[0] += len(data) // 4  # float32 = 4 bytes
        stream.stop_stream()
        stream.close()
        p.terminate()
        playback_done.set()

    player = threading.Thread(target=player_thread, daemon=True)
    player.start()

    t_gen_start = time.perf_counter()
    ttfb = None
    chunk_count = 0
    gen_times = []

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
            print(f"[3] TTFB: {ttfb*1000:.1f} ms")

        if result.audio is not None:
            audio_data = np.array(result.audio, copy=False).astype(np.float32)
            # Non-blocking put into queue (queue has capacity 8)
            audio_queue.put(audio_data.tobytes())
            gen_times.append(time.perf_counter() - t_gen_start)
            chunk_count += 1

    t_gen_done = time.perf_counter()
    gen_total = t_gen_done - t_gen_start

    # Signal end of audio
    audio_queue.put(None)
    # Wait for playback to finish
    player.join()
    t_all_done = time.perf_counter()
    
    total_time = t_all_done - t_gen_start
    audio_duration = total_played_samples[0] / sample_rate

    print(f"\n--- Summary (Optimized) ---")
    print(f"Chunks generated: {chunk_count}")
    print(f"Audio duration: {audio_duration:.2f}s")
    print(f"TTFB: {ttfb*1000:.1f}ms")
    print(f"Generation finished at: {gen_total*1000:.1f}ms")
    print(f"Total (gen + playback drain): {total_time*1000:.1f}ms")
    print(f"RTF: {total_time / audio_duration:.2f}x")

if __name__ == "__main__":
    profile_optimized()
