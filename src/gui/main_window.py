"""Main GUI window for Extended AFK application

The look follows Smart Citizen's Osiris DevWorks theme (see gui/theme.py):
branded title and tagline at the top, flat accent-colored buttons with dark
text, the Osiris / Discord / donation image row along the bottom, and a
status bar with the version on the right.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import ttkbootstrap as ttk_bootstrap
import webbrowser
import logging
import queue
import threading
from PIL import Image, ImageTk
import os

from core.settings import AppSettings
from core.key_presser import KeyPresser
from core import updater
from utils.resource_path import get_resource_path
from gui import theme
from gui.key_selector import select_key
from gui.text_handler import TextHandler, SimpleFormatter
from gui.update_dialog import UpdateDialog

logger = logging.getLogger(__name__)

MAX_KEYS = 3
FOOTER_IMAGE_HEIGHT = 32

DISCORD_URL = "https://discord.gg/BNzRegKZ7k"
GITHUB_URL = "https://github.com/Osiris-DevWorks"
PAYPAL_URL = "https://www.paypal.com/ncp/payment/YAWXHMGZH8T76"
VENMO_URL = "https://venmo.com/u/Amr-Abouelleil"


def _spaced(text):
    """Uppercase *text* with hair spaces between letters, like Smart Citizen's tagline."""
    return " ".join(text.upper())


class MainWindow:
    """Main application window"""

    def __init__(self, root):
        """
        Initialize the main window.

        Args:
            root: tkinter.Tk root window
        """
        self.root = root
        self.version = updater.get_current_version()
        self.root.title(f"Extended AFK v{self.version}")
        self.root.geometry("560x790")
        self.root.resizable(False, False)

        theme.apply_theme(ttk_bootstrap.Style())
        self.root.configure(bg=theme.WINDOW_BG)

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

        # One dict per configured key: frame, key, press_twice_var, label, buttons
        self.key_rows = []

        # Latest status line from the key presser thread, picked up by _poll_status
        self._pending_status = None

        # Build UI
        self._build_ui()

        # Set up logging handler for GUI
        self._setup_logging()

        # Load initial settings
        self._load_settings()

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._poll_status()

        # Check GitHub for a newer release once the window is up
        self._update_queue = queue.Queue()
        self._update_check_running = False
        self._available_update = None
        self.root.after(1500, self._check_for_updates, False)

    # ------------------------------------------------------------------ build

    def _build_ui(self):
        """Build the user interface"""
        # Status bar first so it claims the bottom edge
        self._build_status_bar(self.root)

        main_container = ttk.Frame(self.root, padding=(15, 10, 15, 8))
        main_container.pack(fill=tk.BOTH, expand=True)

        self._build_header(main_container)
        self._build_configuration_section(main_container)
        self._build_control_button(main_container)
        self._build_footer(main_container)
        self._build_log_section(main_container)

    def _build_header(self, parent):
        """Branded title and tagline, as at the top of Smart Citizen"""
        header = ttk.Frame(parent)
        header.pack(fill=tk.X, padx=5, pady=(0, 8))

        tk.Label(
            header,
            text="EXTENDED AFK",
            font=theme.title_font(),
            fg=theme.TITLE_COLOR,
            bg=theme.WINDOW_BG,
            anchor=tk.W
        ).pack(fill=tk.X)
        tk.Label(
            header,
            text=_spaced("Stay in game while you step away"),
            font=(theme.UI_FONT, 8),
            fg=theme.TAGLINE_COLOR,
            bg=theme.WINDOW_BG,
            anchor=tk.W
        ).pack(fill=tk.X)

    def _action_button(self, parent, text, color, command, bold=False):
        return theme.action_button(parent, text, color, command, bold=bold)

    def _set_button_enabled(self, button, color, enabled):
        theme.set_button_enabled(button, color, enabled)

    def _build_configuration_section(self, parent):
        """Build the configuration section"""
        config_frame = ttk.LabelFrame(
            parent,
            text=" Configuration ",
            padding=10
        )
        config_frame.pack(fill=tk.BOTH, padx=5, pady=5)

        ttk.Label(
            config_frame,
            text="Keys to Press:",
            font=(theme.UI_FONT, 10, "bold")
        ).pack(anchor=tk.W, pady=(0, 5))

        self.keys_container = ttk.Frame(config_frame)
        self.keys_container.pack(fill=tk.X, pady=(0, 6))

        add_key_frame = ttk.Frame(config_frame)
        add_key_frame.pack(fill=tk.X, pady=(0, 12))

        self.add_key_button = self._action_button(
            add_key_frame, "Add Key...", theme.BUTTON_GOLD, self._add_key
        )
        self.add_key_button.pack(side=tk.RIGHT)

        ttk.Label(
            config_frame,
            text="Interval (minutes):",
            font=(theme.UI_FONT, 10, "bold")
        ).pack(anchor=tk.W, pady=(0, 5))

        interval_frame = ttk.Frame(config_frame)
        interval_frame.pack(fill=tk.X)

        ttk.Label(interval_frame, text="Min:").pack(side=tk.LEFT, padx=(0, 5))
        self.min_interval_var = tk.IntVar(value=10)
        self.min_spinbox = ttk_bootstrap.Spinbox(
            interval_frame,
            from_=1,
            to=60,
            textvariable=self.min_interval_var,
            width=5,
            command=self._on_settings_changed
        )
        self.min_spinbox.pack(side=tk.LEFT, padx=(0, 20))

        ttk.Label(interval_frame, text="Max:").pack(side=tk.LEFT, padx=(0, 5))
        self.max_interval_var = tk.IntVar(value=14)
        self.max_spinbox = ttk_bootstrap.Spinbox(
            interval_frame,
            from_=1,
            to=60,
            textvariable=self.max_interval_var,
            width=5,
            command=self._on_settings_changed
        )
        self.max_spinbox.pack(side=tk.LEFT)

    def _build_control_button(self, parent):
        """Build the start/stop control buttons"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, padx=5, pady=10)

        self.start_button = self._action_button(
            button_frame, "Start", theme.BUTTON_SAGE, self._start_pressing, bold=True
        )
        self.start_button.config(font=(theme.UI_FONT, 11, "bold"), pady=10)
        self.start_button.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        self.stop_button = self._action_button(
            button_frame, "Stop", theme.BUTTON_COPPER, self._stop_pressing, bold=True
        )
        self.stop_button.config(font=(theme.UI_FONT, 11, "bold"), pady=10)
        self.stop_button.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        self._set_button_enabled(self.stop_button, theme.BUTTON_COPPER, False)

    def _build_log_section(self, parent):
        """Build the activity log section"""
        log_frame = ttk.LabelFrame(
            parent,
            text=" Activity Log ",
            padding=5
        )
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        text_container = ttk.Frame(log_frame)
        text_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        scrollbar = ttk_bootstrap.Scrollbar(text_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_text = tk.Text(
            text_container,
            height=8,
            width=60,
            yscrollcommand=scrollbar.set,
            state='disabled',
            wrap=tk.WORD
        )
        theme.style_text(self.log_text, font=(theme.MONO_FONT, 9))
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.log_text.yview)

    def _build_footer(self, parent):
        """Osiris DevWorks and Discord on the left, donations on the right"""
        footer_frame = ttk.Frame(parent)
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=(10, 0))

        self._image_link(footer_frame, "osiris-devworks.png", "Osiris DevWorks",
                         GITHUB_URL).pack(side=tk.LEFT)
        self._image_link(footer_frame, "discord.png", "Join the Discord",
                         DISCORD_URL).pack(side=tk.LEFT, padx=(10, 0))

        self._image_link(footer_frame, "venmo.png", "Donate via Venmo",
                         VENMO_URL).pack(side=tk.RIGHT)
        self._image_link(footer_frame, "paypal.png", "Donate via PayPal",
                         PAYPAL_URL).pack(side=tk.RIGHT, padx=(0, 10))

    def _image_link(self, parent, image_name, fallback_text, url):
        """
        A clickable image (or gold text if the image is missing) that opens *url*.

        The label background matches the window so the transparent PNGs sit
        directly on the navy, as in Smart Citizen's footer.
        """
        label = tk.Label(
            parent,
            bg=theme.WINDOW_BG,
            cursor="hand2",
            borderwidth=0,
            highlightthickness=0
        )
        try:
            image_path = get_resource_path(os.path.join("assets", image_name))
            img = Image.open(image_path)
            width = int(img.width * FOOTER_IMAGE_HEIGHT / img.height)
            img = img.resize((width, FOOTER_IMAGE_HEIGHT), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            label.config(image=photo)
            label.image = photo  # Keep reference
        except Exception as e:
            logger.warning(f"Failed to load {image_name}: {e}")
            label.config(
                text=fallback_text.upper(),
                fg=theme.TITLE_COLOR,
                font=(theme.UI_FONT, 9, "bold")
            )
        label.bind("<Button-1>", lambda e: webbrowser.open(url))
        return label

    def _build_status_bar(self, parent):
        """Status text on the left, version on the right (Smart Citizen status bar)"""
        bar = tk.Frame(parent, bg=theme.PANEL_BG)
        bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.status_label = tk.Label(
            bar,
            text="Ready",
            bg=theme.PANEL_BG,
            fg=theme.TEXT,
            font=(theme.UI_FONT, 8),
            anchor=tk.W,
            padx=8,
            pady=3
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.version_label = tk.Label(
            bar,
            text=f"v{self.version}",
            bg=theme.PANEL_BG,
            fg=theme.TEXT,
            font=(theme.UI_FONT, 8),
            padx=8,
            pady=3,
            cursor="hand2"
        )
        self.version_label.pack(side=tk.RIGHT)
        self.version_label.bind("<Button-1>", lambda e: self._on_version_clicked())

    # ---------------------------------------------------------------- logging

    def _setup_logging(self):
        """Set up logging to the GUI text widget"""
        handler = TextHandler(self.log_text)
        handler.setLevel(logging.INFO)
        handler.setFormatter(SimpleFormatter())
        logging.getLogger().addHandler(handler)

    # --------------------------------------------------------------- settings

    def _load_settings(self):
        """Load settings and update UI"""
        keys_config = self.settings.get('keys_config', [])

        # Handle backward compatibility with old 'keys' format
        if not keys_config:
            old_keys = self.settings.get('keys', [])
            old_press_twice = self.settings.get('press_twice', False)
            keys_config = [{'key': k, 'press_twice': old_press_twice} for k in old_keys]

        for config in keys_config[:MAX_KEYS]:
            key_name = config.get('key', config) if isinstance(config, dict) else config
            press_twice = config.get('press_twice', False) if isinstance(config, dict) else False
            self._add_key_widget(key_name, press_twice)

        self._refresh_add_button()

        self.min_interval_var.set(self.settings.get('min_interval_minutes', 10))
        self.max_interval_var.set(self.settings.get('max_interval_minutes', 14))

    def _refresh_add_button(self, enabled=True):
        """Enable Add Key unless running or at the key limit"""
        self._set_button_enabled(
            self.add_key_button,
            theme.BUTTON_GOLD,
            enabled and len(self.key_rows) < MAX_KEYS
        )

    def _add_key(self):
        """Add a new key via detection dialog"""
        if len(self.key_rows) >= MAX_KEYS:
            messagebox.showwarning(
                "Maximum Keys Reached",
                "You can only configure a maximum of 3 keys.\n\nDelete an existing key before adding a new one."
            )
            return

        self._set_button_enabled(self.add_key_button, theme.BUTTON_GOLD, False)
        self.root.update()

        key = select_key(self.root)

        if key:
            self._add_key_widget(key)
            self._on_settings_changed()

        self._refresh_add_button()

    def _add_key_widget(self, key_name, press_twice=False):
        """
        Add a key row to the keys container.

        Args:
            key_name: Name of the key
            press_twice: Whether to press this key twice
        """
        row = {'key': key_name}
        key_frame = ttk.Frame(self.keys_container)
        key_frame.pack(fill=tk.X, pady=3)
        row['frame'] = key_frame

        row['label'] = tk.Label(
            key_frame,
            text=key_name.upper(),
            font=(theme.UI_FONT, 10, "bold"),
            width=10,
            bg=theme.PANEL_BG,
            fg=theme.TEXT,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=theme.BORDER,
            pady=2
        )
        row['label'].pack(side=tk.LEFT, padx=(0, 10))

        row['delete'] = self._action_button(
            key_frame, "Delete", theme.BUTTON_SLATE,
            lambda: self._remove_key_widget(row)
        )
        row['delete'].pack(side=tk.LEFT, padx=(0, 8))

        row['change'] = self._action_button(
            key_frame, "Change Key...", theme.BUTTON_GOLD,
            lambda: self._replace_key(row)
        )
        row['change'].pack(side=tk.LEFT, padx=(0, 12))

        row['press_twice'] = tk.BooleanVar(value=press_twice)
        row['check'] = ttk_bootstrap.Checkbutton(
            key_frame,
            text="Use Toggle Behavior",
            variable=row['press_twice'],
            command=self._on_settings_changed
        )
        row['check'].pack(side=tk.LEFT)

        self.key_rows.append(row)

    def _remove_key_widget(self, row):
        """Remove a key row"""
        self.key_rows.remove(row)
        row['frame'].destroy()
        self._refresh_add_button()
        self._on_settings_changed()

    def _replace_key(self, row):
        """Replace the key in a row via the detection dialog"""
        new_key = select_key(self.root)
        if new_key:
            row['key'] = new_key
            row['label'].config(text=new_key.upper())
            self._on_settings_changed()

    def _keys_config(self):
        return [{'key': r['key'], 'press_twice': r['press_twice'].get()} for r in self.key_rows]

    def _on_settings_changed(self):
        """Handle settings change"""
        self.settings.set('keys_config', self._keys_config())
        self.settings.set('min_interval_minutes', self.min_interval_var.get())
        self.settings.set('max_interval_minutes', self.max_interval_var.get())

    # ---------------------------------------------------------------- running

    def _start_pressing(self):
        """Start key pressing"""
        if not self.key_rows:
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

        keys_config = self._keys_config()

        # Update buttons FIRST
        self._set_running(True)
        self.root.update()  # Force GUI to update immediately

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
                self.root.after(0, self._set_running, False)

        threading.Thread(target=start_thread, daemon=True).start()

    def _stop_pressing(self):
        """Stop key pressing"""
        if self.key_presser:
            self.key_presser.stop()
        self._set_running(False)

    def _set_running(self, running):
        """Swap Start/Stop and lock the configuration while running"""
        self._set_button_enabled(self.start_button, theme.BUTTON_SAGE, not running)
        self._set_button_enabled(self.stop_button, theme.BUTTON_COPPER, running)
        self._set_config_enabled(not running)
        if not running:
            self._pending_status = "Ready"

    def _set_config_enabled(self, enabled):
        """
        Enable or disable configuration controls.

        Args:
            enabled: True to enable, False to disable
        """
        self._refresh_add_button(enabled)
        for row in self.key_rows:
            self._set_button_enabled(row['delete'], theme.BUTTON_SLATE, enabled)
            self._set_button_enabled(row['change'], theme.BUTTON_GOLD, enabled)

    def _on_key_presser_status(self, message):
        """
        Handle status message from the key presser thread.

        Only stores the text; _poll_status shows it from the Tk thread.
        """
        self._pending_status = message

    def _poll_status(self):
        """Copy the latest key presser status into the status bar"""
        if self._pending_status is not None:
            self.status_label.config(text=self._pending_status)
            self._pending_status = None
        self.root.after(250, self._poll_status)

    # ---------------------------------------------------------------- updates

    def _on_version_clicked(self):
        """Version label: open the update prompt if one is known, else check now"""
        if self._available_update:
            UpdateDialog(self.root, self._available_update, self.version, on_restart=self._on_close)
        else:
            self._check_for_updates(True)

    def _check_for_updates(self, manual):
        """
        Check GitHub for a newer release on a worker thread.

        Args:
            manual: True when the user clicked the version, so we also report
                "up to date" and errors instead of staying quiet
        """
        if self._update_check_running:
            return
        self._update_check_running = True
        if manual:
            self.status_label.config(text="Checking for updates...")

        def worker():
            try:
                self._update_queue.put(("ok", updater.check_for_update()))
            except Exception as e:
                logger.warning(f"Update check failed: {e}")
                self._update_queue.put(("error", str(e)))

        threading.Thread(target=worker, daemon=True).start()
        self._poll_update_check(manual)

    def _poll_update_check(self, manual):
        """Pick up the update check result on the main thread"""
        try:
            status, result = self._update_queue.get_nowait()
        except queue.Empty:
            self.root.after(200, self._poll_update_check, manual)
            return

        self._update_check_running = False

        if status == "error":
            if manual:
                self.status_label.config(text="Update check failed")
                messagebox.showwarning(
                    "Update Check Failed",
                    f"Couldn't reach GitHub to check for updates:\n{result}"
                )
        elif result is None:
            if manual:
                self.status_label.config(text=f"You're on the latest version (v{self.version})")
        else:
            logger.info(f"Update available: v{result['version']}")
            self._available_update = result
            # Like Smart Citizen, the version indicator lights up when an update exists
            self.version_label.config(
                text=f"v{self.version}  →  v{result['version']} available",
                fg=theme.LINK
            )
            UpdateDialog(self.root, result, self.version, on_restart=self._on_close)

    def _on_close(self):
        """Handle window close event"""
        if self.key_presser and self.key_presser.is_running():
            self.key_presser.stop()
        self.root.destroy()
