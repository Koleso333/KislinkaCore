"""
Demo application — audio, graphics, widgets, custom settings, locale, storage.
Rebuilds UI on language change.
"""

import math

from core.scene import Scene, AnimationType
from core.permissions import PermissionManager, Permission
from core.locale import LocaleManager
from core.storage import StorageManager
from core.theme import ThemeManager
from widgets.klabel import KLabel
from widgets.kbutton import KButton
from widgets.ktextfield import KTextField
from widgets.ktoggle import KToggle
from widgets.kslider import KSlider
from widgets.kgrid import KRow, KColumn, KGrid
from audio.player import AudioPlayer
from audio.metadata import MetadataReader
from graphics.canvas import KCanvas
from graphics.shapes import Shapes, Color
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget, QFileDialog, QLabel, QScrollArea
from PyQt6.QtGui import QPainter, QPixmap
from PyQt6.QtCore import Qt


class DemoApp:

    def setup(self, app):
        self.app = app
        self.sm = app.scene_manager
        self.player = app.audio
        self.pm = app.permissions
        self.loc = app.locale
        self.storage = app.storage

        self._cover_pixmap: QPixmap | None = None
        self._track_text: str = self.loc.t("no_track")
        self._pos_text: str = "0:00 / 0:00"
        self._track_label: KLabel | None = None
        self._cover_label: QLabel | None = None
        self._pos_label: KLabel | None = None
        self._vol_label: KLabel | None = None
        self._demo_canvas: DemoCanvas | None = None

        # titlebar button
        app.window.titlebar.add_custom_button("back", self._go_home, icon_size=16)

        # custom settings tab
        self.pm.register_settings_tab(
            "demo_settings", "demo_settings", "settings",
            self._build_demo_settings, owner=Permission.APP,
        )

        # player signals
        self.player.position_changed.connect(self._on_position)
        self.player.finished.connect(self._on_finished)
        self.player.error.connect(self._on_error)

        # rebuild home on language change
        self.loc.changed.connect(self._on_locale_changed)

        self.sm.push(self._build_home(), AnimationType.NONE)

    def cleanup(self):
        self.player.stop()
        try:
            self.player.position_changed.disconnect(self._on_position)
            self.player.finished.disconnect(self._on_finished)
            self.player.error.disconnect(self._on_error)
            self.loc.changed.disconnect(self._on_locale_changed)
        except Exception:
            pass

    def _on_locale_changed(self):
        """Rebuild home when language changes."""
        # only rebuild if we're on home scene
        if self.sm.current and self.sm.current.name == "demo_home":
            # replace current scene with new home
            if self.sm.stack_depth == 1:
                # clear and rebuild
                self.sm._stack.clear()
                self.sm._current = None
                self.sm.push(self._build_home(), AnimationType.NONE)

    # ── HOME ────────────────────────────────────────

    def _build_home(self) -> Scene:
        scene = Scene("demo_home")
        lay = scene.scene_layout()
        lay.setContentsMargins(40, 20, 40, 20)
        lay.setSpacing(12)
        # в _build_home() добавь:
        lay.addWidget(KButton("Test Error", on_click=lambda: 1 / 0))

        lay.addWidget(KLabel("Demo App", style="heading", align=Qt.AlignmentFlag.AlignCenter))
        lay.addWidget(KLabel(
            "audio + graphics + locale + storage",
            style="dim", align=Qt.AlignmentFlag.AlignCenter,
        ))
        lay.addSpacing(10)

        row = QHBoxLayout()
        row.setSpacing(12)
        row.addWidget(KButton(self.loc.t("audio_demo"), on_click=self._go_audio))
        row.addWidget(KButton(self.loc.t("graphics_demo"), on_click=self._go_graphics))
        row.addWidget(KButton(self.loc.t("widgets_demo"), on_click=self._go_widgets))
        lay.addLayout(row)

        # show saved data
        saved = self.storage.app_get("username", "")
        if saved:
            lay.addSpacing(10)
            lay.addWidget(KLabel(
                f'{self.loc.t("saved_username")}: {saved}',
                style="dim", align=Qt.AlignmentFlag.AlignCenter,
            ))

        lay.addStretch()
        return scene

    def _go_home(self):
        if self.sm.is_animating:
            return
        if self.sm.stack_depth > 1:
            self.sm.pop(AnimationType.SLIDE_RIGHT)

    # ── AUDIO ───────────────────────────────────────

    def _go_audio(self):
        if not self.sm.is_animating:
            self.sm.push(self._build_audio_page(), AnimationType.SLIDE_LEFT)

    def _build_audio_page(self) -> Scene:
        scene = Scene("audio_demo")
        lay = scene.scene_layout()
        lay.setContentsMargins(40, 20, 40, 20)
        lay.setSpacing(12)

        lay.addWidget(KLabel(self.loc.t("audio_demo"), style="heading", align=Qt.AlignmentFlag.AlignCenter))

        self._track_label = KLabel(self._track_text, style="body", align=Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._track_label)

        self._cover_label = QLabel()
        self._cover_label.setFixedSize(120, 120)
        self._cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cover_label.setStyleSheet("background: transparent;")
        if self._cover_pixmap and not self._cover_pixmap.isNull():
            self._cover_label.setPixmap(self._cover_pixmap)

        cr = QHBoxLayout()
        cr.addStretch()
        cr.addWidget(self._cover_label)
        cr.addStretch()
        lay.addLayout(cr)

        self._pos_label = KLabel(self._pos_text, style="dim", align=Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._pos_label)

        br = QHBoxLayout()
        br.setSpacing(10)
        br.addWidget(KButton(self.loc.t("open"), on_click=self._open_file))
        br.addWidget(KButton(self.loc.t("play_pause"), on_click=self._toggle_play))
        br.addWidget(KButton(self.loc.t("stop"), on_click=self._stop))
        lay.addLayout(br)

        vr = QHBoxLayout()
        vr.setSpacing(10)
        vr.addWidget(KButton("Vol -", on_click=self._vol_down))
        self._vol_label = KLabel(f"{int(self.player.volume * 100)}%", style="dim", align=Qt.AlignmentFlag.AlignCenter)
        vr.addWidget(self._vol_label)
        vr.addWidget(KButton("Vol +", on_click=self._vol_up))
        lay.addLayout(vr)

        lay.addSpacing(10)
        lay.addWidget(KButton(self.loc.t("back"), on_click=self._back))
        lay.addStretch()
        return scene

    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(None, "Open Audio", "", "Audio (*.mp3 *.flac *.ogg *.wav *.m4a);;All (*)")
        if not path:
            return
        info = MetadataReader.read(path)
        display = info.title
        if info.artist:
            display = f"{info.artist} — {display}"
        self._track_text = display
        if self._track_label:
            self._track_label.setText(display)
        cover = MetadataReader.get_cover(path, size=120)
        if cover and not cover.isNull():
            self._cover_pixmap = cover
            if self._cover_label:
                self._cover_label.setPixmap(cover)
        else:
            self._cover_pixmap = None
            if self._cover_label:
                self._cover_label.clear()
        self.player.play(path)

    def _toggle_play(self):
        if self.player.is_playing:
            self.player.pause()
        elif self.player.is_paused:
            self.player.resume()

    def _stop(self):
        self.player.stop()
        self._track_text = self.loc.t("no_track")
        self._pos_text = "0:00 / 0:00"
        self._cover_pixmap = None
        if self._track_label:
            self._track_label.setText(self._track_text)
        if self._pos_label:
            self._pos_label.setText(self._pos_text)
        if self._cover_label:
            self._cover_label.clear()

    def _vol_up(self):
        v = min(1.0, self.player.volume + 0.1)
        self.player.set_volume(v)
        if self._vol_label:
            self._vol_label.setText(f"{int(v * 100)}%")

    def _vol_down(self):
        v = max(0.0, self.player.volume - 0.1)
        self.player.set_volume(v)
        if self._vol_label:
            self._vol_label.setText(f"{int(v * 100)}%")

    def _on_position(self, pos_ms: int):
        dur = self.player.duration
        self._pos_text = f"{pos_ms // 60000}:{(pos_ms // 1000) % 60:02d} / {dur // 60000}:{(dur // 1000) % 60:02d}"
        if self._pos_label:
            self._pos_label.setText(self._pos_text)

    def _on_finished(self):
        self._pos_text = "finished"
        if self._pos_label:
            self._pos_label.setText(self._pos_text)

    def _on_error(self, msg: str):
        self._track_text = f"Error: {msg}"
        if self._track_label:
            self._track_label.setText(self._track_text)

    def _back(self):
        if not self.sm.is_animating:
            self.sm.pop(AnimationType.SLIDE_RIGHT)

    # ── WIDGETS (Slider + Grids) ────────────────────

    def _go_widgets(self):
        if not self.sm.is_animating:
            self.sm.push(self._build_widgets_page(), AnimationType.SLIDE_LEFT)

    def _build_widgets_page(self) -> Scene:
        scene = Scene("widgets_demo")
        lay = scene.scene_layout()
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        tm = ThemeManager.instance()
        scroll.setStyleSheet(f"QScrollArea{{background:{tm.bg};border:none;}}")

        inner = QWidget()
        content = QVBoxLayout(inner)
        content.setContentsMargins(40, 20, 40, 30)
        content.setSpacing(16)

        content.addWidget(KLabel(
            self.loc.t("widgets_demo"), style="heading",
            align=Qt.AlignmentFlag.AlignCenter,
        ))

        # ────── SLIDERS SECTION ──────
        content.addSpacing(8)
        content.addWidget(KLabel(
            f"─── {self.loc.t('slider')} ───", style="dim",
            align=Qt.AlignmentFlag.AlignCenter,
        ))
        content.addSpacing(4)

        # Slider 1: Volume (0-100, step 1)
        vol_value_lbl = KLabel("50", style="body", align=Qt.AlignmentFlag.AlignCenter)
        vol_slider = KSlider(min_value=0, max_value=100, value=50, step=1)

        def on_vol(v):
            vol_value_lbl.setText(str(int(v)))

        vol_slider.value_changed.connect(on_vol)

        vol_row = KRow(spacing=12)
        vol_row.add(KLabel(self.loc.t("volume"), style="body"))
        vol_row.add(vol_slider, stretch=1)
        vol_row.add(vol_value_lbl)
        content.addWidget(vol_row)

        # Slider 2: Brightness (0.0-1.0, continuous)
        br_value_lbl = KLabel("0.50", style="body", align=Qt.AlignmentFlag.AlignCenter)
        br_slider = KSlider(min_value=0.0, max_value=1.0, value=0.5)

        def on_br(v):
            br_value_lbl.setText(f"{v:.2f}")

        br_slider.value_changed.connect(on_br)

        br_row = KRow(spacing=12)
        br_row.add(KLabel(self.loc.t("brightness"), style="body"))
        br_row.add(br_slider, stretch=1)
        br_row.add(br_value_lbl)
        content.addWidget(br_row)

        # Slider 3: Speed (0.25 - 3.0, step 0.25)
        sp_value_lbl = KLabel("1.00x", style="body", align=Qt.AlignmentFlag.AlignCenter)
        sp_slider = KSlider(min_value=0.25, max_value=3.0, value=1.0, step=0.25)

        def on_sp(v):
            sp_value_lbl.setText(f"{v:.2f}x")

        sp_slider.value_changed.connect(on_sp)

        sp_row = KRow(spacing=12)
        sp_row.add(KLabel(self.loc.t("speed"), style="body"))
        sp_row.add(sp_slider, stretch=1)
        sp_row.add(sp_value_lbl)
        content.addWidget(sp_row)

        # Slider 4: Opacity — connected to a live preview box
        preview_box = QWidget()
        preview_box.setFixedSize(60, 60)
        preview_box.setStyleSheet(
            f"background: {tm.fg}; border-radius: 8px;"
        )

        op_slider = KSlider(min_value=0.0, max_value=1.0, value=1.0)

        def on_op(v):
            alpha = int(v * 255)
            from PyQt6.QtGui import QColor
            c = QColor(tm.fg)
            c.setAlpha(alpha)
            preview_box.setStyleSheet(
                f"background: rgba({c.red()},{c.green()},{c.blue()},{alpha});"
                f"border-radius: 8px;"
            )

        op_slider.value_changed.connect(on_op)

        op_row = KRow(spacing=16, align="vcenter")
        op_row.add(KLabel(self.loc.t("opacity"), style="body"))
        op_row.add(op_slider, stretch=1)
        op_row.add(preview_box)
        content.addWidget(op_row)

        # ────── GRID LAYOUTS SECTION ──────
        content.addSpacing(16)
        content.addWidget(KLabel(
            f"─── {self.loc.t('grid_layouts')} ───", style="dim",
            align=Qt.AlignmentFlag.AlignCenter,
        ))
        content.addSpacing(4)

        # Demo 1: KRow
        content.addWidget(KLabel(self.loc.t("row_layout"), style="dim"))
        demo_row = KRow(spacing=8)
        for i in range(4):
            demo_row.add(self._make_cell(f"R{i+1}", tm))
        demo_row.add_stretch()
        content.addWidget(demo_row)

        # Demo 2: KGrid auto-placement 3 columns
        content.addSpacing(8)
        content.addWidget(KLabel(self.loc.t("grid_auto"), style="dim"))
        auto_grid = KGrid(columns=3, spacing=10, equal_columns=True)
        for i in range(6):
            auto_grid.add(self._make_cell(f"{self.loc.t('cell')} {i+1}", tm))
        content.addWidget(auto_grid)

        # Demo 3: KGrid manual placement
        content.addSpacing(8)
        content.addWidget(KLabel(self.loc.t("grid_manual"), style="dim"))
        man_grid = KGrid(columns=3, spacing=10, equal_columns=True)
        man_grid.place(self._make_cell(self.loc.t("wide"), tm, h=50), row=0, col=0, colspan=2)
        man_grid.place(self._make_cell(self.loc.t("tall"), tm, h=110), row=0, col=2, rowspan=2)
        man_grid.place(self._make_cell("A", tm, h=50), row=1, col=0)
        man_grid.place(self._make_cell("B", tm, h=50), row=1, col=1)
        content.addWidget(man_grid)

        # Demo 4: Nested KColumn inside KRow
        content.addSpacing(8)
        content.addWidget(KLabel("KRow + KColumn — nested", style="dim"))
        outer = KRow(spacing=12)

        left_col = KColumn(spacing=6)
        left_col.add(self._make_cell("L1", tm, h=40))
        left_col.add(self._make_cell("L2", tm, h=40))
        left_col.add(self._make_cell("L3", tm, h=40))

        right_col = KColumn(spacing=6)
        right_col.add(self._make_cell("R1", tm, h=60))
        right_col.add(self._make_cell("R2", tm, h=60))

        outer.add(left_col, stretch=1)
        outer.add(right_col, stretch=1)
        content.addWidget(outer)

        content.addSpacing(12)
        content.addWidget(KButton(self.loc.t("back"), on_click=self._back))
        content.addStretch()

        scroll.setWidget(inner)
        lay.addWidget(scroll, 1)
        return scene

    @staticmethod
    def _make_cell(text: str, tm, w: int = 0, h: int = 50) -> QWidget:
        """Helper: create a themed cell widget for grid demos."""
        cell = QWidget()
        if w > 0:
            cell.setFixedWidth(w)
        cell.setFixedHeight(h)
        cell.setMinimumWidth(60)
        cell.setStyleSheet(
            f"background: {tm.bg_alt};"
            f"border: 1.5px solid {tm.border};"
            f"border-radius: 8px;"
        )
        cl = QVBoxLayout(cell)
        cl.setContentsMargins(0, 0, 0, 0)
        lbl = KLabel(text, style="dim", font_size=12, align=Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(lbl)
        return cell

    # ── GRAPHICS ────────────────────────────────────

    def _go_graphics(self):
        if not self.sm.is_animating:
            self.sm.push(self._build_graphics_page(), AnimationType.SLIDE_LEFT)

    def _build_graphics_page(self) -> Scene:
        scene = Scene("graphics_demo")
        lay = scene.scene_layout()
        lay.setContentsMargins(20, 10, 20, 10)
        lay.setSpacing(8)

        lay.addWidget(KLabel(self.loc.t("graphics_demo"), style="heading", align=Qt.AlignmentFlag.AlignCenter))

        self._demo_canvas = DemoCanvas()
        self._demo_canvas.setMinimumHeight(350)
        self._demo_canvas.set_fps(60)
        lay.addWidget(self._demo_canvas, 1)

        def go_back():
            if not self.sm.is_animating:
                if self._demo_canvas:
                    self._demo_canvas.set_fps(0)
                self.sm.pop(AnimationType.SLIDE_RIGHT)

        lay.addWidget(KButton(self.loc.t("back"), on_click=go_back))
        return scene

    # ── CUSTOM SETTINGS ─────────────────────────────

    def _build_demo_settings(self) -> Scene:
        from widgets.kicon import load_svg_icon
        from core.theme import ThemeManager
        from PyQt6.QtWidgets import QPushButton
        from PyQt6.QtCore import QSize

        scene = Scene("demo_settings")
        lay = scene.scene_layout()
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # header
        tm = ThemeManager.instance()
        header = QWidget()
        header.setFixedHeight(50)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(8, 0, 8, 0)
        hl.setSpacing(8)

        back_btn = QPushButton()
        back_btn.setFixedSize(36, 36)
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setIconSize(QSize(16, 16))

        def go_back():
            if not self.sm.is_animating:
                self.sm.pop(AnimationType.SLIDE_RIGHT)

        back_btn.clicked.connect(go_back)

        def style_back():
            back_btn.setIcon(load_svg_icon("back", color=tm.fg, size=16))
            back_btn.setStyleSheet(f"QPushButton {{ background: transparent; border: none; border-radius: 6px; }} QPushButton:hover {{ background: {tm.hover}; }}")

        style_back()
        tm.changed.connect(style_back)
        hl.addWidget(back_btn)

        hl.addWidget(KLabel(self.loc.t("demo_settings"), style="heading", font_size=18, align=Qt.AlignmentFlag.AlignCenter), 1)
        hl.addSpacing(36)

        def style_h():
            header.setStyleSheet(f"background: {tm.bg}; border-bottom: 1px solid {tm.hover};")

        style_h()
        tm.changed.connect(style_h)
        lay.addWidget(header)

        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(24, 24, 24, 24)
        cl.setSpacing(16)

        # toggles
        for key, default in [("notifications", True), ("auto_play", False)]:
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(8, 8, 8, 8)
            rl.addWidget(KLabel(self.loc.t(key), style="body"))
            rl.addStretch()

            saved_val = self.storage.app_get(key, default)
            toggle = KToggle(checked=saved_val)

            def make_saver(k):
                def saver(v):
                    self.storage.app_set(k, v)
                return saver

            toggle.toggled.connect(make_saver(key))
            rl.addWidget(toggle)
            cl.addWidget(row)

        # username
        cl.addWidget(KLabel(self.loc.t("username"), style="dim"))
        tf = KTextField(placeholder=self.loc.t("enter_username"))
        saved_name = self.storage.app_get("username", "")
        if saved_name:
            tf.text = saved_name

        def save_username():
            self.storage.app_set("username", tf.text)

        tf.text_changed.connect(save_username)
        cl.addWidget(tf)

        cl.addSpacing(10)
        cl.addWidget(KLabel(self.loc.t("custom_settings_hint"), style="dim"))
        cl.addStretch()
        lay.addWidget(content, 1)

        return scene


class DemoCanvas(KCanvas):

    def __init__(self):
        super().__init__()
        self._time = 0
        self._mx = 0
        self._my = 0
        self._circles = []

    def on_draw(self, painter: QPainter):
        self._time += 1
        w = self.width()
        h = self.height()

        for i in range(5):
            phase = self._time * 0.02 + i * 1.2
            cx = w / 2 + math.cos(phase) * 120
            cy = h / 2 + math.sin(phase * 0.7) * 80
            r = 20 + math.sin(phase * 2) * 10
            alpha = int(150 + 100 * math.sin(phase))
            Shapes.circle(painter, cx, cy, r, color=Color.with_alpha(Color.WHITE, alpha))

        rw = 100 + math.sin(self._time * 0.03) * 30
        rh = 60 + math.cos(self._time * 0.04) * 20
        Shapes.rect(painter, w / 2 - rw / 2, h / 2 - rh / 2, rw, rh,
                    color=Color.with_alpha(Color.WHITE, 100),
                    border=Color.WHITE, border_width=2, radius=10)

        Shapes.circle(painter, self._mx, self._my, 15,
                      color=Color.with_alpha(Color.WHITE, 180),
                      border=Color.WHITE, border_width=2)

        for c in self._circles[:]:
            c["r"] += 2
            c["a"] -= 5
            if c["a"] <= 0:
                self._circles.remove(c)
            else:
                Shapes.circle(painter, c["x"], c["y"], c["r"],
                              color=Color.with_alpha(Color.WHITE, 0),
                              border=Color.with_alpha(Color.WHITE, c["a"]),
                              border_width=2, fill=False)

        Shapes.text(painter, f"FPS: 60  |  Frame: {self._time}", 10, 20,
                    color=Color.with_alpha(Color.WHITE, 150), size=11)

    def on_mouse_move(self, x, y):
        self._mx = x
        self._my = y

    def on_mouse_press(self, x, y, button):
        self._circles.append({"x": x, "y": y, "r": 10, "a": 200})