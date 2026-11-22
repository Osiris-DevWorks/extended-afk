"""Osiris DevWorks theme, ported from Smart Citizen's "odw" theme.

Smart Citizen (PyQt6) defines its look in ``src/gui/theme.py``: a navy
charcoal + antique gold palette, a branded display font for the title, and
flat action buttons in muted accent colors with dark text. This module
carries the same values over to ttkbootstrap so the two apps read as one
family. Keep the hex values in step with Smart Citizen's ``_odw_palette``,
``_BUTTON_COLORS[THEME_ODW]``, ``_TITLE_COLORS`` and ``_TAGLINE_COLORS``.
"""
import logging
import os
import sys
import tkinter as tk
import tkinter.font as tkfont

from utils.resource_path import get_resource_path

logger = logging.getLogger(__name__)

THEME_NAME = "odw"

# Palette (Smart Citizen _odw_palette)
WINDOW_BG = "#1A1F2E"       # navy
PANEL_BG = "#242938"        # raised panel / inputs
BORDER = "#3A4052"
TEXT = "#F0E6CF"            # cream
TEXT_SECONDARY = "#D4B876"
TEXT_DISABLED = "#64594A"
HIGHLIGHT = "#D4A017"       # selection gold
HIGHLIGHT_TEXT = "#1A1F2E"
LINK = "#D4B876"

# Branded header (Smart Citizen _TITLE_COLORS / _TAGLINE_COLORS)
TITLE_COLOR = "#C9A961"
TAGLINE_COLOR = "#A08C5A"

# Action buttons (Smart Citizen _BUTTON_COLORS[THEME_ODW]); text is black
BUTTON_TEXT = "#000000"
BUTTON_GOLD = "#D4B876"     # navigate / neutral actions
BUTTON_COPPER = "#C77A4D"   # rollback / stop
BUTTON_SAGE = "#A5B989"     # commit / start
BUTTON_SLATE = "#7A7D87"    # cleanup / delete
BUTTON_RED = "#C0392B"

# Brand display font (same file Smart Citizen bundles under assets/fonts)
_BRAND_FONT_FILE = "HyperspaceRace-ExpandedBold.otf"
# GDI exposes the legacy family name; fontconfig and Qt use the typographic one.
_BRAND_FONT_FAMILIES = (
    "FSP DEMO - Hyprspc Rc xpndd",
    "FONTSPRING DEMO - Hyperspace Race Expanded",
)
_FALLBACK_TITLE_FONT = "Segoe UI"

UI_FONT = "Segoe UI"
MONO_FONT = "Consolas"


def dim(color, amount=0.45):
    """Blend *color* toward the window background, for disabled buttons."""
    def rgb(c):
        return [int(c[i:i + 2], 16) for i in (1, 3, 5)]
    fg, bg = rgb(color), rgb(WINDOW_BG)
    mixed = [round(f * amount + b * (1 - amount)) for f, b in zip(fg, bg)]
    return "#" + "".join(f"{v:02X}" for v in mixed)


def _register_brand_font():
    """Make the bundled brand font available to Tk for this process only."""
    path = get_resource_path(os.path.join("assets", "fonts", _BRAND_FONT_FILE))
    if not os.path.exists(path):
        logger.warning(f"Brand font not found at {path}; using {_FALLBACK_TITLE_FONT}")
        return
    if sys.platform == "win32":
        try:
            import ctypes
            FR_PRIVATE = 0x10
            added = ctypes.windll.gdi32.AddFontResourceExW(path, FR_PRIVATE, 0)
            if not added:
                logger.warning(f"Windows refused to load brand font {path}")
        except Exception as e:
            logger.warning(f"Failed to register brand font: {e}")


def title_font():
    """Font tuple for the branded window title."""
    families = set(tkfont.families())
    for family in _BRAND_FONT_FAMILIES:
        if family in families:
            return (family, 20, "bold")
    return (_FALLBACK_TITLE_FONT, 20, "bold")


def apply_theme(style):
    """
    Register and activate the Osiris DevWorks theme on a ttkbootstrap Style.

    Args:
        style: the ttkbootstrap Style of the root window
    """
    from ttkbootstrap.style import ThemeDefinition

    _register_brand_font()

    colors = {
        "primary": BUTTON_GOLD,
        "secondary": BUTTON_SLATE,
        "success": BUTTON_SAGE,
        "info": BUTTON_GOLD,
        "warning": BUTTON_COPPER,
        "danger": BUTTON_RED,
        "light": TEXT,
        "dark": PANEL_BG,
        "bg": WINDOW_BG,
        "fg": TEXT,
        "selectbg": HIGHLIGHT,
        "selectfg": HIGHLIGHT_TEXT,
        "border": BORDER,
        "inputfg": TEXT,
        "inputbg": PANEL_BG,
        "active": "#2E3447",
    }
    # ttkbootstrap 1.x calls the light/dark flag `themetype`, 2.x calls it `mode`
    try:
        definition = ThemeDefinition(THEME_NAME, colors, mode="dark")
    except TypeError:
        definition = ThemeDefinition(THEME_NAME, colors, themetype="dark")

    if THEME_NAME not in style.theme_names():
        style.register_theme(definition)
    style.theme_use(THEME_NAME)

    # Group box titles in gold, like Smart Citizen's section headers
    style.configure("TLabelframe.Label", foreground=TITLE_COLOR, font=(UI_FONT, 10, "bold"))
    style.configure("Secondary.TLabel", foreground=TAGLINE_COLOR)


def action_button(parent, text, color, command, bold=False):
    """Flat accent-colored button with dark text (Smart Citizen toolbar style)"""
    return tk.Button(
        parent,
        text=text,
        command=command,
        bg=color,
        fg=BUTTON_TEXT,
        activebackground=color,
        activeforeground=BUTTON_TEXT,
        disabledforeground=dim(BUTTON_TEXT, 0.55),
        font=(UI_FONT, 9, "bold" if bold else "normal"),
        relief=tk.FLAT,
        borderwidth=0,
        highlightthickness=0,
        cursor="hand2",
        padx=10,
        pady=3
    )


def set_button_enabled(button, color, enabled):
    """Enable/disable an action button, dimming its color while disabled"""
    button.config(
        state='normal' if enabled else 'disabled',
        bg=color if enabled else dim(color),
        cursor="hand2" if enabled else "arrow"
    )


def style_text(widget, font=(UI_FONT, 9)):
    """Dark panel colors for a tk.Text, which ttk themes don't reach"""
    widget.config(
        font=font,
        bg=PANEL_BG,
        fg=TEXT,
        insertbackground=TEXT,
        selectbackground=HIGHLIGHT,
        selectforeground=HIGHLIGHT_TEXT,
        relief=tk.FLAT,
        borderwidth=0,
        highlightthickness=1,
        highlightbackground=BORDER,
        highlightcolor=BORDER,
        padx=6,
        pady=4
    )
