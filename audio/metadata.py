"""
Metadata reader for audio files.

Uses mutagen to extract:
  - Title, artist, album, year, track number, genre
  - Duration
  - Cover art as QPixmap or raw bytes

Supports: mp3, flac, ogg, m4a/mp4, wav
"""

from pathlib import Path
from dataclasses import dataclass, field

from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import QByteArray


def _log(msg: str):
    print(f"[Metadata] {msg}")


@dataclass
class TrackInfo:
    """Parsed track metadata."""
    title: str = ""
    artist: str = ""
    album: str = ""
    year: str = ""
    track_number: str = ""
    genre: str = ""
    duration_ms: int = 0
    file_path: str = ""
    has_cover: bool = False

    @property
    def duration_seconds(self) -> float:
        return self.duration_ms / 1000.0

    @property
    def duration_str(self) -> str:
        """Format as M:SS or H:MM:SS."""
        total = int(self.duration_ms / 1000)
        h = total // 3600
        m = (total % 3600) // 60
        s = total % 60
        if h > 0:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"


class MetadataReader:
    """Static methods to read audio file metadata."""

    @staticmethod
    def read(file_path: str | Path) -> TrackInfo:
        """Read metadata from an audio file."""
        path = Path(file_path)
        info = TrackInfo(file_path=str(path))

        if not path.exists():
            _log(f"⚠ File not found: {path}")
            return info

        try:
            import mutagen
            audio = mutagen.File(str(path), easy=True)

            if audio is None:
                _log(f"⚠ Cannot read: {path.name}")
                info.title = path.stem
                return info

            # duration
            if audio.info and hasattr(audio.info, "length"):
                info.duration_ms = int(audio.info.length * 1000)

            # easy tags
            if hasattr(audio, "tags") and audio.tags:
                tags = audio.tags if isinstance(audio.tags, dict) else audio

                def get_tag(key: str) -> str:
                    val = tags.get(key, [""])[0] if isinstance(tags.get(key), list) else tags.get(key, "")
                    return str(val) if val else ""

                info.title = get_tag("title")
                info.artist = get_tag("artist")
                info.album = get_tag("album")
                info.year = get_tag("date")
                info.track_number = get_tag("tracknumber")
                info.genre = get_tag("genre")

            if not info.title:
                info.title = path.stem

            # check for cover
            info.has_cover = MetadataReader._has_cover(path)

        except Exception as e:
            _log(f"⚠ Error reading {path.name}: {e}")
            info.title = path.stem

        return info

    @staticmethod
    def get_cover_bytes(file_path: str | Path) -> bytes | None:
        """Extract raw cover art bytes from audio file."""
        path = Path(file_path)
        if not path.exists():
            return None

        try:
            import mutagen
            ext = path.suffix.lower()

            if ext == ".mp3":
                from mutagen.mp3 import MP3
                from mutagen.id3 import ID3

                audio = MP3(str(path))
                if audio.tags:
                    for key in audio.tags:
                        if key.startswith("APIC"):
                            return audio.tags[key].data
                return None

            elif ext == ".flac":
                from mutagen.flac import FLAC

                audio = FLAC(str(path))
                if audio.pictures:
                    return audio.pictures[0].data
                return None

            elif ext in (".m4a", ".mp4", ".aac"):
                from mutagen.mp4 import MP4

                audio = MP4(str(path))
                if audio.tags and "covr" in audio.tags:
                    covers = audio.tags["covr"]
                    if covers:
                        return bytes(covers[0])
                return None

            elif ext == ".ogg":
                from mutagen.oggvorbis import OggVorbis
                import base64

                audio = OggVorbis(str(path))
                if audio.tags and "metadata_block_picture" in audio.tags:
                    import struct
                    raw = base64.b64decode(audio.tags["metadata_block_picture"][0])
                    # parse FLAC picture block
                    pos = 0
                    pic_type = struct.unpack(">I", raw[pos:pos+4])[0]; pos += 4
                    mime_len = struct.unpack(">I", raw[pos:pos+4])[0]; pos += 4
                    pos += mime_len  # skip mime
                    desc_len = struct.unpack(">I", raw[pos:pos+4])[0]; pos += 4
                    pos += desc_len  # skip description
                    pos += 16  # skip width, height, depth, colors
                    data_len = struct.unpack(">I", raw[pos:pos+4])[0]; pos += 4
                    return raw[pos:pos+data_len]
                return None

            elif ext == ".wav":
                return None  # WAV rarely has embedded art

            else:
                return None

        except Exception as e:
            _log(f"⚠ Cover extraction error for {path.name}: {e}")
            return None

    @staticmethod
    def get_cover(file_path: str | Path, size: int = 0) -> QPixmap | None:
        """
        Get cover art as QPixmap.

        size: if > 0, scale to size x size (keeping aspect ratio)
        """
        data = MetadataReader.get_cover_bytes(file_path)
        if data is None:
            return None

        try:
            pixmap = QPixmap()
            pixmap.loadFromData(QByteArray(data))

            if pixmap.isNull():
                return None

            if size > 0:
                pixmap = pixmap.scaled(
                    size, size,
                    aspectRatioMode=Qt.AspectRatioMode.KeepAspectRatio,
                    transformMode=Qt.TransformationMode.SmoothTransformation,
                )

            return pixmap
        except Exception as e:
            _log(f"⚠ Cover pixmap error: {e}")
            return None

    @staticmethod
    def _has_cover(path: Path) -> bool:
        """Quick check if file has embedded cover."""
        try:
            data = MetadataReader.get_cover_bytes(path)
            return data is not None and len(data) > 0
        except Exception:
            return False


# fix missing import for get_cover scaling
from PyQt6.QtCore import Qt