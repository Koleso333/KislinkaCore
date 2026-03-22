


# KislinkaCore

Application framework built on Python + PyQt6.

KislinkaCore is a runtime engine for desktop applications. You write the logic — the core handles the window, theming, navigation, audio, graphics, localization, and data storage.
Documentation is created for version 0.1.1 (and commits)
---

## Table of Contents

- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Architecture Overview](#architecture-overview)
- [Creating an Application](#creating-an-application)
  - [manifest.json](#manifestjson)
  - [Main Class](#main-class)
  - [Lifecycle](#lifecycle)
- [API Reference](#api-reference)
  - [KislinkaApp](#kislinkaapp)
  - [Scenes](#scenes)
  - [Widgets](#widgets)
    - [KLabel](#klabel)
    - [KButton](#kbutton)
    - [KTextField](#ktextfield)
    - [KToggle](#ktoggle)
    - [KCheckbox](#kcheckbox)
    - [KDropdown](#kdropdown)
    - [KSlider](#kslider)
    - [KProgressBar](#kprogressbar)
    - [KList](#klist)
    - [KTable](#ktable)
    - [KPanel](#kpanel)
    - [KDivider](#kdivider)
    - [KScrollArea](#kscrollarea)
    - [KSettingsItem](#ksettingsitem)
    - [KRow / KColumn / KGrid](#krow--kcolumn--kgrid)
    - [KDialog](#kdialog)
  - [Theme](#theme)
  - [Audio](#audio)
  - [Metadata](#metadata)
  - [Graphics](#graphics)
    - [KCanvas](#kcanvas)
    - [Shapes](#shapes)
    - [Color](#color)
    - [KImage](#kimage)
    - [Effects](#effects)
  - [Storage](#storage)
  - [Localization](#localization)
  - [Permissions](#permissions)
  - [Components](#components)
    - [Creating a Component](#creating-a-component)
    - [Hooks](#hooks)
    - [Accessing Components from Apps](#accessing-components-from-apps)
  - [Titlebar](#titlebar)
  - [Settings Tabs](#settings-tabs)
  - [Fonts](#fonts)
- [Theming](#theming)
- [Error Handling](#error-handling)
- [Launcher & Splash](#launcher--splash)
- [File Paths & Assets](#file-paths--assets)
- [Dependencies](#dependencies)
- [Examples](#examples)

---

## Quick Start

### 1. Install dependencies

```bash
pip install PyQt6 pygame mutagen
```

### 2. Add fonts

Download [Mitr Regular](https://fonts.google.com/specimen/Mitr) and [Roboto Bold](https://fonts.google.com/specimen/Roboto) from Google Fonts.

```
assets/fonts/Mitr-Regular.ttf
assets/fonts/Roboto-Bold.ttf
```

### 3. Create your app

```
App/
  MyApp/
    manifest.json
    main.py
```

**manifest.json:**

```json
{
    "name": "MyApp",
    "display_name": "My Application",
    "version": "1.0.0",
    "author": "Your Name",
    "main_class": "MyApp",
    "entry_point": "main.py",
    "window": {
        "width": 900,
        "height": 600
    }
}
```

**main.py:**

```python
from core.scene import Scene, AnimationType
from widgets.klabel import KLabel
from widgets.kbutton import KButton
from PyQt6.QtCore import Qt


class MyApp:
    def setup(self, app):
        self.app = app
        self.sm = app.scene_manager

        scene = Scene("home")
        lay = scene.scene_layout()
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(16)

        lay.addWidget(KLabel("Hello World", style="heading",
                              align=Qt.AlignmentFlag.AlignCenter))
        lay.addWidget(KButton("Click Me", on_click=self.on_click))

        self.sm.push(scene, AnimationType.NONE)

    def cleanup(self):
        pass

    def on_click(self):
        print("Clicked!")
```

### 4. Run

```bash
python main.py
```

---

## Project Structure

```
KislinkaCore/
│
├── main.py                    # Entry point
├── requirements.txt
│
├── core/                      # Engine
│   ├── app.py                 # KislinkaApp — main controller
│   ├── window.py              # Frameless window
│   ├── titlebar.py            # Custom title bar
│   ├── scene.py               # Scene manager + transitions
│   ├── theme.py               # Dark / Light theme system
│   ├── fonts.py               # Font loader (Mitr + Roboto)
│   ├── permissions.py         # Core / App / User permissions
│   ├── settings.py            # Built-in settings panel
│   ├── loader.py              # App scanner + loader
│   ├── storage.py             # Persistent data (JSON in AppData)
│   ├── locale.py              # Localization (independent core/app)
│   ├── hooks.py               # Hook system for components
│   ├── component.py           # Base component class
│   ├── component_manager.py   # Component scanner + loader
│   ├── error_handler.py       # Global error catcher + error window
│   ├── launcher.py            # Multi-app launcher window
│   ├── splash.py              # Splash overlay animation
│   ├── core_info.json         # Core metadata
│   └── locales/
│       ├── en.json            # English strings
│       └── ru.json            # Russian strings
│
├── components/                # Core components (plugins)
│   └── MyComponent/
│       ├── manifest.json
│       └── component.py
│
├── widgets/                   # UI components
│   ├── kbutton.py             # Button with scale animation
│   ├── klabel.py              # Label with auto font
│   ├── ktextfield.py          # Text input (single/multi line)
│   ├── ktoggle.py             # iOS-style toggle switch
│   ├── kslider.py             # Animated horizontal slider
│   ├── kgrid.py               # KRow, KColumn, KGrid layout containers
│   ├── kpanel.py              # Themed container panel
│   ├── kdivider.py            # Themed separator line
│   ├── kscrollarea.py         # Themed scroll area
│   ├── kicon.py               # SVG icon loader
│   └── ksettingsitem.py       # Settings list item
│
├── audio/                     # Audio system
│   ├── player.py              # Playback (pygame.mixer)
│   └── metadata.py            # Tags + cover art (mutagen)
│
├── graphics/                  # Drawing API
│   ├── canvas.py              # Custom paint widget
│   ├── shapes.py              # Primitives (rect, circle, etc.)
│   ├── image.py               # Image load / transform
│   └── effects.py             # Tint, opacity, invert, round corners
│
├── assets/
│   ├── fonts/
│   │   ├── Mitr-Regular.ttf
│   │   └── Roboto-Bold.ttf
│   └── bin/
│       ├── ffmpeg.exe         # Optional, for m4a support
│       └── ffprobe.exe        # Optional
│
└── App/                       # Your applications
    └── MyApp/
        ├── manifest.json
        ├── main.py
        ├── assets/            # App-specific resources
        └── locales/           # App translations
            ├── en.json
            └── ru.json
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│                KislinkaWindow                    │
│  ┌─────────────────────────────────────────────┐│
│  │ TitleBar: [⚙][custom] ... Title ... [—][✕] ││
│  ├─────────────────────────────────────────────┤│
│  │                                             ││
│  │              SceneManager                   ││
│  │        ┌─────────────────────┐              ││
│  │        │      Scene          │              ││
│  │        │  (your content)     │              ││
│  │        └─────────────────────┘              ││
│  │                                             ││
│  └─────────────────────────────────────────────┘│
└─────────────────────────────────────────────────┘
```

**Flow:**

1. `main.py` creates `KislinkaApp`
2. Core scans `components/` and loads components
3. Core scans `App/` for applications
4. If 1 app → launches directly with splash
5. If 2+ apps → shows Launcher, user picks one
6. If 0 apps → shows Error window
7. Core creates `KislinkaWindow`, `SceneManager`, `SettingsPanel`
8. Core calls `YourApp.setup(app)` — you build your scenes
9. On exit, core calls `YourApp.cleanup()`

---

## Creating an Application

### manifest.json

```json
{
    "name": "UniqueAppName",
    "display_name": "Display Name Shown in Title",
    "version": "1.0.0",
    "author": "Author Name",
    "main_class": "ClassName",
    "entry_point": "main.py",
    "window": {
        "width": 900,
        "height": 600
    },
    "permissions": {
        "audio": true,
        "graphics": true
    }
}
```

| Field | Required | Description |
|---|---|---|
| `name` | Yes | Unique internal name (no spaces) |
| `display_name` | Yes | Shown in title bar and About |
| `version` | Yes | Semantic version |
| `author` | Yes | Shown in About |
| `main_class` | Yes | Class name in entry_point file |
| `entry_point` | No | Default: `main.py` |
| `window.width` | No | Default: 900 |
| `window.height` | No | Default: 600 |
| `permissions` | No | Feature flags |

### Main Class

```python
class MyApp:
    def setup(self, app):
        """
        Called by core after loading.

        app: KislinkaApp instance with access to:
            app.scene_manager   — SceneManager
            app.theme_manager   — ThemeManager
            app.audio           — AudioPlayer
            app.storage         — StorageManager
            app.locale          — LocaleManager
            app.permissions     — PermissionManager
            app.window          — KislinkaWindow
        """
        pass

    def cleanup(self):
        """
        Called before app is unloaded.
        Stop audio, save data, disconnect signals here.
        """
        pass
```

### Lifecycle

```
1. Core calls  setup(app)
   → Build scenes, connect signals, load data

2. App runs — user interacts with scenes

3. Core calls  cleanup()
   → Stop audio, save state, disconnect signals
   (also called on language change before reload)
```

---

## API Reference

### KislinkaApp

Access in `setup(self, app)`:

```python
app.scene_manager    # SceneManager — push/pop scenes
app.theme_manager    # ThemeManager — toggle theme
app.audio            # AudioPlayer  — play music
app.storage          # StorageManager — save/load data
app.locale           # LocaleManager — translate strings
app.permissions      # PermissionManager — register settings tabs
app.window           # KislinkaWindow — access titlebar, set size
app.hooks            # HookManager — register/emit hooks
app.components       # ComponentManager — access loaded components
```

---

### Scenes

Scenes are full-screen views. Push, pop, and replace them with slide animations.

```python
from core.scene import Scene, AnimationType
from PyQt6.QtCore import Qt

# Create a scene
scene = Scene("my_scene")
lay = scene.scene_layout()  # QVBoxLayout
lay.setContentsMargins(40, 20, 40, 20)
lay.setSpacing(12)
lay.addWidget(some_widget)

# Navigation
sm = app.scene_manager

sm.push(scene, AnimationType.SLIDE_LEFT)     # push with slide →
sm.push(scene, AnimationType.SLIDE_RIGHT)    # push with slide ←
sm.push(scene, AnimationType.NONE)           # push instantly

sm.pop(AnimationType.SLIDE_RIGHT)            # go back
sm.replace(scene, AnimationType.SLIDE_LEFT)  # replace current

# Properties
sm.current          # current Scene or None
sm.stack_depth      # int
sm.is_animating     # bool — check before push/pop!
```

**Animation Types:**

| Type | Effect |
|---|---|
| `AnimationType.NONE` | Instant switch |
| `AnimationType.SLIDE_LEFT` | New scene slides in from right |
| `AnimationType.SLIDE_RIGHT` | New scene slides in from left |

**Always check `is_animating` before navigation:**

```python
def go_to_page2(self):
    if not self.sm.is_animating:
        self.sm.push(self.build_page2(), AnimationType.SLIDE_LEFT)
```

**Subclassing Scene:**

```python
class MyScene(Scene):
    def __init__(self):
        super().__init__("my_scene")
        # add widgets to self.scene_layout()

    def on_enter(self):
        """Called when scene becomes visible."""
        print("entered")

    def on_leave(self):
        """Called when scene is hidden."""
        print("left")
```

---

### Widgets

#### KLabel

```python
from widgets.klabel import KLabel
from PyQt6.QtCore import Qt

# Styles: "heading" (Mitr font), "body", "dim", "small" (Roboto)
label = KLabel("Title", style="heading")
label = KLabel("Regular text", style="body")
label = KLabel("Subtitle", style="dim")
label = KLabel("Small note", style="small")

# Custom size
label = KLabel("Custom", style="heading", font_size=36)

# Alignment
label = KLabel("Centered", style="body", align=Qt.AlignmentFlag.AlignCenter)
```

| Style | Font | Default Size | Color |
|---|---|---|---|
| `heading` | Mitr | 28pt | White |
| `body` | Roboto Bold | 14pt | White |
| `dim` | Roboto Bold | 13pt | Gray |
| `small` | Roboto Bold | 11pt | Gray |

#### KButton

```python
from widgets.kbutton import KButton

# Basic
btn = KButton("Click Me", on_click=my_function)

# Customized
btn = KButton(
    "Submit",
    on_click=my_function,
    height=50,
    font_size=16,
    enabled=True,
)

# Disable
btn.setEnabled(False)   # greys out, cursor changes
btn.setEnabled(True)    # re-enable
```

Design:
- White background, black text (dark theme) — inverted in light
- Rounded corners (8px)
- Scale 0.95 press animation (100ms ease-in)
- Disabled: greyed out, no pointer cursor

#### KTextField

```python
from widgets.ktextfield import KTextField

# Single line
tf = KTextField(placeholder="Enter name...")

# Multi line
tf = KTextField(
    placeholder="Write something...",
    multiline=True,
    fixed_height=120,
)

# Options
tf = KTextField(
    placeholder="Max 50 chars",
    max_length=50,
    font_size=16,
)

# Read / write
text = tf.text              # get text
tf.text = "Hello"           # set text
tf.clear()                  # clear
tf.set_read_only(True)      # read-only mode

# Events
tf.text_changed.connect(lambda: print(tf.text))
```

Design:
- Black background, white 1.5px border, white text
- Blinking cursor (800ms cycle)
- Placeholder text in gray

#### KToggle

```python
from widgets.ktoggle import KToggle

toggle = KToggle(checked=False)
toggle.toggled.connect(lambda v: print(f"Toggle: {v}"))

# Read / write
is_on = toggle.checked
toggle.checked = True
```

Design:
- iOS-style switch
- Animated knob slide (150ms)
- White track when on, gray when off (dark theme)

#### KCheckbox

```python
from widgets.kcheckbox import KCheckbox

# Basic
checkbox = KCheckbox("Remember me", checked=False)
checkbox.toggled.connect(lambda v: print(f"Checked: {v}"))

# Read / write
is_checked = checkbox.isChecked()
checkbox.setChecked(True)
```

Design:
- Custom painted box with rounded corners
- Unchecked: empty box with cross icon (✕)
- Checked: filled box with checkmark icon (✓)
- Icons adapt to theme: white on dark, black on light
- No hover effect

#### KDropdown

```python
from widgets.kdropdown import KDropdown

# Basic
dropdown = KDropdown(["Option A", "Option B", "Option C"])

# With placeholder
dropdown = KDropdown(placeholder="Select an option...")

# Editable
dropdown = KDropdown(["A", "B"], editable=True)

# Set items dynamically
dropdown.set_items(["New A", "New B", "New C"])

# Read / write
idx = dropdown.currentIndex()
val = dropdown.currentText()
dropdown.setCurrentIndex(1)
```

Design:
- Themed combobox with animated arrow rotation
- Arrow rotates 180° when popup opens/closes
- Rounded corners (6px)
- Theme-aware colors and selection highlight

#### KSlider

```python
from widgets.kslider import KSlider

# Basic
slider = KSlider(min_val=0, max_val=100, value=50)
slider.value_changed.connect(lambda v: print(v))

# Stepped
slider = KSlider(min_val=0, max_val=10, value=5, step=1)

# Read / write
val = slider.value
slider.value = 75
```

Design:
- Horizontal track with animated round knob
- Knob slides with 120ms ease-out animation
- Mouse wheel support (step or 1% increments)
- Theme-aware colors

#### KProgressBar

```python
from widgets.kprogressbar import KProgressBar

# Basic
progress = KProgressBar(value=50)

# With range
progress = KProgressBar(minimum=0, maximum=1000, value=250)

# Show percentage text
progress = KProgressBar(value=75, show_text=True)

# Read / write
val = progress.value()
progress.setValue(80)
```

Design:
- Fully rounded fill (caps are round)
- Text color inverts on filled area for contrast
- Theme-aware colors

#### KList

```python
from widgets.klist import KList

# Basic
lst = KList(["Item 1", "Item 2", "Item 3"])

# Set items dynamically
lst.set_items(["A", "B", "C"])

# Selection
item = lst.currentItem()
lst.itemClicked.connect(lambda item: print(item.text()))
```

Design:
- Themed QListWidget with rounded corners
- Hover and selection highlight
- No grid lines, clean appearance

#### KTable

```python
from widgets.ktable import KTable

# Basic
table = KTable(rows=3, columns=2, headers=["Name", "Value"])

# Set cell content
table.setItem(0, 0, QTableWidgetItem("Row 1"))
table.setItem(0, 1, QTableWidgetItem("100"))

# Headers stretch to fill width
table.set_headers(["Col A", "Col B", "Col C"])
```

Design:
- Themed QTableWidget with hidden vertical header
- Columns stretch to fill width
- Selection highlight inverts colors
- Clean header styling with bottom border

#### KPanel

```python
from widgets.kpanel import KPanel

# Default background
panel = KPanel()

# Elevated surface
panel = KPanel("alt")

# Sidebar with border
sidebar = KPanel("alt", fixed_width=320, border=True, radius=8)

# Horizontal toolbar
toolbar = KPanel("alt", direction="horizontal", spacing=8, margins=(16, 0, 16, 0))

# Fluent API
panel = KPanel("alt", spacing=12, margins=(20, 16, 20, 16))
panel.add(label).add_spacing(8).add(button).add_stretch()
```

| Variant | Background |
|---|---|
| `"default"` | `theme.bg` |
| `"alt"` | `theme.bg_alt` |
| `"custom"` | `custom_bg` color |

#### KDivider

```python
from widgets.kdivider import KDivider

# Horizontal line (default)
div = KDivider()

# Vertical separator
div = KDivider(direction="vertical")

# Custom thickness / color
div = KDivider(thickness=2, color_key="fg_dim")
```

#### KScrollArea

```python
from widgets.kscrollarea import KScrollArea

scroll = KScrollArea()
scroll.set_content(my_widget)
```

Auto-themed background, horizontal scroll off by default.

#### KSettingsItem

```python
from widgets.ksettingsitem import KSettingsItem

# Basic
item = KSettingsItem("Theme", icon_name="settings")
item.clicked.connect(lambda: print("Clicked!"))

# Without arrow
item = KSettingsItem("Version 1.0", icon_name="info", show_arrow=False)
```

Design:
- iOS-style settings row with rounded corners
- Optional icon on the left
- Optional arrow (›) on the right
- Hover and press states
- Bottom separator line

#### KRow / KColumn / KGrid

```python
from widgets.kgrid import KRow, KColumn, KGrid

# Horizontal row
row = KRow(spacing=12)
row.add(btn_a).add(btn_b).add_stretch()

# Vertical column
col = KColumn(spacing=8, margins=(20, 10, 20, 10))
col.add(title, stretch=0).add(editor, stretch=1).add_stretch()

# Auto-placement grid
grid = KGrid(columns=3, spacing=12, equal_columns=True)
for w in widgets:
    grid.add(w)

# Manual grid placement
grid = KGrid(columns=4)
grid.place(header, row=0, col=0, colspan=4)
grid.place(sidebar, row=1, col=0, rowspan=2)
```

All containers use transparent background and fluent `.add()` chaining.

#### KDialog

```python
from widgets.kdialog import KDialog

dialog = KDialog(app.window.body, "Delete File", "Are you sure you want to delete this?")

# Add buttons
dialog.add_button("Cancel", dialog.reject)
dialog.add_button("Delete", self.on_confirm)

# Show with animation
dialog.show_dialog()
```

Design:
- Semi-transparent full-screen overlay (blocks clicks underneath)
- Centered modal box with theme-aware background/border
- Scale and fade-in / fade-out animations
- Pressing Escape calls `reject()`

---

### Theme

```python
tm = app.theme_manager

# Toggle
tm.toggle()

# Set directly
tm.set_theme("dark")
tm.set_theme("light")

# Read
tm.is_dark          # bool
tm.theme.name       # "dark" or "light"
tm.bg               # "#000000" or "#FFFFFF"
tm.fg               # "#FFFFFF" or "#000000"
tm.bg_alt           # elevated surface
tm.fg_dim           # secondary text
tm.border           # outline color
tm.disabled         # greyed out
tm.hover            # hover overlay
tm.scrollbar        # scrollbar thumb

# Listen for changes
tm.changed.connect(my_callback)
```

| Property | Dark | Light |
|---|---|---|
| `bg` | `#000000` | `#FFFFFF` |
| `fg` | `#FFFFFF` | `#000000` |
| `bg_alt` | `#0D0D0D` | `#F2F2F2` |
| `fg_dim` | `#666666` | `#999999` |
| `border` | `#FFFFFF` | `#000000` |
| `disabled` | `#3A3A3A` | `#C5C5C5` |
| `hover` | `#1A1A1A` | `#E5E5E5` |

---

### Audio

```python
player = app.audio

# Play
player.play("path/to/track.mp3")
player.play("track.m4a")           # requires ffmpeg in assets/bin/

# Controls
player.pause()
player.resume()
player.toggle_pause()
player.stop()

# Volume (0.0 — 1.0)
player.set_volume(0.5)
vol = player.volume

# Seek (milliseconds)
player.seek(30000)   # jump to 30 seconds

# State
player.is_playing    # bool
player.is_paused     # bool
player.position      # int (ms)
player.duration       # int (ms)
player.current_file  # Path or None

# Signals
player.started.connect(on_start)
player.paused.connect(on_pause)
player.resumed.connect(on_resume)
player.stopped.connect(on_stop)
player.finished.connect(on_end)
player.position_changed.connect(lambda ms: update_progress(ms))
player.duration_changed.connect(lambda ms: set_total(ms))
player.volume_changed.connect(lambda v: update_slider(v))
player.error.connect(lambda msg: show_error(msg))
```

**Supported formats:**

| Format | Support |
|---|---|
| MP3 | Native |
| OGG | Native |
| WAV | Native |
| FLAC | Native |
| M4A/AAC | Via ffmpeg conversion |

Place `ffmpeg.exe` and `ffprobe.exe` in `assets/bin/` for M4A support.

---

### Metadata

```python
from audio.metadata import MetadataReader

# Read tags
info = MetadataReader.read("track.mp3")
info.title           # str
info.artist          # str
info.album           # str
info.year            # str
info.genre           # str
info.track_number    # str
info.duration_ms     # int
info.duration_str    # "3:45"
info.has_cover       # bool
info.file_path       # str

# Get cover art
pixmap = MetadataReader.get_cover("track.mp3", size=200)  # QPixmap or None
raw_bytes = MetadataReader.get_cover_bytes("track.mp3")   # bytes or None
```

---

### Graphics

#### KCanvas

Custom drawing widget. Subclass and override `on_draw()`.

```python
from graphics.canvas import KCanvas
from graphics.shapes import Shapes, Color
from PyQt6.QtGui import QPainter
from PyQt6.QtCore import Qt


class MyCanvas(KCanvas):
    def __init__(self):
        super().__init__()
        self._time = 0

    def on_draw(self, painter: QPainter):
        self._time += 1
        Shapes.circle(painter, 100, 100, 50, color=Color.WHITE)
        Shapes.text(painter, f"Frame: {self._time}", 10, 20)

    def on_mouse_press(self, x: int, y: int, button: Qt.MouseButton):
        print(f"Click at {x}, {y}")

    def on_mouse_move(self, x: int, y: int):
        pass

    def on_key_press(self, key: int, text: str):
        pass


# Usage
canvas = MyCanvas()
canvas.set_fps(60)       # auto-refresh at 60 FPS
canvas.set_fps(0)        # manual refresh only
canvas.refresh()         # manual repaint
canvas.set_background("#111111")  # custom bg (default: theme bg)
```

**Available overrides:**

| Method | When |
|---|---|
| `on_draw(painter)` | Every paint cycle |
| `on_mouse_press(x, y, button)` | Mouse button down |
| `on_mouse_release(x, y, button)` | Mouse button up |
| `on_mouse_move(x, y)` | Mouse moved |
| `on_key_press(key, text)` | Key pressed |
| `on_key_release(key, text)` | Key released |

#### Shapes

All methods are static. First argument is always `QPainter`.

```python
from graphics.shapes import Shapes, Color

# Rectangle
Shapes.rect(painter, x, y, width, height,
    color=Color.WHITE,       # fill color
    border="#FF0000",        # outline (None = no outline)
    border_width=2.0,
    radius=8,                # corner radius (0 = sharp)
    fill=True,               # False = outline only
)

# Circle
Shapes.circle(painter, cx, cy, radius,
    color=Color.WHITE,
    border=None,
    border_width=1.0,
    fill=True,
)

# Ellipse
Shapes.ellipse(painter, x, y, width, height, color=Color.WHITE)

# Line
Shapes.line(painter, x1, y1, x2, y2,
    color=Color.WHITE,
    width=1.0,
)

# Polygon
Shapes.polygon(painter,
    [(100, 100), (200, 50), (200, 150)],
    color=Color.WHITE,
)

# Triangle (shorthand)
Shapes.triangle(painter, x1, y1, x2, y2, x3, y3, color=Color.WHITE)

# Arc
Shapes.arc(painter, x, y, width, height,
    start_angle=0,     # degrees
    span_angle=180,    # degrees
    color=Color.WHITE,
    line_width=2.0,
)

# Text
Shapes.text(painter, "Hello", x, y,
    color=Color.WHITE,
    size=14,
    font_family="Roboto",
    bold=True,
    max_width=200,     # 0 = no limit
)

# Point (small filled circle)
Shapes.point(painter, x, y, color=Color.WHITE, size=4.0)
```

#### Color

```python
from graphics.shapes import Color

# Constants
Color.BLACK, Color.WHITE, Color.RED, Color.GREEN, Color.BLUE
Color.YELLOW, Color.CYAN, Color.MAGENTA
Color.GRAY, Color.DARK_GRAY, Color.LIGHT_GRAY
Color.TRANSPARENT

# Constructors
color = Color.from_rgb(255, 128, 0)          # RGBA
color = Color.from_hex("#FF8800")             # hex
color = Color.with_alpha("#FFFFFF", 128)      # white at 50% opacity
color = Color.with_alpha(Color.RED, 200)      # red at ~78% opacity
```

#### KImage

```python
from graphics.image import KImage

# Load
img = KImage("path/to/image.png")
img = KImage.from_bytes(raw_bytes)
img = KImage.create(200, 200, fill="#000000")  # blank image

# Properties
img.width, img.height, img.size  # (w, h)
img.is_valid                     # bool
img.pixmap                       # QPixmap

# Draw on canvas
img.draw(painter, x, y)
img.draw(painter, x, y, width=100, height=100)         # scaled
img.draw(painter, x, y, opacity=0.5)                    # transparent
img.draw_centered(painter, cx, cy, width=100, height=100)
img.draw_tiled(painter, x, y, width, height)

# Transformations (return new KImage)
scaled = img.scaled(200, 200, keep_aspect=True)
scaled = img.scaled_to_width(300)
scaled = img.scaled_to_height(200)
rotated = img.rotated(45)              # degrees
flipped = img.flipped(horizontal=True)
flipped = img.flipped(vertical=True)
cropped = img.cropped(x, y, w, h)
gray = img.to_grayscale()

# Save
img.save("output.png", quality=90)
```

#### Effects

```python
from graphics.effects import Effects

tinted = Effects.tint(img, "#FF0000", strength=0.5)
faded = Effects.opacity(img, 0.5)
inverted = Effects.invert(img)
rounded = Effects.round_corners(img, radius=20)
```

---

### Storage

Persistent JSON storage. Core saves to `%LOCALAPPDATA%/KislinkaCore/`, app saves to `%LOCALAPPDATA%/KislinkaCore/<app_name>/`.

```python
storage = app.storage

# App data (scoped to current app)
storage.app_set("username", "Kislinka")
storage.app_set("volume", 0.8)
storage.app_set("playlist", ["a.mp3", "b.mp3"])

name = storage.app_get("username", "")          # default = ""
vol = storage.app_get("volume", 1.0)

storage.app_delete("username")
storage.app_clear()                              # delete all app data
all_data = storage.app_get_all()                 # dict

# Core data (used by engine, but readable)
theme = storage.core_get("theme", "dark")
lang = storage.core_get("language", "en")
```

Values can be any JSON-serializable type: `str`, `int`, `float`, `bool`, `list`, `dict`, `None`.

---

### Localization

Core and app have **independent** language settings. If you select a language that exists only in core, the app stays on its previous language and vice versa.

**Core locales:** `core/locales/en.json`, `core/locales/ru.json`

**App locales:** `App/MyApp/locales/en.json`, `App/MyApp/locales/ru.json`

```python
loc = app.locale

# Translate
text = loc.t("my_key")                    # returns translated string
text = loc.t("my_key", "Fallback text")   # custom fallback

# Current languages
loc.core_language    # "en"
loc.app_language     # "ru" (can differ from core!)
loc.language         # alias for core_language

# Available languages
langs = loc.available_languages()
# [
#   {"code": "en", "name": "English", "in_core": True, "in_app": True, "availability": "both"},
#   {"code": "ru", "name": "Русский", "in_core": True, "in_app": True, "availability": "both"},
#   {"code": "es", "name": "Español", "in_core": False, "in_app": True, "availability": "only_in_app"},
# ]

# Listen for changes (called on language change + app reload)
loc.changed.connect(my_callback)
```

**Translation lookup order:**

1. App strings in `app_language`
2. Core strings in `core_language`
3. App strings in English
4. Core strings in English
5. Fallback or key itself

**App locale file example** (`App/MyApp/locales/en.json`):

```json
{
    "greeting": "Hello!",
    "play": "Play",
    "pause": "Pause",
    "settings_title": "App Settings"
}
```

**Important:** When the user changes language in settings, core calls `cleanup()` then `setup()` on your app. You don't need to handle language changes manually — just use `loc.t()` everywhere and it works.

---

### Permissions

```python
pm = app.permissions

# Register a custom settings tab
pm.register_settings_tab(
    "my_tab_id",              # unique ID
    "my_settings_title",      # locale key or display name
    "settings",               # icon name
    self.build_my_settings,   # callable() → Scene
    owner=Permission.APP,
)

# Remove a tab
pm.remove_settings_tab("my_tab_id")

# Register a widget for permission control
from core.permissions import Permission
pm.register_widget("my_button", btn, owner=Permission.APP)
pm.set_enabled("my_button", False)   # grey out
pm.set_enabled("my_button", True)    # re-enable

# Check permissions
pm.is_allowed(Permission.APP, "add_settings_tab")   # True
pm.is_allowed(Permission.USER, "change_window_size") # False
```

**Permission levels:**

| Level | Can do |
|---|---|
| `CORE` | Everything. Owns Themes, Language, About tabs |
| `APP` | Add settings tabs, disable widgets, change window size |
| `USER` | Toggle theme |

Apps **cannot** modify or remove core-owned settings tabs.

---

### Components

Components are plugins that extend or modify the core. They live in `components/` at the project root.

#### Creating a Component

```
components/
  MyComponent/
    manifest.json
    component.py
```

**manifest.json:**

```json
{
    "name": "MyComponent",
    "display_name": "My Component",
    "version": "1.0.0",
    "author": "Author",
    "description": "What it does",
    "main_class": "MyComponent",
    "entry_point": "component.py",
    "dependencies": [],
    "priority": 100,
    "hidden_imports": []
}
```

| Field | Required | Description |
|---|---|---|
| `name` | Yes | Unique internal name |
| `display_name` | Yes | Human-readable name |
| `version` | Yes | Semantic version |
| `main_class` | Yes | Class name in entry point file |
| `entry_point` | No | Default: `component.py` |
| `dependencies` | No | List of component names required before this one |
| `priority` | No | Load order — lower = loaded first (default: 100) |
| `hidden_imports` | No | List of Python modules to include in frozen exe (for PyInstaller) |

**component.py:**

```python
from core.component import KislinkaComponent

class MyComponent(KislinkaComponent):

    def on_register(self, core):
        self.core = core
        # register hooks, read config, init state

    def on_ready(self):
        # all components loaded — safe to reference others
        pass

    def on_app_setup(self, app_instance):
        # user app's setup() completed
        pass

    def on_app_cleanup(self):
        # before user app's cleanup()
        pass

    def on_unload(self):
        # clean up resources (hooks auto-unregistered by owner name)
        pass
```

**Lifecycle:**

```
scan → load → on_register(core) → on_ready()
              → on_app_setup(app) → ... → on_app_cleanup()
              → on_unload()
```

#### Dynamic Imports & hidden_imports

If your component uses `importlib` to dynamically load modules (e.g., loading plugins from a `modules/` folder), PyInstaller won't detect these imports during static analysis. This causes `ImportError` or `AttributeError` at runtime in frozen executables.

**Solution:** Add all dynamically imported modules to `hidden_imports` in your `manifest.json`:

```json
{
    "name": "KislinkaWinapi",
    "hidden_imports": [
        "win32api",
        "win32con",
        "pywintypes",
        "pythoncom"
    ]
}
```

**Example component with dynamic loading:**

```python
import importlib.util
import sys
from pathlib import Path
from core.component import KislinkaComponent

# Handle PyInstaller frozen path
if getattr(sys, 'frozen', False):
    _DIR = Path(sys._MEIPASS) / "components" / "MyComponent"
else:
    _DIR = Path(__file__).parent

def _load_module(name):
    path = _DIR / "modules" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"mycomp.{name}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

class MyComponent(KislinkaComponent):
    def on_register(self, core):
        # These modules must be listed in hidden_imports!
        self.feature = _load_module("feature")
```

**Important:** When using `sys._MEIPASS` for frozen apps, always construct paths relative to the extracted bundle root, not `__file__`.

#### Hooks

Components interact with the core through hooks — events that the core emits at key points.

**Two types:**

| Type | Description | Example |
|---|---|---|
| `emit` | Notification (fire-and-forget) | `hooks.emit("after_theme_change", theme_name="dark")` |
| `filter` | Value passes through chain — each handler can modify it | `qss = hooks.filter("core_qss", qss_string, theme=t)` |

**Registering hooks:**

```python
def on_register(self, core):
    core.hooks.register(
        "after_theme_change",     # event name
        self.on_theme,            # callback
        priority=100,             # lower = called first
        owner="MyComponent",      # auto-cleanup on unload
    )

def on_theme(self, **kwargs):
    print(f"Theme is now: {kwargs['theme_name']}")
```

**Available hooks (emit):**

| Hook | kwargs | When |
|---|---|---|
| `core_ready` | — | All components loaded, before app scan |
| `on_window_created` | `window` | Main window created |
| `on_window_close` | — | Window closing |
| `before_app_setup` | `manifest` | Before user app setup |
| `after_app_setup` | `manifest`, `app_instance` | After user app setup |
| `before_theme_change` | `old_theme`, `new_theme` | Before theme switches |
| `after_theme_change` | `theme_name`, `old_theme` | After theme switched |
| `before_scene_push` | `scene`, `animation` | Before scene push |
| `after_scene_push` | `scene` | After scene push completes |
| `before_scene_pop` | `scene`, `animation` | Before scene pop |
| `after_scene_pop` | `scene` | After scene pop completes |
| `before_scene_replace` | `scene`, `old_scene`, `animation` | Before scene replace |
| `after_scene_replace` | `scene` | After scene replace completes |
| `before_visual_reload` | `manifest` | Before UI rebuild |
| `after_visual_reload` | `manifest` | After UI rebuild |
| `before_full_reload` | `manifest` | Before full app reload |
| `after_full_reload` | `manifest`, `app_instance` | After full app reload |
| `before_language_change` | `lang`, `old_core`, `old_app` | Before language switch |
| `after_language_change` | `core_lang`, `app_lang` | After language switched |
| `after_audio_play` | `file_path` | Audio started playing |
| `on_audio_pause` | — | Audio paused |
| `on_audio_resume` | — | Audio resumed |
| `on_audio_stop` | — | Audio stopped |
| `on_audio_finished` | — | Track finished naturally |
| `on_audio_volume` | `volume` | Volume changed |
| `on_audio_seek` | `position_ms` | Seek position changed |
| `on_settings_open` | — | Settings panel opened |
| `on_settings_close` | — | Settings panel closed |
| `on_file_drop` | `file_paths` (list of str) | User dropped files into the window |
| `on_error` | `error_type`, `error_msg`, `traceback` | Unhandled exception caught |

**Available hooks (filter):**

| Hook | Value | kwargs | Purpose |
|---|---|---|---|
| `core_qss` | QSS string | `theme` | Modify global stylesheet |
| `translate` | translated string | `key` | Override any translation |
| `window_title` | title string | — | Modify window title |
| `splash_text` | app name string | — | Modify splash screen text |
| `before_audio_play` | file path string | `start_ms` | Redirect/modify audio file path |
| `settings_tabs` | tabs list | — | Add/remove/reorder settings tabs |
| `app_manifests` | manifests list | — | Filter apps shown in launcher |

**Filter example — add custom QSS rules:**

```python
def on_register(self, core):
    core.hooks.register("core_qss", self.modify_qss, owner="MyComponent")

def modify_qss(self, qss, **kwargs):
    theme = kwargs["theme"]
    return qss + f"""
        QToolTip {{
            background: {theme.bg_alt};
            color: {theme.fg};
            border: 1px solid {theme.border};
        }}
    """
```

#### Accessing Components from Apps

```python
def setup(self, app):
    # get a component
    demo = app.components.get("DemoComponent")
    if demo:
        demo.greet("Kislinka")  # call public API

    # check if loaded
    if app.components.has("Logger"):
        logger = app.components.get("Logger")
        logger.info("App started")

    # list all components
    for name in app.components.names():
        print(f"Component: {name}")
```

#### Services & Widgets

Components can register services and widget classes for other components and apps:

```python
# in component on_register():
core.components.register_service("http", MyHttpClient())
core.components.register_widget("ColorPicker", ColorPickerWidget)

# in app:
http = app.components.get_service("http")
http.get("https://api.example.com")

ColorPicker = app.components.get_widget("ColorPicker")
picker = ColorPicker(parent=self.container)
```

#### Component Storage

Components have persistent storage scoped to their name:

```python
# in component:
core.components.storage_set("MyComponent", "api_key", "abc123")
key = core.components.storage_get("MyComponent", "api_key", "")
core.components.storage_delete("MyComponent", "api_key")

# stored at: %LOCALAPPDATA%/KislinkaCore/_components/MyComponent/data.json
```

---

### Titlebar

```python
window = app.window

# Change title
window.set_title("New Title")

# Change window size (app only)
window.set_size(800, 500)
window.center_on_screen()

# Add custom button (appears right of ⚙)
btn = window.titlebar.add_custom_button(
    "back",              # icon name (built-in) or SVG file path
    self.on_click,       # callback
    icon_size=16,
)

# Clear all custom buttons
window.titlebar.clear_custom_buttons()
```

**Built-in icon names:** `"close"`, `"minimize"`, `"settings"`, `"back"`

Custom SVG icons: pass a file path instead of a name.

**Note:** Custom titlebar buttons are automatically hidden while Settings is open, and restored when Settings closes.

---

### Settings Tabs

Your app can add custom pages to the Settings panel:

```python
from core.permissions import Permission

def setup(self, app):
    app.permissions.register_settings_tab(
        "my_settings",                    # unique ID
        "my_settings_title",             # locale key
        "settings",                       # icon
        self.build_settings_page,         # callable → Scene
        owner=Permission.APP,
    )

def build_settings_page(self) -> Scene:
    scene = Scene("my_settings")
    lay = scene.scene_layout()
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(0)

    # Use the same header pattern as core settings:
    header = self._make_header("My Settings")
    lay.addWidget(header)

    content = QWidget()
    cl = QVBoxLayout(content)
    cl.setContentsMargins(24, 24, 24, 24)
    cl.setSpacing(16)

    # Add your controls...
    cl.addWidget(KLabel("Some Setting", style="body"))
    toggle = KToggle(checked=True)
    cl.addWidget(toggle)

    cl.addStretch()
    lay.addWidget(content, 1)
    return scene
```

---

### Fonts

```python
from core.fonts import Fonts

# Get QFont objects
heading_font = Fonts.heading(28)     # Mitr
body_font = Fonts.body(14)           # Roboto Bold
custom = Fonts.custom("Arial", 16, bold=True)

# Font family names
Fonts.heading_family()  # "Mitr"
Fonts.body_family()     # "Roboto"
```

---

## Theming

The design is pure black & white. All widgets automatically respond to theme changes.

**Dark theme:** Black background, white elements
**Light theme:** White background, black elements

Theme is saved automatically and restored on next launch.

Users can toggle in Settings → Themes, or you can toggle programmatically:

```python
app.theme_manager.toggle()
```

---

## Error Handling

All unhandled exceptions (including those in Qt signal handlers) are caught automatically. When an error occurs:

1. All windows close
2. A standalone Error Window appears with:
   - Error type and message
   - Full traceback
   - Copy Error button
   - Close button

You don't need to do anything — it works out of the box.

For testing:

```python
KButton("Crash", on_click=lambda: 1/0)
```

---

## Launcher & Splash

**Launcher:** Automatically shown when 2+ apps are found in `App/`. User picks one. Frameless, draggable, same B&W style.

**Splash:** Shown inside the main window while the app loads. Displays the app name in large Mitr font. Animates out with scale-up + fade (400ms).

Both are handled entirely by the core — no app code needed.

**Splash behavior:**
- Single app mode: Splash appears immediately after window creation
- Launcher mode: Splash appears after user selects an app from the launcher
- The splash covers the entire window (including titlebar) and animates out after app setup completes

---

## File Paths & Assets

```python
# From your app's main.py, access your own assets:
from pathlib import Path

APP_DIR = Path(__file__).parent
my_image = APP_DIR / "assets" / "image.png"
my_sound = APP_DIR / "assets" / "click.wav"
```

---

## Dependencies

```txt
PyQt6>=6.6.0
pygame>=2.5.0
mutagen>=1.47.0
```

Optional:
- `ffmpeg.exe` + `ffprobe.exe` in `assets/bin/` for M4A/AAC audio support

---

## Examples

### Minimal App

```python
from core.scene import Scene, AnimationType
from widgets.klabel import KLabel
from PyQt6.QtCore import Qt

class MinimalApp:
    def setup(self, app):
        scene = Scene("home")
        lay = scene.scene_layout()
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(KLabel("Hello!", style="heading"))
        app.scene_manager.push(scene, AnimationType.NONE)

    def cleanup(self):
        pass
```

### Multi-Scene App

```python
from core.scene import Scene, AnimationType
from widgets.klabel import KLabel
from widgets.kbutton import KButton
from PyQt6.QtCore import Qt

class MultiSceneApp:
    def setup(self, app):
        self.sm = app.scene_manager
        self.sm.push(self.build_home(), AnimationType.NONE)

    def cleanup(self):
        pass

    def build_home(self):
        scene = Scene("home")
        lay = scene.scene_layout()
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(16)
        lay.addWidget(KLabel("Home", style="heading"))
        lay.addWidget(KButton("Go to Page 2", on_click=self.go_page2))
        return scene

    def build_page2(self):
        scene = Scene("page2")
        lay = scene.scene_layout()
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(16)
        lay.addWidget(KLabel("Page 2", style="heading"))
        lay.addWidget(KButton("← Back", on_click=self.go_back))
        return scene

    def go_page2(self):
        if not self.sm.is_animating:
            self.sm.push(self.build_page2(), AnimationType.SLIDE_LEFT)

    def go_back(self):
        if not self.sm.is_animating:
            self.sm.pop(AnimationType.SLIDE_RIGHT)
```

### Audio Player App

```python
from core.scene import Scene, AnimationType
from widgets.klabel import KLabel
from widgets.kbutton import KButton
from audio.metadata import MetadataReader
from PyQt6.QtWidgets import QFileDialog, QHBoxLayout
from PyQt6.QtCore import Qt

class PlayerApp:
    def setup(self, app):
        self.sm = app.scene_manager
        self.player = app.audio
        self.loc = app.locale

        self.player.position_changed.connect(self.on_pos)
        self.sm.push(self.build_ui(), AnimationType.NONE)

    def cleanup(self):
        self.player.stop()
        self.player.position_changed.disconnect(self.on_pos)

    def build_ui(self):
        scene = Scene("player")
        lay = scene.scene_layout()
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(12)

        self.title = KLabel("No track", style="heading",
                             align=Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.title)

        self.pos = KLabel("0:00", style="dim",
                           align=Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.pos)

        row = QHBoxLayout()
        row.setSpacing(12)
        row.addWidget(KButton("Open", on_click=self.open_file))
        row.addWidget(KButton("Play/Pause", on_click=self.player.toggle_pause))
        row.addWidget(KButton("Stop", on_click=self.player.stop))
        lay.addLayout(row)

        return scene

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            None, "Open", "", "Audio (*.mp3 *.flac *.ogg *.wav *.m4a)")
        if path:
            info = MetadataReader.read(path)
            self.title.setText(info.title)
            self.player.play(path)

    def on_pos(self, ms):
        s = ms // 1000
        self.pos.setText(f"{s // 60}:{s % 60:02d}")
```

---

## License
MIT

---
## by Koleso
