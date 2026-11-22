"""Key detection dialog using pynput"""
import tkinter as tk
from tkinter import ttk
import threading
from pynput import keyboard as pynput_keyboard
import logging

from gui import theme

logger = logging.getLogger(__name__)


class KeySelectorDialog(tk.Toplevel):
    """Modal dialog for detecting keyboard key presses"""

    def __init__(self, parent):
        """
        Initialize the key selector dialog.

        Args:
            parent: Parent tkinter window
        """
        super().__init__(parent)
        self.title("Select Key")
        self.geometry("350x240")
        self.resizable(False, False)

        # Make modal
        self.transient(parent)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

        # Result
        self.selected_key = None
        self.listener = None
        self.timeout_timer = None

        # Build UI
        self._build_ui()

        # Start listening
        self.after(100, self._start_listening)

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _build_ui(self):
        """Build the dialog UI"""
        # Main frame
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Instruction label
        instruction = ttk.Label(
            main_frame,
            text="Press any key to select...",
            font=("Segoe UI", 11, "bold")
        )
        instruction.pack(pady=(0, 20))

        # Status frame
        status_frame = ttk.LabelFrame(main_frame, text="Status", padding=10)
        status_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

        self.status_label = ttk.Label(
            status_frame,
            text="Listening for key press...\n\n(Press ESC to cancel)",
            justify=tk.CENTER
        )
        self.status_label.pack(expand=True)

        # Cancel button
        self.cancel_button = theme.action_button(
            main_frame, "Cancel", theme.BUTTON_SLATE, self._on_cancel
        )
        self.cancel_button.pack()

    def _start_listening(self):
        """Start the pynput keyboard listener"""
        try:
            self.listener = pynput_keyboard.Listener(on_press=self._on_key_press)
            self.listener.start()

            # Set timeout (10 seconds)
            self.timeout_timer = self.after(10000, self._on_timeout)

            logger.debug("Key detection listener started")
        except Exception as e:
            logger.error(f"Failed to start key listener: {e}")
            self.status_label.config(text=f"Error: {e}")

    def _on_key_press(self, key):
        """
        Handle key press event from pynput.

        Args:
            key: pynput key object
        """
        try:
            # Convert pynput key to string
            if hasattr(key, 'char') and key.char:
                # Regular character key
                key_name = key.char.lower()
            elif hasattr(key, 'name'):
                # Special key (f1, esc, ctrl, etc.)
                key_name = key.name.lower()
            else:
                # Unknown key
                key_name = str(key).lower()

            # Check for ESC (cancel)
            if key_name == 'esc':
                self.after(0, self._on_cancel)
                return False

            # Set selected key
            self.selected_key = key_name
            logger.info(f"Key detected: {key_name}")

            # Close dialog
            self.after(0, self._on_accept)

            # Stop listener
            return False

        except Exception as e:
            logger.error(f"Error processing key press: {e}")
            return False

    def _on_accept(self):
        """Accept the selected key and close dialog"""
        self._cleanup()
        self.destroy()

    def _on_cancel(self):
        """Cancel key selection and close dialog"""
        self.selected_key = None
        self._cleanup()
        self.destroy()

    def _on_timeout(self):
        """Handle timeout"""
        logger.info("Key detection timed out")
        self.status_label.config(text="Timeout! No key detected.")
        self.after(1000, self._on_cancel)

    def _cleanup(self):
        """Clean up resources"""
        # Cancel timeout timer
        if self.timeout_timer:
            try:
                self.after_cancel(self.timeout_timer)
            except:
                pass
            self.timeout_timer = None

        # Stop listener
        if self.listener:
            try:
                self.listener.stop()
            except:
                pass
            self.listener = None

    def get_selected_key(self):
        """
        Get the selected key.

        Returns:
            str or None: Selected key name, or None if cancelled
        """
        return self.selected_key


def select_key(parent):
    """
    Show key selection dialog and return selected key.

    Args:
        parent: Parent tkinter window

    Returns:
        str or None: Selected key name, or None if cancelled
    """
    dialog = KeySelectorDialog(parent)
    parent.wait_window(dialog)
    return dialog.get_selected_key()
