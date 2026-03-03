"""
Audio player.

Uses pygame.mixer for playback.
Supports: mp3, ogg, wav, flac (native), m4a (via ffmpeg conversion).
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal, QTimer


ROOT = Path(__file__).resolve().parent.parent
BIN_DIR = ROOT / "assets" / "bin"

NATIVE_FORMATS = {".mp3", ".ogg", ".wav", ".flac"}
CONVERT_FORMATS = {".m4a", ".mp4", ".aac", ".wma"}


def _log(msg: str):
    print(f"[AudioPlayer] {msg}")


def _find_ffmpeg() -> str | None:
    for name in ("ffmpeg.exe", "ffmpeg"):
        p = BIN_DIR / name
        if p.exists():
            return str(p)
    return shutil.which("ffmpeg")


def _find_ffprobe() -> str | None:
    for name in ("ffprobe.exe", "ffprobe"):
        p = BIN_DIR / name
        if p.exists():
            return str(p)
    return shutil.which("ffprobe")


class AudioPlayer(QObject):
    """
    Audio player with pygame.mixer backend.

    Signals:
        started()
        paused()
        resumed()
        stopped()
        finished()
        position_changed(int)   — position in ms
        duration_changed(int)   — duration in ms
        volume_changed(float)   — 0.0–1.0
        error(str)
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

    _instance: "AudioPlayer | None" = None

    def __init__(self):
        if AudioPlayer._instance is not None:
            raise RuntimeError("Use AudioPlayer.instance()")
        super().__init__()
        AudioPlayer._instance = self

        self._volume = 1.0
        self._position_ms = 0
        self._duration_ms = 0
        self._playing = False
        self._paused_flag = False
        self._current_file: Path | None = None
        self._temp_file: str | None = None
        self._play_start_pos = 0

        self._ffmpeg = _find_ffmpeg()
        self._ffprobe = _find_ffprobe()
        if self._ffmpeg:
            _log(f"ffmpeg found: {self._ffmpeg}")
        else:
            _log("⚠ ffmpeg not found — m4a/aac playback disabled")

        # defer pygame init
        self._mixer_ready = False
        self._pygame = None

        # timer for position tracking
        self._timer = QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._update_position)

    @classmethod
    def instance(cls) -> "AudioPlayer":
        if cls._instance is None:
            cls()
        return cls._instance

    def _ensure_mixer(self) -> bool:
        """Lazy init pygame mixer on first use."""
        if self._mixer_ready:
            return True

        try:
            import pygame
            self._pygame = pygame

            # init pygame first
            if not pygame.get_init():
                pygame.init()
                _log("pygame.init() done")

            # then mixer
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
                _log("pygame.mixer.init() done")

            self._mixer_ready = True
            _log("Audio system ready ✓")
            return True

        except Exception as e:
            _log(f"⚠ pygame init failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    # ── properties ──────────────────────────────────

    @property
    def position(self) -> int:
        return self._position_ms

    @property
    def duration(self) -> int:
        return self._duration_ms

    @property
    def is_playing(self) -> bool:
        return self._playing and not self._paused_flag

    @property
    def is_paused(self) -> bool:
        return self._paused_flag

    @property
    def current_file(self) -> Path | None:
        return self._current_file

    @property
    def volume(self) -> float:
        return self._volume

    # ── playback ────────────────────────────────────

    def play(self, file_path: str | Path, start_ms: int = 0):
        """Play an audio file."""
        if not self._ensure_mixer():
            self.error.emit("Audio system not available")
            return

        path = Path(file_path)
        if not path.exists():
            self.error.emit(f"File not found: {path}")
            return

        self._stop_internal()

        ext = path.suffix.lower()
        play_path = str(path)

        # convert if needed
        if ext in CONVERT_FORMATS:
            if not self._ffmpeg:
                self.error.emit(f"ffmpeg required for {ext} files")
                return
            converted = self._convert_to_wav(path)
            if converted is None:
                self.error.emit(f"Failed to convert {path.name}")
                return
            play_path = converted

        # get duration
        from audio.metadata import MetadataReader
        info = MetadataReader.read(file_path)
        self._duration_ms = info.duration_ms
        self.duration_changed.emit(self._duration_ms)

        # load and play
        try:
            self._pygame.mixer.music.load(play_path)
            self._pygame.mixer.music.set_volume(self._volume)

            if start_ms > 0:
                self._pygame.mixer.music.play()
                try:
                    self._pygame.mixer.music.set_pos(start_ms / 1000.0)
                    self._play_start_pos = start_ms
                except Exception:
                    self._play_start_pos = 0
            else:
                self._pygame.mixer.music.play()
                self._play_start_pos = 0

            self._current_file = path
            self._playing = True
            self._paused_flag = False
            self._position_ms = start_ms

            self._timer.start()
            self.started.emit()
            _log(f"Playing: {path.name}")

        except Exception as e:
            _log(f"⚠ Direct play failed: {e}")

            # fallback: convert to wav
            if ext in NATIVE_FORMATS and self._ffmpeg:
                _log("Trying ffmpeg fallback...")
                converted = self._convert_to_wav(path)
                if converted:
                    try:
                        self._pygame.mixer.music.load(converted)
                        self._pygame.mixer.music.set_volume(self._volume)
                        self._pygame.mixer.music.play()
                        self._current_file = path
                        self._playing = True
                        self._paused_flag = False
                        self._play_start_pos = 0
                        self._position_ms = 0
                        self._timer.start()
                        self.started.emit()
                        _log(f"Playing (converted): {path.name}")
                        return
                    except Exception as e2:
                        _log(f"⚠ Fallback also failed: {e2}")

            self.error.emit(f"Cannot play: {e}")

    def pause(self):
        if not self._playing or self._paused_flag:
            return
        if not self._mixer_ready:
            return
        try:
            self._pygame.mixer.music.pause()
            self._paused_flag = True
            self._timer.stop()
            self.paused.emit()
            _log("Paused")
        except Exception as e:
            _log(f"⚠ Pause error: {e}")

    def resume(self):
        if not self._paused_flag:
            return
        if not self._mixer_ready:
            return
        try:
            self._pygame.mixer.music.unpause()
            self._paused_flag = False
            self._timer.start()
            self.resumed.emit()
            _log("Resumed")
        except Exception as e:
            _log(f"⚠ Resume error: {e}")

    def toggle_pause(self):
        if self._paused_flag:
            self.resume()
        elif self._playing:
            self.pause()

    def stop(self):
        self._stop_internal()
        self.stopped.emit()
        _log("Stopped")

    def set_volume(self, vol: float):
        self._volume = max(0.0, min(1.0, vol))
        if self._mixer_ready:
            try:
                self._pygame.mixer.music.set_volume(self._volume)
            except Exception:
                pass
        self.volume_changed.emit(self._volume)

    def seek(self, position_ms: int):
        if not self._playing or not self._current_file:
            return
        if not self._mixer_ready:
            return
        position_ms = max(0, min(position_ms, self._duration_ms))
        try:
            self._pygame.mixer.music.set_pos(position_ms / 1000.0)
            self._play_start_pos = position_ms
            self._position_ms = position_ms
            self.position_changed.emit(self._position_ms)
        except Exception as e:
            _log(f"⚠ Seek error: {e}")

    # ── internal ────────────────────────────────────

    def _stop_internal(self):
        self._timer.stop()
        if self._mixer_ready:
            try:
                self._pygame.mixer.music.stop()
                self._pygame.mixer.music.unload()
            except Exception:
                pass
        self._playing = False
        self._paused_flag = False
        self._position_ms = 0
        self._play_start_pos = 0
        self._cleanup_temp()

    def _update_position(self):
        if not self._mixer_ready:
            return
        try:
            if not self._pygame.mixer.music.get_busy():
                if self._playing and not self._paused_flag:
                    self._playing = False
                    self._timer.stop()
                    self._position_ms = self._duration_ms
                    self.position_changed.emit(self._position_ms)
                    self.finished.emit()
                    self._cleanup_temp()
                    _log("Track finished")
                return

            pos = self._pygame.mixer.music.get_pos()
            if pos >= 0:
                self._position_ms = self._play_start_pos + pos
                if self._duration_ms > 0:
                    self._position_ms = min(self._position_ms, self._duration_ms)
                self.position_changed.emit(self._position_ms)

        except Exception:
            pass

    # ── ffmpeg ──────────────────────────────────────

    def _convert_to_wav(self, source: Path) -> str | None:
        if not self._ffmpeg:
            return None

        try:
            fd, tmp_path = tempfile.mkstemp(suffix=".wav")
            os.close(fd)

            cmd = [
                self._ffmpeg,
                "-y",
                "-i", str(source),
                "-acodec", "pcm_s16le",
                "-ar", "44100",
                "-ac", "2",
                tmp_path,
            ]

            kwargs = {"stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "timeout": 60}
            if os.name == "nt":
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

            result = subprocess.run(cmd, **kwargs)

            if result.returncode != 0:
                _log(f"⚠ ffmpeg error: {result.stderr.decode(errors='replace')[:200]}")
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
                return None

            self._temp_file = tmp_path
            _log(f"Converted: {source.name} → temp WAV")
            return tmp_path

        except Exception as e:
            _log(f"⚠ Conversion error: {e}")
            return None

    def _cleanup_temp(self):
        if self._temp_file and os.path.exists(self._temp_file):
            try:
                os.unlink(self._temp_file)
            except Exception:
                pass
            self._temp_file = None

    # ── shutdown ────────────────────────────────────

    def shutdown(self):
        self._stop_internal()
        if self._mixer_ready:
            try:
                self._pygame.mixer.quit()
                self._pygame.quit()
            except Exception:
                pass
        _log("Audio system shut down")