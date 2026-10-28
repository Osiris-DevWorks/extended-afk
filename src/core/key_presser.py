"""Key pressing logic with threading support"""
import keyboard
import time
import random
import threading
import logging

from utils.windows import is_admin, foreground_window_title

logger = logging.getLogger(__name__)

# How long each key is held down. Many games poll input once per frame, so an
# instant press-and-release can fall between two polls and never register.
KEY_HOLD_SECONDS = 0.1


class KeyPresser:
    """Handles automatic key pressing in a background thread"""

    def __init__(self, keys_config, min_interval_minutes, max_interval_minutes, status_callback=None):
        """
        Initialize key presser.

        Args:
            keys_config: List of dicts with 'key' and 'press_twice' settings
            min_interval_minutes: Minimum interval between presses (in minutes)
            max_interval_minutes: Maximum interval between presses (in minutes)
            status_callback: Optional callback function for status updates (receives message string)
        """
        self.keys_config = keys_config
        self.min_interval = min_interval_minutes * 60  # Convert to seconds
        self.max_interval = max_interval_minutes * 60  # Convert to seconds
        self.status_callback = status_callback

        # Threading control
        self._thread = None
        self._stop_event = threading.Event()
        self._running = False

    def start(self):
        """Start the key pressing thread"""
        if self._running:
            logger.warning("Key pressing already active")
            return

        self._stop_event.clear()
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("Starting key presser...")
        self._send_status("Key pressing started")

    def stop(self):
        """Stop the key pressing thread"""
        if not self._running:
            logger.warning("Key pressing not active")
            return

        self._stop_event.set()
        self._running = False

        # Wait for thread to finish (with timeout)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

        logger.info("Key pressing stopped")
        self._send_status("Key pressing stopped")

    def is_running(self):
        """
        Check if key presser is currently running.

        Returns:
            bool: True if running, False otherwise
        """
        return self._running

    def _run(self):
        """Main thread worker function"""
        try:
            if not is_admin():
                logger.info(
                    "Extended AFK is not running as administrator. If your game "
                    "runs as administrator, Windows will block these key presses; "
                    "right-click Extended AFK and choose 'Run as administrator'."
                )
            logger.info("Key presses go to the focused window, so keep the game in focus.")

            # Initial delay
            self._send_status("Initializing... (5 second countdown)")

            if self._wait_interruptible(5):
                return

            # First key press
            self._press_keys()

            # Main loop
            while not self._stop_event.is_set():
                # Calculate random interval
                interval = random.randint(int(self.min_interval), int(self.max_interval))
                minutes = interval // 60
                seconds = interval % 60

                if seconds > 0:
                    self._send_status(f"Next press in {minutes}m {seconds}s")
                else:
                    self._send_status(f"Next press in {minutes} minutes")

                # Wait for interval (or stop event)
                if self._wait_interruptible(interval):
                    break

                # Press keys
                self._press_keys()

        except Exception as e:
            logger.error(f"Error in key presser thread: {e}", exc_info=True)
            self._send_status(f"Error: {str(e)[:50]}")
        finally:
            self._running = False

    def _wait_interruptible(self, seconds):
        """
        Wait for specified seconds, but can be interrupted by stop event.

        Args:
            seconds: Number of seconds to wait

        Returns:
            bool: True if interrupted, False if wait completed normally
        """
        return self._stop_event.wait(seconds)

    def _press_keys(self):
        """Press the configured keys"""
        try:
            if not self.keys_config:
                logger.warning("No keys configured")
                return

            logger.debug(f"Pressing {len(self.keys_config)} key(s): {self.keys_config}")

            pressed_keys = []
            for i, config in enumerate(self.keys_config):
                key_name = config['key']
                press_twice = config.get('press_twice', False)

                try:
                    logger.debug(f"Pressing key {i+1}/{len(self.keys_config)}: {key_name} (press_twice={press_twice})")

                    self._tap(key_name)
                    pressed_keys.append(key_name.upper())
                    logger.debug(f"Successfully pressed: {key_name}")

                    if press_twice:
                        # Hold for 2 seconds between presses so toggle behavior
                        # registers (interruptible by stop event)
                        if self._stop_event.wait(2.0):
                            logger.debug("Stop requested during toggle interval")
                            return
                        logger.debug(f"Pressing second time: {key_name}")
                        self._tap(key_name)
                        logger.debug(f"Successfully pressed second time: {key_name}")

                    # Delay between different keys
                    time.sleep(0.5)

                except Exception as e:
                    logger.error(f"Error pressing key '{key_name}': {e}")
                    self._send_status(f"Error pressing {key_name}: {str(e)[:30]}")

            if pressed_keys:
                keys_str = " + ".join(pressed_keys)
                window = foreground_window_title()
                if window:
                    logger.info(f"Pressed: {keys_str} (sent to '{window}')")
                else:
                    logger.info(f"Pressed: {keys_str}")
                self._send_status(f"Pressed: {keys_str}")
            else:
                logger.warning("No keys were successfully pressed")

        except Exception as e:
            logger.error(f"Error in _press_keys: {e}", exc_info=True)
            self._send_status(f"Error pressing keys")

    def _tap(self, key_name):
        """
        Press a key (or combo like 'ctrl+a'), hold it briefly, then release it.

        Args:
            key_name: Key name understood by the keyboard library
        """
        keyboard.press(key_name)
        try:
            time.sleep(KEY_HOLD_SECONDS)
        finally:
            keyboard.release(key_name)

    def _send_status(self, message):
        """
        Send status message via callback.

        Args:
            message: Status message string
        """
        if self.status_callback:
            try:
                self.status_callback(message)
            except Exception as e:
                logger.error(f"Error in status callback: {e}")
