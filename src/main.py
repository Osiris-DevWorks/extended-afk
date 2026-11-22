"""Main entry point for Extended AFK application"""
# Import keyboard library FIRST, before anything else
# This initializes keyboard hooks before tkinter starts
try:
    import keyboard
except Exception as e:
    print(f"Warning: Failed to import keyboard library: {e}")

import tkinter as tk
import ttkbootstrap as ttk_bootstrap
import logging
from logging.handlers import RotatingFileHandler
import os
import sys

# Add src directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.main_window import MainWindow


def setup_logging():
    """Set up logging with file and console handlers"""
    # Create logs directory
    log_dir = os.path.join(os.getenv('APPDATA'), 'extended-afk', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'extended-afk.log')

    # Root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # File handler (rotating, 5MB max, 3 backups)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    )
    logger.addHandler(file_handler)

    # Console handler (for development)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(
        logging.Formatter(
            '%(levelname)s - %(message)s'
        )
    )
    logger.addHandler(console_handler)

    # Suppress noisy debug logging from PIL
    logging.getLogger('PIL').setLevel(logging.WARNING)

    logger.info("Extended AFK started")


def main():
    """Main application entry point"""
    # Set up logging
    setup_logging()

    try:
        # Start from darkly; MainWindow switches to the Osiris DevWorks
        # theme (gui/theme.py) shared with Smart Citizen
        root = ttk_bootstrap.Window(themename="darkly")

        # Create main window
        app = MainWindow(root)

        # Start event loop
        root.mainloop()

    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
