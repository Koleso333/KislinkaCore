"""Audio player — PyAV (decode) + sounddevice (output).

Supports every format FFmpeg knows: mp3, flac, wav, ogg, opus,
m4a/aac/alac, wma, webm, etc.  No external binaries — the
FFmpeg libraries are bundled inside the `av` pip wheel.

Public API (signals, methods, properties) is identical to the
original pygame-based player so existing code keeps working.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from pathlib import Path
from typing import Deque

import av
import numpy as np
import sounddevice as sd
from PyQt6.QtCore import QObject, Qt, QTimer, pyqtSignal

from core.hooks import HookManager


def _log(msg: str) -> None:
    print(f"[AudioPlayer] {msg}")


# ── decode thread ───────────────────────────────────────────────

# How many seconds of audio we keep decoded ahead.
_BUF_TARGET_S = 1.0
# Maximum size of the ring-buffer (seconds).  Decode thread sleeps
# when the buffer exceeds this to avoid wasting memory.
_BUF_MAX_S = 4.0


class _Engine:
    """Runs in a background thread.  Decodes with PyAV and feeds
    float-32 samples to a sounddevice OutputStream via a deque."""

    def __init__(self) -> None:
        # ── shared state (lock-protected or atomic-like) ────────
        self._lock = threading.Lock()
        self._buf: Deque[np.ndarray] = deque()  # chunks of float32
        self._buf_samples = 0  # total samples currently in _buf

        # Stream params (set when file is opened)
        self._sr: int = 44100
        self._channels: int = 2

        # Playback state
        self._playing = False
        self._paused = False
        self._duration_ms: int = 0
        self._position_samples: int = 0  # samples written to output
        self._base_position_ms: int = 0  # after seek
        self._volume: float = 1.0

        # Commands
        self._stop_flag = threading.Event()
        self._pause_event = threading.Event()  # SET = not paused
        self._pause_event.set()
        self._seek_target: int | None = None  # ms, or None

        # Events queue (consumed by UI thread)
        self._events_lock = threading.Lock()
        self._events: list[tuple] = []

        # Stream
        self._stream: sd.OutputStream | None = None

        # Decode thread
        self._thread: threading.Thread | None = None

    # ── event helpers ──────────────────────────────────────────

    def _push_event(self, *args: object) -> None:
        with self._events_lock:
            self._events.append(args)

    def drain_events(self) -> list[tuple]:
        with self._events_lock:
            evts = self._events
            self._events = []
            return evts

    # ── public commands (called from UI thread) ────────────────

    def play(self, path: str, start_ms: int = 0) -> None:
        """Start (or restart) playback."""
        self._stop_current()  # stop any previous playback
        self._stop_flag.clear()
        self._pause_event.set()
        self._paused = False
        self._seek_target = None
        self._base_position_ms = start_ms
        self._position_samples = 0
        with self._lock:
            self._buf.clear()
            self._buf_samples = 0

        self._thread = threading.Thread(
            target=self._decode_thread,
            args=(path, start_ms),
            daemon=True,
            name="kislinka-audio",
        )
        self._thread.start()

    def pause(self) -> None:
        if self._playing and not self._paused:
            self._paused = True
            self._pause_event.clear()
            if self._stream and self._stream.active:
                self._stream.stop()
            self._push_event("paused")

    def resume(self) -> None:
        if self._playing and self._paused:
            self._paused = False
            self._pause_event.set()
            if self._stream and not self._stream.active:
                self._stream.start()
            self._push_event("resumed")

    def stop(self) -> None:
        self._stop_current()
        self._push_event("stopped")

    def seek(self, ms: int) -> None:
        self._seek_target = ms

    def set_volume(self, v: float) -> None:
        self._volume = max(0.0, min(1.0, v))

    def shutdown(self) -> None:
        self._stop_current()

    # ── queries ────────────────────────────────────────────────

    @property
    def playing(self) -> bool:
        return self._playing

    @property
    def paused(self) -> bool:
        return self._paused

    @property
    def duration_ms(self) -> int:
        return self._duration_ms

    @property
    def position_ms(self) -> int:
        if self._sr == 0 or self._channels == 0:
            return 0
        # _position_samples counts individual float values (interleaved),
        # so frames = _position_samples / channels,  seconds = frames / sr.
        frames_played = self._position_samples / self._channels
        ms = int(frames_played / self._sr * 1000)
        return self._base_position_ms + ms

    @property
    def volume(self) -> float:
        return self._volume

    # ── internal ───────────────────────────────────────────────

    def _stop_current(self) -> None:
        """Signal the decode thread to exit and wait for it."""
        self._stop_flag.set()
        self._pause_event.set()  # un-block if paused
        if self._stream is not None:
            try:
                self._stream.abort()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None
        self._playing = False
        self._paused = False

    # ── sounddevice callback ───────────────────────────────────

    def _audio_callback(
        self,
        outdata: np.ndarray,
        frames: int,
        time_info: object,
        status: sd.CallbackFlags,
    ) -> None:
        needed = frames * self._channels
        filled = 0
        vol = self._volume
        out = outdata.reshape(-1)  # flat view

        while filled < needed:
            with self._lock:
                if not self._buf:
                    break
                chunk = self._buf[0]
                avail = len(chunk)
                take = min(avail, needed - filled)
                out[filled : filled + take] = chunk[:take] * vol
                if take == avail:
                    self._buf.popleft()
                else:
                    self._buf[0] = chunk[take:]
                self._buf_samples -= take
            filled += take

        if filled < needed:
            out[filled:] = 0.0  # silence

        self._position_samples += filled

    # ── decode thread body ─────────────────────────────────────

    def _decode_thread(self, path: str, start_ms: int) -> None:
        container = None
        try:
            container = av.open(path)
            stream = container.streams.audio[0]
            stream.thread_type = "AUTO"  # threaded codec decoding

            codec_ctx = stream.codec_context
            self._sr = codec_ctx.sample_rate or 44100
            try:
                self._channels = codec_ctx.channels
            except AttributeError:
                ch_layout = codec_ctx.layout
                self._channels = ch_layout.nb_channels if ch_layout else 2

            # Duration — stream.duration is in time_base units,
            # container.duration is in AV_TIME_BASE (microseconds).
            if stream.duration and stream.time_base:
                self._duration_ms = int(
                    float(stream.duration * stream.time_base) * 1000
                )
            elif container.duration:
                # container.duration is microseconds
                self._duration_ms = int(container.duration // 1000)
            else:
                self._duration_ms = 0
            self._push_event("duration", self._duration_ms)

            # Seek to start_ms if needed
            if start_ms > 0:
                target_ts = int(start_ms / 1000 / stream.time_base)
                container.seek(target_ts, stream=stream)

            # Create resampler -> float32 output
            resampler = av.AudioResampler(
                format="flt",  # float32 interleaved
                layout="stereo" if self._channels >= 2 else "mono",
                rate=self._sr,
            )
            # Force stereo output
            self._channels = 2 if self._channels >= 2 else 1

            # Create output stream
            buf_size = max(512, int(self._sr * 0.02))  # ~20ms
            self._stream = sd.OutputStream(
                samplerate=self._sr,
                channels=self._channels,
                dtype="float32",
                blocksize=buf_size,
                callback=self._audio_callback,
            )
            self._stream.start()

            self._playing = True
            self._push_event("started")

            max_buf = int(self._sr * self._channels * _BUF_MAX_S)

            # ── main decode loop ───────────────────────────────
            for packet in container.demux(stream):
                if self._stop_flag.is_set():
                    return

                # Wait while paused
                self._pause_event.wait()
                if self._stop_flag.is_set():
                    return

                # Handle seek
                seek_ms = self._seek_target
                if seek_ms is not None:
                    self._seek_target = None
                    target_ts = int(seek_ms / 1000 / stream.time_base)
                    container.seek(target_ts, stream=stream)
                    with self._lock:
                        self._buf.clear()
                        self._buf_samples = 0
                    self._position_samples = 0
                    self._base_position_ms = seek_ms
                    continue  # restart demux from new position

                for frame in packet.decode():
                    if self._stop_flag.is_set():
                        return

                    # Resample to f32
                    resampled = resampler.resample(frame)
                    for r_frame in resampled:
                        arr = r_frame.to_ndarray().flatten().astype(
                            np.float32, copy=False
                        )
                        with self._lock:
                            self._buf.append(arr)
                            self._buf_samples += len(arr)

                    # Throttle if buffer is full
                    while self._buf_samples > max_buf:
                        if self._stop_flag.is_set():
                            return
                        time.sleep(0.02)

            # Flush resampler
            resampled = resampler.resample(None)
            for r_frame in resampled:
                arr = r_frame.to_ndarray().flatten().astype(np.float32, copy=False)
                with self._lock:
                    self._buf.append(arr)
                    self._buf_samples += len(arr)

            # Wait for buffer to drain
            while self._buf_samples > 0:
                if self._stop_flag.is_set():
                    return
                time.sleep(0.05)
            # Small extra wait so sounddevice finishes outputting
            time.sleep(0.15)

            self._playing = False
            self._push_event("finished")

        except Exception as e:
            self._push_event("error", str(e))
            _log(f"Decode error: {e}")
        finally:
            self._playing = False
            if container:
                try:
                    container.close()
                except Exception:
                    pass


# ── Qt wrapper ──────────────────────────────────────────────────


class AudioPlayer(QObject):
    """Audio player — PyAV + sounddevice.

    Signals
    -------
    started, paused, resumed, stopped, finished,
    position_changed(int ms), duration_changed(int ms),
    volume_changed(float 0-1), error(str)
    """

    started = pyqtSignal()
    paused = pyqtSignal()
    resumed = pyqtSignal()
    stopped = pyqtSignal()
    finished = pyqtSignal()
    position_changed = pyqtSignal(int)
    duration_changed = pyqtSignal(int)
    volume_changed = pyqtSignal(float)
    error = pyqtSignal(str)

    _instance: AudioPlayer | None = None

    def __init__(self) -> None:
        if AudioPlayer._instance is not None:
            raise RuntimeError("Use AudioPlayer.instance()")
        super().__init__()
        AudioPlayer._instance = self

        self._engine = _Engine()
        self._current_file: Path | None = None

        self._timer = QTimer(self)
        self._timer.setInterval(80)
        self._timer.timeout.connect(self._poll)

        _log("Audio system ready (PyAV + sounddevice)")

    # ── singleton ──────────────────────────────────────────────

    @classmethod
    def instance(cls) -> AudioPlayer:
        if cls._instance is None:
            cls()
        return cls._instance  # type: ignore[return-value]

    # ── properties ─────────────────────────────────────────────

    @property
    def position(self) -> int:
        return self._engine.position_ms

    @property
    def duration(self) -> int:
        return self._engine.duration_ms

    @property
    def is_playing(self) -> bool:
        return self._engine.playing and not self._engine.paused

    @property
    def is_paused(self) -> bool:
        return self._engine.paused

    @property
    def current_file(self) -> Path | None:
        return self._current_file

    @property
    def volume(self) -> float:
        return self._engine.volume

    # ── playback ───────────────────────────────────────────────

    def play(self, file_path: str | Path, start_ms: int = 0) -> None:
        hooks = HookManager.instance()
        path = Path(file_path)
        path = Path(hooks.filter("before_audio_play", str(path), start_ms=start_ms))

        if not path.exists():
            self.error.emit(f"File not found: {path}")
            return

        try:
            self._engine.play(str(path), start_ms)
            self._current_file = path
            self._timer.start()
            _log(f"Playing: {path.name}")
        except Exception as e:
            _log(f"Play failed: {e}")
            self.error.emit(f"Cannot play: {e}")

    def pause(self) -> None:
        if self.is_playing:
            self._engine.pause()

    def resume(self) -> None:
        if self.is_paused:
            self._engine.resume()

    def toggle_pause(self) -> None:
        if self.is_paused:
            self.resume()
        elif self.is_playing:
            self.pause()

    def stop(self) -> None:
        self._engine.stop()
        self._current_file = None

    def set_volume(self, vol: float) -> None:
        self._engine.set_volume(vol)
        self.volume_changed.emit(self._engine.volume)
        HookManager.instance().emit("on_audio_volume", volume=self._engine.volume)

    def seek(self, position_ms: int) -> None:
        if not self._current_file:
            return
        position_ms = max(0, min(position_ms, self.duration))
        self._engine.seek(position_ms)
        self.position_changed.emit(position_ms)
        HookManager.instance().emit("on_audio_seek", position_ms=position_ms)

    # ── poll events from engine thread ─────────────────────────

    def _poll(self) -> None:
        hooks = HookManager.instance()

        for ev in self._engine.drain_events():
            name = ev[0]

            if name == "started":
                self.started.emit()
                hooks.emit("after_audio_play", file_path=str(self._current_file or ""))

            elif name == "paused":
                self.paused.emit()
                hooks.emit("on_audio_pause")

            elif name == "resumed":
                self.resumed.emit()
                hooks.emit("on_audio_resume")

            elif name == "stopped":
                self._current_file = None
                self.stopped.emit()
                hooks.emit("on_audio_stop")

            elif name == "finished":
                self._timer.stop()
                dur = self._engine.duration_ms
                self._current_file = None
                self.position_changed.emit(dur)
                self.finished.emit()
                hooks.emit("on_audio_finished")
                _log("Track finished")

            elif name == "duration":
                self.duration_changed.emit(int(ev[1]))

            elif name == "error":
                msg = str(ev[1])
                _log(f"Engine error: {msg}")
                self.error.emit(msg)

        # Live position update (more responsive than event-based).
        if self._engine.playing:
            self.position_changed.emit(self._engine.position_ms)

    # ── shutdown ───────────────────────────────────────────────

    def shutdown(self) -> None:
        self._timer.stop()
        self._engine.shutdown()
        _log("Audio system shut down")