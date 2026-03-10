"""
TripleTimecode — lyrics timecode editor for KislinkaCore.
"""

import re
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout,
    QFileDialog, QPlainTextEdit, QScrollArea,
    QLabel, QApplication,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QShortcut, QKeySequence, QTextCursor

from core.scene import Scene, AnimationType
from core.fonts import Fonts
from widgets.klabel import KLabel
from widgets.kbutton import KButton
from widgets.ktoggle import KToggle
from audio.metadata import MetadataReader


_TC = re.compile(r"^\[(\d+):(\d{2})\.(\d{2})\]\s?(.*)")
_TC_STRIP = re.compile(r"^\[\d+:\d{2}\.\d{2}]\s?")


class TripleTimecode:

    # ================================================================
    #  Lifecycle
    # ================================================================

    def setup(self, app, state=None):
        self._pending_state = state
        return self._setup(app)

    def _setup(self, app):
        state = None
        if hasattr(self, "_pending_state"):
            state = self._pending_state
            self._pending_state = None

        self.app = app
        self.sm = app.scene_manager
        self.player = app.audio
        self.loc = app.locale
        self.tm = app.theme_manager

        self.current_file = None
        self.total_dur = 0
        self.sync_mode = False
        self.in_preview = False
        self._history = []

        self._pv_labels = []
        self._pv_times = []
        self._pv_cur = -2

        self.player.started.connect(self._on_play)
        self.player.stopped.connect(self._on_stop)
        self.player.finished.connect(self._on_stop)

        app.window.titlebar.add_custom_button(
            "back", self._toggle_preview, icon_size=16,
        )

        self._clock = QTimer()
        self._clock.setInterval(50)
        self._clock.timeout.connect(self._tick)

        self._pv_clock = QTimer()
        self._pv_clock.setInterval(50)
        self._pv_clock.timeout.connect(self._tick_pv)

        self._hotkey = QShortcut(QKeySequence("W"), app.window)
        self._hotkey.setContext(Qt.ShortcutContext.WindowShortcut)
        self._hotkey.activated.connect(self._stamp)
        self._hotkey.setEnabled(False)

        # restore
        restore_scene = "editor"
        restore_text = ""
        restore_sync = False
        restore_file = None
        restore_total_dur = 0
        if isinstance(state, dict):
            restore_scene = state.get("scene", "editor")
            restore_text = state.get("lyrics", "")
            restore_sync = bool(state.get("sync_mode", False))
            restore_file = state.get("current_file")
            restore_total_dur = int(state.get("total_dur", 0) or 0)

        self.sm.push(self._editor_scene(), AnimationType.NONE)
        if restore_text:
            self._ed.setPlainText(restore_text)
        if restore_total_dur:
            self.total_dur = restore_total_dur
            self._time_lbl.setText(f"0:00.00 / {self._fmt(self.total_dur)}")
        if restore_sync:
            self._set_mode(True)

        if restore_file:
            self.current_file = restore_file

        if restore_scene == "preview":
            self._toggle_preview()

    def save_state(self):
        scene = "editor"
        try:
            if self.sm and self.sm.current:
                scene = self.sm.current.name
        except Exception:
            pass
        text = ""
        try:
            if hasattr(self, "_ed") and self._ed:
                text = self._ed.toPlainText()
        except Exception:
            pass

        return {
            "scene": scene,
            "lyrics": text,
            "sync_mode": bool(getattr(self, "sync_mode", False)),
            "current_file": getattr(self, "current_file", None),
            "total_dur": int(getattr(self, "total_dur", 0) or 0),
        }

    def cleanup_visual(self):
        """Cleanup only UI-related resources; keep audio playback/state intact."""
        try:
            self._clock.stop()
        except Exception:
            pass
        try:
            self._pv_clock.stop()
        except Exception:
            pass

        for sig, slot in (
            (self.player.started, self._on_play),
            (self.player.stopped, self._on_stop),
            (self.player.finished, self._on_stop),
        ):
            try:
                sig.disconnect(slot)
            except Exception:
                pass

        try:
            self.app.window.titlebar.clear_custom_buttons()
        except Exception:
            pass

    def on_theme_changed(self):
        """Called by core on theme change to re-apply per-widget stylesheets."""
        try:
            self._apply_theme_widgets()
        except Exception:
            pass

    def on_language_changed(self):
        """Called by core on language change to update translated texts."""
        try:
            self._apply_language_widgets()
        except Exception:
            pass

    def _apply_language_widgets(self):
        """Update all widget texts with current locale."""
        # load button
        if hasattr(self, "_load_btn") and self._load_btn:
            self._load_btn.setText(self.loc.t("load_music"))

        # title label (only if no track loaded)
        if hasattr(self, "_title_lbl") and self._title_lbl:
            if not getattr(self, "current_file", None):
                self._title_lbl.setText(self.loc.t("no_track"))

        # play button
        if hasattr(self, "_play_btn") and self._play_btn:
            if self.player.is_playing:
                self._play_btn.setText(self.loc.t("pause"))
            else:
                self._play_btn.setText(self.loc.t("play"))

        # mode label
        if hasattr(self, "_mode_lbl") and self._mode_lbl:
            sync = getattr(self, "sync_mode", False)
            self._mode_lbl.setText(self.loc.t("sync_mode") if sync else self.loc.t("edit_mode"))

        # editor placeholder
        if hasattr(self, "_ed") and self._ed:
            self._ed.setPlaceholderText(self.loc.t("lyrics_placeholder"))

        # stamp button
        if hasattr(self, "_stamp_btn") and self._stamp_btn:
            self._stamp_btn.setText(self.loc.t("stamp"))

        # undo button
        if hasattr(self, "_undo_btn") and self._undo_btn:
            self._undo_btn.setText(self.loc.t("undo_stamp"))

        # stop button
        if hasattr(self, "_stop_btn") and self._stop_btn:
            self._stop_btn.setText(self.loc.t("stop"))

        # clear button
        if hasattr(self, "_clear_btn") and self._clear_btn:
            self._clear_btn.setText(self.loc.t("clear_timecodes"))

        # export button
        if hasattr(self, "_export_btn") and self._export_btn:
            self._export_btn.setText(self.loc.t("export"))

        # preview play/pause button
        if hasattr(self, "_pvt") and self._pvt:
            self._pvt.setText(f"{self.loc.t('play')} / {self.loc.t('pause')}")

    def cleanup(self):
        self.player.stop()
        self._clock.stop()
        self._pv_clock.stop()

        for sig, slot in (
            (self.player.started, self._on_play),
            (self.player.stopped, self._on_stop),
            (self.player.finished, self._on_stop),
        ):
            try:
                sig.disconnect(slot)
            except Exception:
                pass
        self.app.window.titlebar.clear_custom_buttons()

    # ================================================================
    #  Helpers
    # ================================================================

    @staticmethod
    def _fmt(ms):
        if ms < 0:
            ms = 0
        m = int(ms // 60_000)
        s = int(ms % 60_000 // 1_000)
        c = int(ms % 1_000 // 10)
        return f"{m}:{s:02d}.{c:02d}"

    # ================================================================
    #  Editor scene
    # ================================================================

    def _editor_scene(self):
        sc = Scene("editor")
        root = sc.scene_layout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        body = QWidget()
        hl = QHBoxLayout(body)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(0)
        hl.addWidget(self._build_left())
        hl.addWidget(self._build_right(), 1)

        root.addWidget(body, 1)
        return sc

    # ── left panel ──────────────────────────────────────

    def _build_left(self):
        pan = QWidget()
        self._left_pan = pan
        pan.setFixedWidth(320)
        pan.setStyleSheet(f"background:{self.tm.bg_alt};")

        v = QVBoxLayout(pan)
        v.setContentsMargins(20, 16, 20, 16)
        v.setSpacing(0)

        self._load_btn = KButton(self.loc.t("load_music"), on_click=self._load)
        v.addWidget(self._load_btn)
        v.addSpacing(12)

        self._cover = QLabel()
        self._cover.setFixedSize(280, 280)
        self._cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._reset_cover_style()
        v.addWidget(self._cover, alignment=Qt.AlignmentFlag.AlignCenter)
        v.addSpacing(12)

        self._title_lbl = KLabel(
            self.loc.t("no_track"), style="body",
            align=Qt.AlignmentFlag.AlignCenter,
        )
        v.addWidget(self._title_lbl)
        v.addSpacing(8)

        self._time_lbl = KLabel(
            "0:00.00 / 0:00.00", style="heading", font_size=22,
            align=Qt.AlignmentFlag.AlignCenter,
        )
        v.addWidget(self._time_lbl)
        v.addSpacing(16)

        row = QHBoxLayout()
        row.setSpacing(10)
        self._play_btn = KButton(
            self.loc.t("play"), on_click=self._toggle_play, height=46,
        )
        row.addWidget(self._play_btn)
        self._stop_btn = KButton(
            self.loc.t("stop"), on_click=self._do_stop, height=46,
        )
        row.addWidget(self._stop_btn)
        v.addLayout(row)

        v.addStretch()
        return pan

    def _reset_cover_style(self):
        self._cover.setStyleSheet(
            f"background:{self.tm.bg};"
            f"border:1px solid {self.tm.border};"
            f"border-radius:8px;"
        )

    # ── right panel (editor + controls) ────────────────

    def _build_right(self):
        pan = QWidget()
        self._right_pan = pan
        vl = QVBoxLayout(pan)
        vl.setContentsMargins(20, 16, 20, 16)
        vl.setSpacing(0)

        self._ed = QPlainTextEdit()
        self._ed.setPlaceholderText(self.loc.t("lyrics_placeholder"))
        self._ed.setFont(Fonts.body(14))
        self._ed.setStyleSheet(
            f"QPlainTextEdit{{"
            f"  background:{self.tm.bg};"
            f"  color:{self.tm.fg};"
            f"  border:1.5px solid {self.tm.border};"
            f"  border-radius:8px;"
            f"  padding:12px;"
            f"  selection-background-color:{self.tm.fg};"
            f"  selection-color:{self.tm.bg};"
            f"}}"
        )
        vl.addWidget(self._ed, 1)
        vl.addSpacing(12)

        div = QWidget()
        self._right_div = div
        div.setFixedHeight(1)
        div.setStyleSheet(f"background:{self.tm.border};")
        vl.addWidget(div)
        vl.addSpacing(12)

        bottom = QVBoxLayout()
        bottom.setSpacing(8)

        mr = QHBoxLayout()
        mr.setSpacing(12)
        self._mode_lbl = KLabel(self.loc.t("edit_mode"), style="body")
        mr.addWidget(self._mode_lbl)
        mr.addStretch()
        tog = KToggle(checked=False)
        tog.toggled.connect(self._set_mode)
        mr.addWidget(tog)
        bottom.addLayout(mr)

        self._stamp_btn = KButton(
            self.loc.t("stamp"), on_click=self._stamp, height=42,
        )
        self._stamp_btn.setEnabled(False)
        bottom.addWidget(self._stamp_btn)

        acts = QHBoxLayout()
        acts.setSpacing(8)

        self._undo_btn = KButton(
            self.loc.t("undo_stamp"), on_click=self._undo, height=38,
        )
        self._undo_btn.setEnabled(False)
        acts.addWidget(self._undo_btn)

        self._clear_btn = KButton(
            self.loc.t("clear_timecodes"), on_click=self._clear, height=38,
        )
        acts.addWidget(self._clear_btn)

        self._export_btn = KButton(
            self.loc.t("export"), on_click=self._copy, height=38,
        )
        acts.addWidget(self._export_btn)

        bottom.addLayout(acts)
        vl.addLayout(bottom)
        return pan

    # ================================================================
    #  Player controls
    # ================================================================

    def _load(self):
        path, _ = QFileDialog.getOpenFileName(
            None, self.loc.t("load_music"), "",
            "Audio (*.mp3 *.flac *.ogg *.wav *.m4a)",
        )
        if not path:
            return

        self.current_file = path
        info = MetadataReader.read(path)
        self._title_lbl.setText(info.title or Path(path).stem)
        self.total_dur = info.duration_ms

        px = MetadataReader.get_cover(path, size=280)
        if px:
            self._cover.setPixmap(px.scaled(
                280, 280,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))
        else:
            self._reset_cover_style()

        self.player.play(path)
        self._clock.start()

    def _toggle_play(self):
        if not self.current_file:
            return
        if self.player.is_playing and not self.player.is_paused:
            self.player.pause()
        elif self.player.is_paused:
            self.player.resume()
        else:
            self.player.play(self.current_file)
            self._clock.start()

    def _do_stop(self):
        self.player.stop()
        self._clock.stop()
        self._time_lbl.setText(f"0:00.00 / {self._fmt(self.total_dur)}")
        self._play_btn.setText(self.loc.t("play"))

    def _on_play(self):
        self._play_btn.setText(self.loc.t("pause"))
        self._clock.start()

    def _on_stop(self):
        self._play_btn.setText(self.loc.t("play"))

    def _tick(self):
        if self.player.is_playing or self.player.is_paused:
            p = self.player.position
            d = self.player.duration or self.total_dur
            self._time_lbl.setText(f"{self._fmt(p)} / {self._fmt(d)}")

    # ================================================================
    #  Mode switching
    # ================================================================

    def _set_mode(self, sync):
        self.sync_mode = sync
        self._ed.setReadOnly(sync)
        self._stamp_btn.setEnabled(sync)
        self._hotkey.setEnabled(sync)
        self._mode_lbl.setText(
            self.loc.t("sync_mode") if sync else self.loc.t("edit_mode"),
        )

    # ================================================================
    #  Timecode stamping
    # ================================================================

    def _stamp(self):
        if not self.current_file:
            return
        if not (self.player.is_playing or self.player.is_paused):
            return

        tc = f"[{self._fmt(self.player.position)}]"
        lines = self._ed.toPlainText().split("\n")

        for i, ln in enumerate(lines):
            if not _TC.match(ln):
                self._history.append((i, ln))
                lines[i] = f"{tc} {ln}" if ln.strip() else tc
                self._ed.setPlainText("\n".join(lines))

                cursor = self._ed.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.Start)
                for _ in range(min(i + 2, len(lines) - 1)):
                    cursor.movePosition(QTextCursor.MoveOperation.Down)
                self._ed.setTextCursor(cursor)
                self._ed.ensureCursorVisible()

                self._undo_btn.setEnabled(True)
                return

    def _undo(self):
        if not self._history:
            return
        idx, orig = self._history.pop()
        lines = self._ed.toPlainText().split("\n")
        if idx < len(lines):
            lines[idx] = orig
            self._ed.setPlainText("\n".join(lines))
        self._undo_btn.setEnabled(bool(self._history))

    def _clear(self):
        lines = self._ed.toPlainText().split("\n")
        self._ed.setPlainText("\n".join(_TC_STRIP.sub("", l) for l in lines))
        self._history.clear()
        self._undo_btn.setEnabled(False)

    def _copy(self):
        QApplication.clipboard().setText(self._ed.toPlainText())

    # ================================================================
    #  Preview scene
    # ================================================================

    def _toggle_preview(self):
        if self.sm.is_animating:
            return
        if self.in_preview:
            self._pv_clock.stop()
            self.sm.pop(AnimationType.SLIDE_RIGHT)
            self.in_preview = False
        else:
            self.sm.push(self._preview_scene(), AnimationType.SLIDE_LEFT)
            self._pv_clock.start()
            self.in_preview = True

    def _preview_scene(self):
        sc = Scene("preview")
        root = sc.scene_layout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._scr = QScrollArea()
        self._scr.setWidgetResizable(True)

        self._scr.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff,
        )
        self._scr.setStyleSheet(
            f"QScrollArea{{background:{self.tm.bg};border:none;}}"
        )

        inner = QWidget()
        vl = QVBoxLayout(inner)
        vl.setContentsMargins(40, 60, 40, 250)
        vl.setSpacing(6)

        self._pv_labels.clear()
        self._pv_times.clear()
        self._pv_cur = -2

        text = self._ed.toPlainText().strip()
        if text:
            self._build_lyrics(vl, text)
        else:
            vl.addWidget(KLabel(
                self.loc.t("no_lyrics"), style="dim",
                align=Qt.AlignmentFlag.AlignCenter,
            ))

        vl.addStretch()
        self._scr.setWidget(inner)
        root.addWidget(self._scr, 1)

        # bottom bar
        bar = QWidget()
        self._pv_bar = bar
        bar.setFixedHeight(72)
        bar.setStyleSheet(f"background:{self.tm.bg_alt};")

        bh = QHBoxLayout(bar)
        bh.setContentsMargins(32, 0, 32, 0)

        self._pvt = KLabel(
            "0:00.00", style="heading", font_size=22,
            align=Qt.AlignmentFlag.AlignCenter,
        )

        pp = KButton(
            f"{self.loc.t('play')} / {self.loc.t('pause')}",
            on_click=self._toggle_play,
            height=48,
            font_size=15,
        )
        pp.setFixedWidth(220)

        bh.addStretch()
        bh.addWidget(self._pvt)
        bh.addStretch()
        bh.addWidget(pp)

        root.addWidget(bar)
        return sc

    def _apply_theme_widgets(self):
        # panels
        if hasattr(self, "_left_pan") and self._left_pan:
            self._left_pan.setStyleSheet(f"background:{self.tm.bg_alt};")
        if hasattr(self, "_right_div") and self._right_div:
            self._right_div.setStyleSheet(f"background:{self.tm.border};")

        # cover
        if hasattr(self, "_cover") and self._cover:
            self._reset_cover_style()

        # editor
        if hasattr(self, "_ed") and self._ed:
            self._ed.setStyleSheet(
                f"QPlainTextEdit{{"
                f"  background:{self.tm.bg};"
                f"  color:{self.tm.fg};"
                f"  border:1.5px solid {self.tm.border};"
                f"  border-radius:8px;"
                f"  padding:12px;"
                f"  selection-background-color:{self.tm.fg};"
                f"  selection-color:{self.tm.bg};"
                f"}}"
            )

        # preview scroll
        if hasattr(self, "_scr") and self._scr:
            self._scr.setStyleSheet(
                f"QScrollArea{{background:{self.tm.bg};border:none;}}"
            )
        if hasattr(self, "_pv_bar") and self._pv_bar:
            self._pv_bar.setStyleSheet(f"background:{self.tm.bg_alt};")

        # preview labels recolor
        if hasattr(self, "_pv_labels") and hasattr(self, "_pv_cur"):
            for i, lbl in enumerate(self._pv_labels):
                if lbl is None:
                    continue
                if i == self._pv_cur:
                    lbl.setStyleSheet(f"color:{self.tm.fg};padding:4px 0px;")
                else:
                    lbl.setStyleSheet(f"color:{self.tm.fg_dim};padding:4px 0px;")

    def _build_lyrics(self, layout, text):
        for line in text.split("\n"):
            m = _TC.match(line)
            if m:
                ms = (int(m[1]) * 60_000
                      + int(m[2]) * 1_000
                      + int(m[3]) * 10)
                show = m[4] or ""
            else:
                ms = -1
                show = line.strip()

            self._pv_times.append(ms)

            if not show:
                spacer = QWidget()
                spacer.setFixedHeight(16)
                layout.addWidget(spacer)
                self._pv_labels.append(None)
                continue

            lbl = QLabel(show)
            lbl.setFont(Fonts.heading(22))
            lbl.setWordWrap(True)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"color:{self.tm.fg_dim};padding:4px 0px;")
            layout.addWidget(lbl)
            self._pv_labels.append(lbl)

    # ── preview tick ────────────────────────────────────

    def _tick_pv(self):
        pos = self.player.position
        self._pvt.setText(self._fmt(pos))

        cur = -1
        for i, t in enumerate(self._pv_times):
            if 0 <= t <= pos:
                cur = i

        if cur == self._pv_cur:
            return
        self._pv_cur = cur

        for i, lbl in enumerate(self._pv_labels):
            if lbl is None:
                continue
            if i == cur:
                lbl.setStyleSheet(f"color:{self.tm.fg};padding:4px 0px;")
                self._scr.ensureWidgetVisible(lbl, 50, 150)
            else:
                lbl.setStyleSheet(f"color:{self.tm.fg_dim};padding:4px 0px;")