"""KislinkaCore custom widgets."""

from widgets.kbutton import KButton
from widgets.ktextfield import KTextField
from widgets.klabel import KLabel
from widgets.kicon import load_svg_icon
from widgets.ktoggle import KToggle
from widgets.ksettingsitem import KSettingsItem
from widgets.kdropdown import KDropdown
from widgets.kcheckbox import KCheckbox
from widgets.kprogressbar import KProgressBar
from widgets.klist import KList
from widgets.ktable import KTable

__all__ = [
    "KButton",
    "KTextField",
    "KLabel",
    "KToggle",
    "KSettingsItem",
    "KDropdown",
    "KCheckbox",
    "KProgressBar",
    "KList",
    "KTable",
    "load_svg_icon",
]