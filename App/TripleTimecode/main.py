"""
TripleTimecode — lyrics timecode editor for KislinkaCore.
"""

import re
from pathlib import Path

from PyQt6.QtWidgets import QWidget, QFileDialog, QLabel, QApplication
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QShortcut, QKeySequence

from core.scene import Scene, AnimationType
from core.fonts import Fonts
from widgets.klabel import KLabel
from widgets.kbutton import KButton
from widgets.ktoggle import KToggle
from widgets.ktextfield import KTextField
from widgets.kgrid import KRow, KColumn
from widgets.kpanel import KPanel
from widgets.kdivider import KDivider
from widgets.kscrollarea import KScrollArea
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
            self._ed.text = restore_text
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
                text = self._ed.text
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
            self._ed.set_placeholder(self.loc.t("lyrics_placeholder"))

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

        body = KRow(spacing=0)
        body.add(self._build_left())
        body.add(self._build_right(), stretch=1)

        root.addWidget(body, 1)
        return sc

    # ── left panel ──────────────────────────────────────

    def _build_left(self):
        pan = KPanel(
            "alt", fixed_width=320,
            spacing=0, margins=(20, 16, 20, 16),
        )
        self._left_pan = pan

        self._load_btn = KButton(self.loc.t("load_music"), on_click=self._load)
        pan.add(self._load_btn)
        pan.add_spacing(12)

        self._cover = QLabel()
        self._cover.setFixedSize(280, 280)
        self._cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._reset_cover_style()
        pan.add(self._cover, align="center")
        pan.add_spacing(12)

        self._title_lbl = KLabel(
            self.loc.t("no_track"), style="body",
            align=Qt.AlignmentFlag.AlignCenter,
        )
        pan.add(self._title_lbl)
        pan.add_spacing(8)

        self._time_lbl = KLabel(
            "0:00.00 / 0:00.00", style="heading", font_size=22,
            align=Qt.AlignmentFlag.AlignCenter,
        )
        pan.add(self._time_lbl)
        pan.add_spacing(16)

        row = KRow(spacing=10)
        self._play_btn = KButton(
            self.loc.t("play"), on_click=self._toggle_play, height=46,
        )
        self._stop_btn = KButton(
            self.loc.t("stop"), on_click=self._do_stop, height=46,
        )
        row.add(self._play_btn).add(self._stop_btn)
        pan.add(row)

        pan.add_stretch()
        return pan

    def _reset_cover_style(self):
        self._cover.setStyleSheet(
            f"background:{self.tm.bg};"
            f"border:1px solid {self.tm.border};"
            f"border-radius:8px;"
        )

    # ── right panel (editor + controls) ────────────────

    def _build_right(self):
        pan = KColumn(spacing=0, margins=(20, 16, 20, 16))
        self._right_pan = pan

        self._ed = KTextField(
            placeholder=self.loc.t("lyrics_placeholder"),
            multiline=True, font_size=14,
        )
        pan.add(self._ed, stretch=1)
        pan.add_spacing(12)

        pan.add(KDivider())
        pan.add_spacing(12)

        bottom = KColumn(spacing=8)

        mode_row = KRow(spacing=12)
        self._mode_lbl = KLabel(self.loc.t("edit_mode"), style="body")
        tog = KToggle(checked=False)
        tog.toggled.connect(self._set_mode)
        mode_row.add(self._mode_lbl).add_stretch().add(tog)
        bottom.add(mode_row)

        self._stamp_btn = KButton(
            self.loc.t("stamp"), on_click=self._stamp, height=42,
        )
        self._stamp_btn.setEnabled(False)
        bottom.add(self._stamp_btn)

        acts = KRow(spacing=8)
        self._undo_btn = KButton(
            self.loc.t("undo_stamp"), on_click=self._undo, height=38,
        )
        self._undo_btn.setEnabled(False)
        self._clear_btn = KButton(
            self.loc.t("clear_timecodes"), on_click=self._clear, height=38,
        )
        self._export_btn = KButton(
            self.loc.t("export"), on_click=self._copy, height=38,
        )
        acts.add(self._undo_btn).add(self._clear_btn).add(self._export_btn)
        bottom.add(acts)

        pan.add(bottom)
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
        self._ed.set_read_only(sync)
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
        lines = self._ed.lines()

        for i, ln in enumerate(lines):
            if not _TC.match(ln):
                self._history.append((i, ln))
                lines[i] = f"{tc} {ln}" if ln.strip() else tc
                self._ed.set_lines(lines)
                self._ed.set_cursor_line(min(i + 2, len(lines) - 1))

                self._undo_btn.setEnabled(True)
                return

    def _undo(self):
        if not self._history:
            return
        idx, orig = self._history.pop()
        lines = self._ed.lines()
        if idx < len(lines):
            lines[idx] = orig
            self._ed.set_lines(lines)
        self._undo_btn.setEnabled(bool(self._history))

    def _clear(self):
        self._ed.set_lines(
            [_TC_STRIP.sub("", l) for l in self._ed.lines()],
        )
        self._history.clear()
        self._undo_btn.setEnabled(False)

    def _copy(self):
        QApplication.clipboard().setText(self._ed.text)

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

        self._scr = KScrollArea()

        inner = KColumn(spacing=6, margins=(40, 60, 40, 250))

        self._pv_labels.clear()
        self._pv_times.clear()
        self._pv_cur = -2

        text = self._ed.text.strip()
        if text:
            self._build_lyrics(inner, text)
        else:
            inner.add(KLabel(
                self.loc.t("no_lyrics"), style="dim",
                align=Qt.AlignmentFlag.AlignCenter,
            ))

        inner.add_stretch()
        self._scr.set_content(inner)
        root.addWidget(self._scr, 1)

        # bottom bar
        bar = KPanel(
            "alt", direction="horizontal",
            fixed_height=72, margins=(32, 0, 32, 0),
        )
        self._pv_bar = bar

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

        bar.add_stretch().add(self._pvt).add_stretch().add(pp)

        root.addWidget(bar)
        return sc

    def _apply_theme_widgets(self):
        # cover (raw QLabel — manual theme)
        if hasattr(self, "_cover") and self._cover:
            self._reset_cover_style()

        # preview lyrics labels (raw QLabel — dynamic active/inactive color)
        if hasattr(self, "_pv_labels") and hasattr(self, "_pv_cur"):
            for i, lbl in enumerate(self._pv_labels):
                if lbl is None:
                    continue
                if i == self._pv_cur:
                    lbl.setStyleSheet(f"color:{self.tm.fg};padding:4px 0px;")
                else:
                    lbl.setStyleSheet(f"color:{self.tm.fg_dim};padding:4px 0px;")

    def _build_lyrics(self, container, text):
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
                container.add(spacer)
                self._pv_labels.append(None)
                continue

            lbl = QLabel(show)
            lbl.setFont(Fonts.heading(22))
            lbl.setWordWrap(True)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"color:{self.tm.fg_dim};padding:4px 0px;")
            container.add(lbl)
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