"""Small Windows helpers used for diagnostics (no-ops elsewhere)"""
import sys
import logging

logger = logging.getLogger(__name__)


def is_admin():
    """
    Check whether this process runs with administrator rights.

    Windows blocks simulated key presses from a normal process to a window
    owned by an elevated one, so this tells us whether that can happen.

    Returns:
        bool: True if elevated, False if not (or not on Windows)
    """
    if sys.platform != 'win32':
        return False
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception as e:
        logger.debug(f"Could not check admin rights: {e}")
        return False


def foreground_window_title():
    """
    Get the title of the window that currently has keyboard focus.

    Simulated key presses go to this window, so logging it shows the user
    where each press actually landed.

    Returns:
        str: Window title, or '' if unknown
    """
    if sys.platform != 'win32':
        return ''
    try:
        import ctypes
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return ''
        length = user32.GetWindowTextLengthW(hwnd)
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        return buffer.value
    except Exception as e:
        logger.debug(f"Could not read foreground window: {e}")
        return ''
