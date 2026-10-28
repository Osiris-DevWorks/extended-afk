"""Update-available dialog with release notes and download progress"""
import tkinter as tk
from tkinter import ttk
import threading
import queue
import webbrowser
import logging

from core import updater

logger = logging.getLogger(__name__)


class UpdateDialog:
    """
    Modal dialog shown when a newer release is on GitHub.

    Offers Update Now (download the new exe, then restart into it) when
    self-update can work, otherwise Open Release Page. Later just closes.
    The download runs on a worker thread that reports through a queue the
    dialog polls, so tkinter is only touched from the main thread.
    """

    def __init__(self, parent, update_info, current_version, on_restart):
        """
        Args:
            parent: Parent window
            update_info: Dict from updater.check_for_update()
            current_version: Running version string
            on_restart: Called after the update helper starts; should close the app
        """
        self.parent = parent
        self.info = update_info
        self.on_restart = on_restart
        self.can_auto_update = bool(update_info.get("asset")) and updater.can_self_update()

        self._queue = queue.Queue()
        self._cancel_event = threading.Event()
        self._downloading = False

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Update Available")
        self.dialog.geometry("480x420")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)

        self._build_ui(current_version)

        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")

        self.dialog.protocol("WM_DELETE_WINDOW", self._on_later)
        self.dialog.grab_set()

    def _build_ui(self, current_version):
        frame = ttk.Frame(self.dialog, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            frame,
            text=f"Extended AFK v{self.info['version']} is available (you have v{current_version}).",
            font=("Segoe UI", 10, "bold"),
            wraplength=440
        ).pack(anchor=tk.W, pady=(0, 10))

        notes_frame = ttk.Frame(frame)
        notes_frame.pack(fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(notes_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        notes = tk.Text(
            notes_frame,
            height=12,
            wrap=tk.WORD,
            font=("Segoe UI", 9),
            yscrollcommand=scrollbar.set
        )
        notes.insert("1.0", self.info.get("notes") or "No release notes.")
        notes.config(state='disabled')
        notes.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=notes.yview)

        self.status_label = ttk.Label(frame, text="", font=("Segoe UI", 9), wraplength=440)
        self.status_label.pack(anchor=tk.W, pady=(10, 0))
        if self.can_auto_update:
            self.status_label.config(
                text="Update Now downloads the new version and restarts Extended AFK. "
                     "Your settings are kept."
            )

        self.progress = ttk.Progressbar(frame, mode='determinate', maximum=100)

        buttons = ttk.Frame(frame)
        buttons.pack(fill=tk.X, pady=(10, 0))
        self.later_button = ttk.Button(buttons, text="Later", command=self._on_later)
        self.later_button.pack(side=tk.RIGHT)
        if self.can_auto_update:
            self.primary_button = ttk.Button(buttons, text="Update Now", command=self._on_update)
        else:
            self.primary_button = ttk.Button(buttons, text="Open Release Page", command=self._on_open_page)
        self.primary_button.pack(side=tk.RIGHT, padx=(0, 10))

    def _on_open_page(self):
        webbrowser.open(self.info["page_url"])
        self._close()

    def _on_later(self):
        if self._downloading:
            # Cancel; the worker reports back and the dialog stays open
            self._cancel_event.set()
            self.later_button.config(state='disabled')
            return
        self._close()

    def _on_update(self):
        url, name, size = self.info["asset"]
        self._downloading = True
        self.primary_button.config(state='disabled')
        self.later_button.config(text="Cancel")
        self.status_label.config(text="Downloading...")
        self.progress.pack(fill=tk.X, pady=(5, 0), before=self.later_button.master)

        def progress(done, total):
            self._queue.put(("progress", done, total))

        def worker():
            try:
                path = updater.download_update(
                    url, name, size,
                    progress_callback=progress,
                    cancel_event=self._cancel_event
                )
                self._queue.put(("done", path))
            except updater.UpdateCancelled:
                self._queue.put(("cancelled",))
            except Exception as e:
                logger.error(f"Update download failed: {e}", exc_info=True)
                self._queue.put(("error", str(e)))

        threading.Thread(target=worker, daemon=True).start()
        self._poll()

    def _poll(self):
        try:
            while True:
                msg = self._queue.get_nowait()
                if msg[0] == "progress":
                    done, total = msg[1], msg[2]
                    mb = 1024 * 1024
                    if total:
                        self.progress.config(value=done * 100 / total)
                        self.status_label.config(text=f"Downloading... {done / mb:.1f} / {total / mb:.1f} MB")
                    else:
                        self.status_label.config(text=f"Downloading... {done / mb:.1f} MB")
                elif msg[0] == "done":
                    self._finish(msg[1])
                    return
                elif msg[0] == "cancelled":
                    logger.info("Update download cancelled")
                    self._downloading = False
                    self._close()
                    return
                elif msg[0] == "error":
                    self._downloading = False
                    self.progress.pack_forget()
                    self.status_label.config(
                        text=f"Download failed: {msg[1][:120]}\nYou can download it from the release page instead."
                    )
                    self.later_button.config(text="Later", state='normal')
                    self.primary_button.config(text="Open Release Page", command=self._on_open_page, state='normal')
                    return
        except queue.Empty:
            pass
        self.dialog.after(100, self._poll)

    def _finish(self, new_exe):
        self.status_label.config(text="Restarting into the new version...")
        try:
            updater.launch_replacement(new_exe)
        except Exception as e:
            logger.error(f"Failed to start update helper: {e}", exc_info=True)
            self._downloading = False
            self.progress.pack_forget()
            self.status_label.config(
                text=f"Couldn't restart automatically. The new version was saved to:\n{new_exe}"
            )
            self.later_button.config(text="Close", state='normal')
            return
        self._downloading = False
        self._close()
        self.on_restart()

    def _close(self):
        try:
            self.dialog.grab_release()
        except tk.TclError:
            pass
        self.dialog.destroy()
