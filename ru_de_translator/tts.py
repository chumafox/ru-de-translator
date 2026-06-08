"""Text-to-Speech engine for RU-DE Translator.

Uses Qwen3-TTS via MLX with ffplay for audio playback.
Fully local, no cloud dependencies.
"""
import asyncio
import hashlib
import logging
import queue
import subprocess
import threading
from pathlib import Path
from collections import OrderedDict

# Monkey-patch subprocess.Popen to bypass macOS Python 3.13 fds_to_keep bug in threads
_original_popen = subprocess.Popen
class _MonkeyPatchedPopen(_original_popen):
    def __init__(self, *args, **kwargs):
        kwargs["close_fds"] = False
        super().__init__(*args, **kwargs)
subprocess.Popen = _MonkeyPatchedPopen

# Pre-initialize tqdm's multiprocessing lock in the main thread during import.
try:
    from tqdm import tqdm
    tqdm.get_lock()
except Exception:
    pass

import edge_tts
import mlx.core as mx

logger = logging.getLogger(__name__)


class TTSError(Exception):
    """Raised when TTS synthesis or playback fails."""


class TTSEngine:
    def __init__(self, config: dict):
        self.config = config
        self._model = None
        self._model_path: str | None = None
        self._stop_event = threading.Event()
        self._cache: OrderedDict[str, list[bytes]] = OrderedDict()  # text+voice hash → chunks
        self._ffplay_proc: subprocess.Popen | None = None
        self._model_lock = threading.Lock()
        
        # Stored for practice mode
        self._last_audio_type: str | None = None
        self._last_audio_chunks: list[bytes] = []

    def unload(self) -> None:
        """Unloads the MLX model to free RAM."""
        with self._model_lock:
            if self._model is not None:
                logger.info("Unloading Qwen3-TTS model to free RAM.")
                self._model = None
                import gc
                gc.collect()
                try:
                    mx.metal.clear_cache()
                except Exception:
                    pass

    async def warmup(self) -> None:
        """Background task to pre-load and compile the Qwen TTS model."""
        provider = self.config.get("tts_provider", "qwen_tts")
        if provider == "qwen_tts":
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._sync_warmup)

    def _sync_warmup(self) -> None:
        try:
            from mlx_audio.tts.utils import load_model as load
        except ImportError:
            return

        model_path = self.config.get(
            "qwen_tts_model",
            "/Users/jenyanovak/.cache/huggingface/hub/models--mlx-community--Qwen3-TTS-12Hz-0.6B-Base-4bit"
        )
        voice = self.config.get("qwen_tts_voice", "ryan")

        with self._model_lock:
            if self._model is None:
                logger.info("Warming up Qwen3-TTS model from %s...", model_path)
                try:
                    for attempt in range(3):
                        try:
                            self._model = load(model_path, strict=False)
                            break
                        except Exception as ex:
                            if "fds_to_keep" in str(ex) and attempt < 2:
                                import time
                                time.sleep(0.5)
                                continue
                            raise
                    self._model_path = model_path
                    for _ in self._model.generate("a", voice=voice, stream=True):
                        break
                    logger.info("Qwen3-TTS warmup and graph compilation complete.")
                except Exception as ex:
                    logger.warning("Failed to warmup Qwen3-TTS model: %s", ex)

    def stop(self) -> None:
        """Stops any currently playing audio immediately."""
        self._stop_event.set()
        self._kill_ffplay()

    def _kill_ffplay(self) -> None:
        proc = self._ffplay_proc
        if proc is not None:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            except Exception:
                logger.debug("Error killing ffplay", exc_info=True)
            self._ffplay_proc = None

    @classmethod
    async def get_edge_voices(cls) -> list[dict]:
        try:
            manager = await asyncio.wait_for(edge_tts.VoicesManager.create(), timeout=3.0)
            return sorted([{"friendly_name": v["FriendlyName"], "name": v["Name"]} for v in manager.voices if v["Locale"].startswith("de-")], key=lambda v: v["friendly_name"])
        except Exception as e:
            logger.error("Failed to fetch Edge TTS voices: %s", e)
            return [{"friendly_name": "Fallback Voice (Katja)", "name": "de-DE-KatjaNeural"}]

    @staticmethod
    def _spawn_ffplay_mp3() -> subprocess.Popen:
        """Launches ffplay to play mp3 audio directly from pipe."""
        return subprocess.Popen(
            [
                "ffplay", "-i", "pipe:0",
                "-af", "volume=2.0",
                "-nodisp", "-autoexit", "-loglevel", "quiet"
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=False,
        )

    @staticmethod
    def _spawn_ffplay_pcm() -> subprocess.Popen:
        """Launches ffplay to play raw PCM f32le directly from pipe."""
        return subprocess.Popen(
            [
                "ffplay", "-f", "f32le",
                "-ch_layout", "mono",
                "-ar", "24000",
                "-i", "pipe:0",
                "-af", "volume=2.0",
                "-nodisp", "-autoexit", "-loglevel", "quiet"
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=False,
        )

    def _player_thread(self, audio_q: queue.Queue, done_event: threading.Event) -> None:
        """Consumer thread: reads audio chunks from queue, writes directly to ffplay."""
        proc = None
        try:
            proc = self._spawn_ffplay_pcm()
            self._ffplay_proc = proc
            while True:
                data = audio_q.get()
                if data is None:
                    break
                if self._stop_event.is_set():
                    break
                proc.stdin.write(data)
                proc.stdin.flush()
        except Exception as ex:
            logger.error("ffplay streaming error: %s", ex)
        finally:
            if proc is not None:
                try:
                    proc.stdin.close()
                except Exception:
                    pass
                proc.wait() # wait for playback buffer to finish
            
            self._ffplay_proc = None
            done_event.set()

    def _speak_qwen(self, text: str, repeat: int = 1) -> None:
        """Synchronous: generates audio via MLX and streams to ffplay."""
        try:
            from mlx_audio.tts.utils import load_model as load
        except ImportError as e:
            raise TTSError("MLX-Audio is not installed.") from e

        model_path = self.config.get(
            "qwen_tts_model",
            "/Users/jenyanovak/.cache/huggingface/hub/models--mlx-community--Qwen3-TTS-12Hz-0.6B-Base-4bit"
        )
        voice = self.config.get("qwen_tts_voice", "ryan")

        text_hash = int(hashlib.md5(text.encode()).hexdigest(), 16) & 0xFFFFFFFF
        mx.random.seed(text_hash)

        with self._model_lock:
            if self._model is not None and self._model_path != model_path:
                logger.info("Qwen TTS model path changed, reloading...")
                self._model = None
    
            if self._model is None:
                logger.info("Loading Qwen3-TTS model from %s", model_path)
                try:
                    for attempt in range(3):
                        try:
                            self._model = load(model_path, strict=False)
                            break
                        except Exception as ex:
                            if "fds_to_keep" in str(ex) and attempt < 2:
                                import time
                                time.sleep(0.5)
                                continue
                            raise
                    self._model_path = model_path
                except Exception as ex:
                    raise TTSError(f"Failed to load Qwen3-TTS model: {ex}") from ex

        cache_key = f"{text}||{voice}"
        cached_chunks = self._cache.get(cache_key)

        def _play_chunks(chunks: list[bytes]) -> None:
            audio_q = queue.Queue(maxsize=32)
            done_event = threading.Event()
            player = threading.Thread(target=self._player_thread, args=(audio_q, done_event), daemon=True)
            player.start()
            try:
                for chunk in chunks:
                    if self._stop_event.is_set():
                        break
                    audio_q.put(chunk, timeout=10.0)
            except queue.Full:
                pass
            finally:
                try: audio_q.put(None, timeout=1.0)
                except queue.Full: pass
                done_event.wait(timeout=30.0)
                player.join(timeout=2.0)

        if cached_chunks is not None:
            self._cache.move_to_end(cache_key)
            logger.info("TTS cache hit for: %s...", text[:30])
            self._last_audio_type = "pcm"
            self._last_audio_chunks = cached_chunks
            
            for _ in range(repeat):
                if self._stop_event.is_set():
                    break
                _play_chunks(cached_chunks)
                if repeat > 1 and not self._stop_event.is_set():
                    import time as _time
                    _time.sleep(0.5)
            return

        logger.info("MLX-TTS generating for: %s...", text[:40])
        collected_chunks: list[bytes] = []

        audio_q = queue.Queue(maxsize=32)
        done_event = threading.Event()
        player = threading.Thread(target=self._player_thread, args=(audio_q, done_event), daemon=True)
        player.start()

        try:
            for result in self._model.generate(
                text=text,
                voice=voice,
                temperature=0.9,
                stream=True,
                streaming_interval=0.32,
            ):
                if self._stop_event.is_set():
                    break
                if result.audio is not None:
                    import numpy as np
                    chunk_bytes = np.array(result.audio, copy=False).astype(np.float32).tobytes()
                    collected_chunks.append(chunk_bytes)
                    try:
                        audio_q.put(chunk_bytes, timeout=10.0)
                    except queue.Full:
                        pass
        finally:
            try: audio_q.put(None, timeout=1.0)
            except queue.Full: pass
            done_event.wait(timeout=30.0)
            player.join(timeout=2.0)

        if not self._stop_event.is_set() and collected_chunks:
            self._cache[cache_key] = collected_chunks
            self._cache.move_to_end(cache_key)
            if len(self._cache) > 30:
                self._cache.popitem(last=False)
                
            self._last_audio_type = "pcm"
            self._last_audio_chunks = collected_chunks

            if repeat > 1:
                import time as _time
                _time.sleep(0.5)
                for r in range(repeat - 1):
                    if self._stop_event.is_set():
                        break
                    _play_chunks(collected_chunks)
                    if r < repeat - 2 and not self._stop_event.is_set():
                        _time.sleep(0.5)

    async def _speak_edge(self, text: str, repeat: int = 1) -> None:
        voice = self.config.get("edge_voice", "de-DE-KatjaNeural")
        
        # Edge TTS generates dynamically, but we'll collect chunks to support practice mode natively
        collected_chunks = []
        communicate = edge_tts.Communicate(text, voice)
        
        try:
            proc = self._spawn_ffplay_mp3()
        except OSError as e:
            raise TTSError(f"ffplay not found. Please install ffmpeg. {e}") from e
            
        self._ffplay_proc = proc
        try:
            async for chunk in communicate.stream():
                if self._stop_event.is_set():
                    break
                if chunk["type"] == "audio":
                    proc.stdin.write(chunk["data"])
                    proc.stdin.flush()
                    collected_chunks.append(chunk["data"])
        except Exception as e:
            logger.error("Edge TTS error: %s", e)
            raise TTSError(f"Edge TTS error: {e}") from e
        finally:
            try:
                proc.stdin.close()
            except Exception:
                pass
            while proc.poll() is None:
                await asyncio.sleep(0.1)
                if self._stop_event.is_set():
                    proc.terminate()
                    break
            self._ffplay_proc = None

        if not self._stop_event.is_set() and collected_chunks:
            self._last_audio_type = "mp3"
            self._last_audio_chunks = collected_chunks
            
            if repeat > 1:
                for r in range(repeat - 1):
                    if self._stop_event.is_set():
                        break
                    await asyncio.sleep(0.5)
                    await self._play_cached_mp3()

    async def _play_cached_mp3(self) -> None:
        """Plays the collected MP3 chunks using ffplay."""
        if not self._last_audio_chunks:
            return
        proc = self._spawn_ffplay_mp3()
        self._ffplay_proc = proc
        try:
            for chunk in self._last_audio_chunks:
                if self._stop_event.is_set():
                    break
                proc.stdin.write(chunk)
                proc.stdin.flush()
        finally:
            try: proc.stdin.close()
            except Exception: pass
            
            while proc.poll() is None:
                await asyncio.sleep(0.1)
                if self._stop_event.is_set():
                    proc.terminate()
                    break
            self._ffplay_proc = None

    async def speak(self, text: str, repeat: int = 1) -> None:
        """Async wrapper."""
        self.stop()
        self._stop_event.clear()

        text = text.strip()
        if not text:
            return

        provider = self.config.get("tts_provider", "qwen_tts")
        try:
            if provider == "edge_tts":
                await self._speak_edge(text, repeat)
            elif provider == "qwen_tts":
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, self._speak_qwen, text, repeat)
            else:
                raise TTSError(f"Unknown TTS provider: {provider}")
        except TTSError:
            raise
        except Exception as e:
            import traceback
            with open("/Users/jenyanovak/Projects/active/ru-de-translator/ru_de_translator/tts_crash_traceback.txt", "w") as f:
                f.write(traceback.format_exc())
            raise TTSError(f"TTS failed: {e}") from e

    def clear_cache(self) -> None:
        """Clears the in-memory audio cache."""
        self._cache.clear()
        self._last_audio_chunks.clear()
        logger.info("TTS cache cleared")

    async def practice(self, repeats: int, pause: float) -> None:
        """Plays the last generated audio chunks directly from memory."""
        if not self._last_audio_chunks or not self._last_audio_type:
            raise TTSError("No audio available for practice. Please translate something first.")
            
        self.stop()
        self._stop_event.clear()
        
        for i in range(repeats):
            if self._stop_event.is_set():
                break
                
            try:
                if self._last_audio_type == "pcm":
                    # For Qwen PCM chunks
                    proc = self._spawn_ffplay_pcm()
                else:
                    # For Edge MP3 chunks
                    proc = self._spawn_ffplay_mp3()
                    
                self._ffplay_proc = proc
                
                # Write chunks to process
                for chunk in self._last_audio_chunks:
                    if self._stop_event.is_set():
                        break
                    proc.stdin.write(chunk)
                    proc.stdin.flush()
                
                try: proc.stdin.close()
                except Exception: pass
                
                # Wait for playback to finish
                while proc.poll() is None:
                    await asyncio.sleep(0.1)
                    if self._stop_event.is_set():
                        proc.terminate()
                        break
                        
            except Exception as e:
                logger.error("ffplay practice error: %s", e)
                
            self._ffplay_proc = None
            
            if i < repeats - 1 and not self._stop_event.is_set():
                pause_time = 0.0
                while pause_time < pause:
                    if self._stop_event.is_set():
                        break
                    await asyncio.sleep(0.1)
                    pause_time += 0.1
