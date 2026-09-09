"""Main GUI window for Extended AFK application"""
import tkinter as tk
from tkinter import ttk, messagebox
import ttkbootstrap as ttk_bootstrap
from ttkbootstrap.constants import *
import webbrowser
import logging
from PIL import Image, ImageTk
import os

from core.settings import AppSettings
from core.key_presser import KeyPresser
from utils.resource_path import get_resource_path
from gui.key_selector import select_key
from gui.text_handler import TextHandler, SimpleFormatter

logger = logging.getLogger(__name__)

# Colors matching sc-profile-editor
BG_COLOR = "#f0f0f0"
FRAME_BG = "#ffffff"
ACCENT_COLOR = "#c9a961"
TEXT_COLOR = "#333333"
BUTTON_START_COLOR = "#4CAF50"
BUTTON_STOP_COLOR = "#f44336"


class MainWindow:
    """Main application window"""

    def __init__(self, root):
        """
        Initialize the main window.

        Args:
            root: tkinter.Tk root window
        """
        self.root = root
        self.root.title("Extended AFK - Auto Key Presser")
        self.root.geometry("550x720")
        self.root.resizable(False, False)

        # Set window icon (for taskbar and title bar)
        try:
            icon_path = get_resource_path(os.path.join("assets", "extended-afk.ico"))
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception as e:
            logger.warning(f"Failed to set window icon: {e}")

        # Settings manager
        self.settings = AppSettings()

        # Key presser (will be initialized when started)
        self.key_presser = None

        # Key list widgets (for dynamic key management)
        self.key_frames = []

        # Build UI
        self._build_ui()

        # Set up logging handler for GUI
        self._setup_logging()

        # Load initial settings
        self._load_settings()

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        """Build the user interface"""
        # Main container - use ttk.Frame for proper theming
        main_container = ttk.Frame(self.root, padding=15)
        main_container.pack(fill=tk.BOTH, expand=True)

        # Configuration section
        self._build_configuration_section(main_container)

        # Start/Stop button
        self._build_control_button(main_container)

        # Activity log section
        self._build_log_section(main_container)

        # Footer with branding
        self._build_footer(main_container)

    def _build_configuration_section(self, parent):
        """Build the configuration section"""
        # Configuration frame
        config_frame = ttk.LabelFrame(
            parent,
            text=" Configuration ",
            padding=10
        )
        config_frame.pack(fill=tk.BOTH, padx=5, pady=5)

        # Keys section
        keys_label = ttk.Label(
            config_frame,
            text="Keys to Press:",
            font=("Segoe UI", 10, "bold")
        )
        keys_label.pack(anchor=tk.W, pady=(0, 5))

        # Keys container
        self.keys_container = ttk.Frame(config_frame)
        self.keys_container.pack(fill=tk.X, pady=(0, 10))

        # Add key button
        add_key_frame = ttk.Frame(config_frame)
        add_key_frame.pack(fill=tk.X, pady=(0, 15))

        self.add_key_button = ttk.Button(
            add_key_frame,
            text="Add Key...",
            command=self._add_key
        )
        self.add_key_button.pack(side=tk.RIGHT)

        # Interval section
        interval_label = ttk.Label(
            config_frame,
            text="Interval (minutes):",
            font=("Segoe UI", 10, "bold")
        )
        interval_label.pack(anchor=tk.W, pady=(0, 5))

        interval_frame = ttk.Frame(config_frame)
        interval_frame.pack(fill=tk.X, pady=(0, 15))

        # Min interval
        ttk.Label(interval_frame, text="Min:").pack(side=tk.LEFT, padx=(0, 5))
        self.min_interval_var = tk.IntVar(value=10)
        min_spinbox = ttk.Spinbox(
            interval_frame,
            from_=1,
            to=60,
            textvariable=self.min_interval_var,
            width=5,
            command=self._on_settings_changed
        )
        min_spinbox.pack(side=tk.LEFT, padx=(0, 20))

        # Max interval
        ttk.Label(interval_frame, text="Max:").pack(side=tk.LEFT, padx=(0, 5))
        self.max_interval_var = tk.IntVar(value=14)
        max_spinbox = ttk.Spinbox(
            interval_frame,
            from_=1,
            to=60,
            textvariable=self.max_interval_var,
            width=5,
            command=self._on_settings_changed
        )
        max_spinbox.pack(side=tk.LEFT)

    def _build_control_button(self, parent):
        """Build the start/stop control buttons"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, padx=5, pady=10)

        # Start button
        self.start_button = tk.Button(
            button_frame,
            text="Start",
            command=self._start_pressing,
            bg=BUTTON_START_COLOR,
            fg="white",
            font=("Segoe UI", 11, "bold"),
            relief=tk.FLAT,
            cursor="hand2",
            padx=20,
            pady=12
        )
        self.start_button.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        # Stop button
        self.stop_button = tk.Button(
            button_frame,
            text="Stop",
            command=self._stop_pressing,
            bg=BUTTON_STOP_COLOR,
            fg="white",
            font=("Segoe UI", 11, "bold"),
            relief=tk.FLAT,
            cursor="hand2",
            padx=20,
            pady=12,
            state='disabled'
        )
        self.stop_button.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

    def _build_log_section(self, parent):
        """Build the activity log section"""
        # Log frame
        log_frame = ttk.LabelFrame(
            parent,
            text=" Activity Log ",
            padding=5
        )
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Text widget with scrollbar
        text_container = ttk.Frame(log_frame)
        text_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        scrollbar = ttk.Scrollbar(text_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_text = tk.Text(
            text_container,
            height=10,
            width=60,
            yscrollcommand=scrollbar.set,
            font=("Consolas", 9),
            state='disabled',
            wrap=tk.WORD
        )
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.log_text.yview)

    def _build_footer(self, parent):
        """Build the footer with branding and donation links"""
        # Footer frame
        footer_frame = ttk.Frame(parent)
        footer_frame.pack(fill=tk.X, padx=5, pady=(10, 0))

        # Osiris DevWorks button (left)
        self._create_osiris_button(footer_frame)

        # Spacer
        ttk.Frame(footer_frame, width=10).pack(side=tk.LEFT)

        # Support label
        support_label = ttk.Label(
            footer_frame,
            text="Support:",
            font=("Segoe UI", 9)
        )
        support_label.pack(side=tk.LEFT, padx=(10, 5))

        # PayPal button
        self._create_paypal_button(footer_frame)

        # Spacer
        ttk.Frame(footer_frame, width=5).pack(side=tk.LEFT)

        # Venmo button
        self._create_venmo_button(footer_frame)

    def _create_osiris_button(self, parent):
        """Create Osiris DevWorks button"""
        try:
            # Try to load image
            image_path = get_resource_path(os.path.join("assets", "osiris-devworks.png"))
            if os.path.exists(image_path):
                img = Image.open(image_path)
                # Scale to height 40
                ratio = 40 / img.height
                new_width = int(img.width * ratio)
                img = img.resize((new_width, 40), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)

                label = tk.Label(parent, image=photo, cursor="hand2")
                label.image = photo  # Keep reference
                label.pack(side=tk.LEFT)
                label.bind("<Button-1>", lambda e: self._open_discord())
            else:
                # Fallback to text
                self._create_text_button(
                    parent,
                    "Osiris DevWorks",
                    "#1a1f2e",
                    ACCENT_COLOR,
                    self._open_discord
                )
        except Exception as e:
            logger.error(f"Failed to load Osiris image: {e}")
            self._create_text_button(
                parent,
                "Osiris DevWorks",
                "#1a1f2e",
                ACCENT_COLOR,
                self._open_discord
            )

    def _create_paypal_button(self, parent):
        """Create PayPal donation button"""
        try:
            # Try to load image
            image_path = get_resource_path(os.path.join("assets", "paypal.png"))
            if os.path.exists(image_path):
                img = Image.open(image_path)
                # Scale to height 40
                ratio = 40 / img.height
                new_width = int(img.width * ratio)
                img = img.resize((new_width, 40), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)

                label = tk.Label(parent, image=photo, cursor="hand2")
                label.image = photo  # Keep reference
                label.pack(side=tk.LEFT)
                label.bind("<Button-1>", lambda e: self._open_paypal())
            else:
                # Fallback to text
                self._create_text_button(
                    parent,
                    "PayPal",
                    "#0070ba",
                    "white",
                    self._open_paypal
                )
        except Exception as e:
            logger.error(f"Failed to load PayPal image: {e}")
            self._create_text_button(
                parent,
                "PayPal",
                "#0070ba",
                "white",
                self._open_paypal
            )

    def _create_venmo_button(self, parent):
        """Create Venmo donation button"""
        try:
            # Try to load image
            image_path = get_resource_path(os.path.join("assets", "venmo.png"))
            if os.path.exists(image_path):
                img = Image.open(image_path)
                # Scale to height 40
                ratio = 40 / img.height
                new_width = int(img.width * ratio)
                img = img.resize((new_width, 40), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)

                label = tk.Label(parent, image=photo, cursor="hand2")
                label.image = photo  # Keep reference
                label.pack(side=tk.LEFT)
                label.bind("<Button-1>", lambda e: self._open_venmo())
            else:
                # Fallback to text
                self._create_text_button(
                    parent,
                    "Venmo",
                    "#008CFF",
                    "white",
                    self._open_venmo
                )
        except Exception as e:
            logger.error(f"Failed to load Venmo image: {e}")
            self._create_text_button(
                parent,
                "Venmo",
                "#008CFF",
                "white",
                self._open_venmo
            )

    def _create_text_button(self, parent, text, bg, fg, command):
        """Create a styled text button"""
        label = tk.Label(
            parent,
            text=text,
            bg=bg,
            fg=fg,
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=8,
            cursor="hand2",
            relief=tk.RAISED,
            borderwidth=1
        )
        label.pack(side=tk.LEFT)
        label.bind("<Button-1>", lambda e: command())

    def _setup_logging(self):
        """Set up logging to the GUI text widget"""
        # Create handler
        handler = TextHandler(self.log_text)
        handler.setLevel(logging.INFO)
        handler.setFormatter(SimpleFormatter())

        # Add to root logger
        logging.getLogger().addHandler(handler)

    def _load_settings(self):
        """Load settings and update UI"""
        # Load keys configuration (maximum of 3)
        keys_config = self.settings.get('keys_config', [])

        # Handle backward compatibility with old 'keys' format
        if not keys_config:
            old_keys = self.settings.get('keys', [])
            old_press_twice = self.settings.get('press_twice', False)
            keys_config = [{'key': k, 'press_twice': old_press_twice} for k in old_keys]

        # Limit to first 3 keys
        keys_config = keys_config[:3]

        for config in keys_config:
            key_name = config.get('key', config) if isinstance(config, dict) else config
            press_twice = config.get('press_twice', False) if isinstance(config, dict) else False
            self._add_key_widget(key_name, press_twice)

        # Disable add button if we have 3 keys
        if len(self.key_frames) >= 3:
            self.add_key_button.config(state='disabled')

        # Load intervals
        self.min_interval_var.set(self.settings.get('min_interval_minutes', 10))
        self.max_interval_var.set(self.settings.get('max_interval_minutes', 14))

    def _add_key(self):
        """Add a new key via detection dialog"""
        # Check if we already have 3 keys (maximum)
        if len(self.key_frames) >= 3:
            messagebox.showwarning(
                "Maximum Keys Reached",
                "You can only configure a maximum of 3 keys.\n\nDelete an existing key before adding a new one."
            )
            return

        # Disable control during detection
        self.add_key_button.config(state='disabled')
        self.root.update()

        # Show key selection dialog
        key = select_key(self.root)

        # Re-enable control
        self.add_key_button.config(state='normal')

        if key:
            self._add_key_widget(key)
            self._on_settings_changed()

            # Update add button state if we reached max
            if len(self.key_frames) >= 3:
                self.add_key_button.config(state='disabled')

    def _add_key_widget(self, key_name, press_twice=False):
        """
        Add a key widget to the keys container.

        Args:
            key_name: Name of the key
            press_twice: Whether to press this key twice
        """
        # Create frame for this key
        key_frame = ttk.Frame(self.keys_container)
        key_frame.pack(fill=tk.X, pady=2)

        # Key label
        key_label = ttk.Label(
            key_frame,
            text=key_name.upper(),
            font=("Segoe UI", 10),
            width=10,
            relief=tk.SUNKEN,
            borderwidth=1
        )
        key_label.pack(side=tk.LEFT, padx=(0, 10))

        # Delete button
        delete_button = ttk.Button(
            key_frame,
            text="Delete",
            command=lambda: self._remove_key_widget(key_frame)
        )
        delete_button.pack(side=tk.LEFT, padx=(0, 10))

        # Change Key button
        select_button = ttk.Button(
            key_frame,
            text="Change Key...",
            command=lambda: self._replace_key(key_frame)
        )
        select_button.pack(side=tk.LEFT, padx=(0, 10))

        # Use toggle behavior checkbox
        press_twice_var = tk.BooleanVar(value=press_twice)
        press_twice_check = ttk.Checkbutton(
            key_frame,
            text="Use Toggle Behavior",
            variable=press_twice_var,
            command=self._on_settings_changed
        )
        press_twice_check.pack(side=tk.LEFT)

        # Store reference (key_frame, key_name, press_twice_var)
        self.key_frames.append((key_frame, key_name, press_twice_var))

    def _remove_key_widget(self, key_frame):
        """
        Remove a key widget.

        Args:
            key_frame: Frame to remove
        """
        # Remove from list
        self.key_frames = [(f, k, v) for f, k, v in self.key_frames if f != key_frame]

        # Destroy widget
        key_frame.destroy()

        # Re-enable add button if we were at max
        if len(self.key_frames) < 3:
            self.add_key_button.config(state='normal')

        # Save settings
        self._on_settings_changed()

    def _replace_key(self, key_frame):
        """
        Replace a key.

        Args:
            key_frame: Frame containing the key
        """
        # Show key selection dialog
        new_key = select_key(self.root)

        if new_key:
            # Update the key name in the frame
            for widget in key_frame.winfo_children():
                if isinstance(widget, ttk.Label):
                    widget.config(text=new_key.upper())
                    break

            # Update in key_frames list
            for i, (f, k, v) in enumerate(self.key_frames):
                if f == key_frame:
                    self.key_frames[i] = (f, new_key, v)
                    break

            # Save settings
            self._on_settings_changed()

    def _on_settings_changed(self):
        """Handle settings change"""
        # Get current keys with press_twice settings
        keys_config = [
            {'key': k, 'press_twice': v.get()}
            for f, k, v in self.key_frames
        ]

        # Update settings
        self.settings.set('keys_config', keys_config)
        self.settings.set('min_interval_minutes', self.min_interval_var.get())
        self.settings.set('max_interval_minutes', self.max_interval_var.get())

    def _start_pressing(self):
        """Start key pressing"""
        # Validate settings
        if not self.key_frames:
            messagebox.showwarning("No Keys", "Please add at least one key to press.")
            return

        min_int = self.min_interval_var.get()
        max_int = self.max_interval_var.get()

        if min_int > max_int:
            messagebox.showwarning(
                "Invalid Interval",
                "Minimum interval cannot be greater than maximum interval."
            )
            return

        # Get keys configuration
        keys_config = [
            {'key': k, 'press_twice': v.get()}
            for f, k, v in self.key_frames
        ]

        # Update buttons FIRST
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.root.update()  # Force GUI to update immediately

        # Create and start key presser in a separate thread to avoid blocking
        try:
            def start_thread():
                try:
                    self.key_presser = KeyPresser(
                        keys_config=keys_config,
                        min_interval_minutes=min_int,
                        max_interval_minutes=max_int,
                        status_callback=self._on_key_presser_status
                    )
                    self.key_presser.start()
                    logger.info("Key presser started successfully")
                except Exception as e:
                    logger.error(f"Failed to start key pressing: {e}", exc_info=True)
                    self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to start key pressing:\n{e}"))
                    # Reset buttons on error
                    self.root.after(0, lambda: self.start_button.config(state='normal'))
                    self.root.after(0, lambda: self.stop_button.config(state='disabled'))
                    self.root.after(0, self._set_config_enabled, True)

            import threading
            setup_thread = threading.Thread(target=start_thread, daemon=True)
            setup_thread.start()

            # Disable configuration
            self._set_config_enabled(False)

        except Exception as e:
            logger.error(f"Failed to start key pressing: {e}", exc_info=True)
            messagebox.showerror("Error", f"Failed to start key pressing:\n{e}")
            # Reset button states
            self.start_button.config(state='normal')
            self.stop_button.config(state='disabled')
            self._set_config_enabled(True)

    def _stop_pressing(self):
        """Stop key pressing"""
        if self.key_presser:
            self.key_presser.stop()

        # Update buttons
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')

        # Enable configuration
        self._set_config_enabled(True)

    def _set_config_enabled(self, enabled):
        """
        Enable or disable configuration controls.

        Args:
            enabled: True to enable, False to disable
        """
        state = 'normal' if enabled else 'disabled'

        # Disable add key button and key widgets
        self.add_key_button.config(state=state)

        for key_frame, key_name, press_twice_var in self.key_frames:
            for widget in key_frame.winfo_children():
                if isinstance(widget, tk.Button) or isinstance(widget, ttk.Button):
                    widget.config(state=state)

    def _on_key_presser_status(self, message):
        """
        Handle status message from key presser.

        Args:
            message: Status message
        """
        # Message is already logged by the key presser, just display in UI
        pass

    def _open_discord(self):
        """Open Osiris DevWorks Discord"""
        webbrowser.open("https://discord.gg/BNzRegKZ7k")

    def _open_paypal(self):
        """Open PayPal donation page"""
        webbrowser.open("https://www.paypal.com/ncp/payment/YAWXHMGZH8T76")

    def _open_venmo(self):
        """Open Venmo donation page"""
        webbrowser.open("https://venmo.com/u/Amr-Abouelleil")

    def _on_close(self):
        """Handle window close event"""
        # Stop key presser if running
        if self.key_presser and self.key_presser.is_running():
            self.key_presser.stop()

        # Close window
        self.root.destroy()
