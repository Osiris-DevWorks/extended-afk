"""Check GitHub Releases for a newer Extended AFK and swap in the new exe.

Same idea as Smart Citizen's app updater: hit the public ``/releases/latest``
endpoint (no auth), compare ``tag_name`` against the bundled ``VERSION.TXT``,
and offer the release's exe asset. GitHub allows 60 unauthenticated requests
per hour per IP; we make one per launch plus one per manual check.

Extended AFK ships as a single portable exe rather than an installer, so the
install step is different: the new exe is downloaded next to the running one
(``.part`` first, renamed when complete, so a half download is never
runnable), then a small batch script waits for this process to exit, deletes
the old exe and launches the new one.

Nothing in this module touches tkinter; the GUI calls these from a worker
thread.
"""
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request

from utils.resource_path import get_resource_path

logger = logging.getLogger(__name__)

GITHUB_API_URL = "https://api.github.com/repos/Osiris-DevWorks/extended-afk/releases/latest"
RELEASES_PAGE_URL = "https://github.com/Osiris-DevWorks/extended-afk/releases/latest"
REQUEST_TIMEOUT_SECONDS = 10
DOWNLOAD_CHUNK_BYTES = 256 * 1024

# Release-asset name for the exe, e.g. ExtendedAFK-v1.0.3.exe. Full match so
# other assets (zips, checksums) never get picked up.
_EXE_ASSET_RE = re.compile(r"extendedafk-v?\d+\.\d+\.\d+\.exe", re.IGNORECASE)


class UpdateCancelled(Exception):
    """Raised when the user cancels a download"""


def get_current_version():
    """
    Read the running version from the bundled VERSION.TXT.

    Returns:
        str: Version like '1.0.3', or '0.0.0' if it can't be read
    """
    try:
        with open(get_resource_path("VERSION.TXT"), "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError as e:
        logger.warning(f"Could not read VERSION.TXT: {e}")
        return "0.0.0"


def parse_version(s):
    """
    Parse 'major.minor.patch' (optionally 'v'-prefixed) into a tuple.

    Returns:
        tuple or None: None if unparseable, so callers treat it as
        "can't compare" rather than "equal"
    """
    if not s:
        return None
    parts = s.strip().lstrip("vV").split(".")
    if len(parts) < 2:
        return None
    try:
        nums = [int(p) for p in parts[:3]]
    except ValueError:
        return None
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums)


def is_newer(latest, current):
    """
    Check whether latest is strictly newer than current.

    Unparseable input on either side returns False, so we never prompt
    based on a malformed tag.
    """
    lt = parse_version(latest)
    ct = parse_version(current)
    if lt is None or ct is None:
        return False
    return lt > ct


def pick_exe_asset(assets):
    """
    Find the exe in a release's assets.

    Args:
        assets: The 'assets' array from a GitHub release payload

    Returns:
        tuple or None: (download_url, name, size_bytes), or None if the
        release has no exe attached
    """
    for asset in assets or []:
        try:
            name = (asset.get("name") or "").strip()
            url = (asset.get("browser_download_url") or "").strip()
            size = int(asset.get("size") or 0)
        except (AttributeError, TypeError, ValueError):
            continue
        if url and _EXE_ASSET_RE.fullmatch(name):
            return (url, name, size)
    return None


def check_for_update():
    """
    Ask GitHub for the latest release.

    Returns:
        dict or None: None when up to date, otherwise a dict with 'version',
        'page_url', 'notes', and 'asset' (pick_exe_asset result or None)

    Raises:
        Exception: Network or payload errors, for the caller to log
    """
    current = get_current_version()
    req = urllib.request.Request(
        GITHUB_API_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"ExtendedAFK/{current}",
        },
    )
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
        payload = json.load(resp)

    tag = (payload.get("tag_name") or "").strip()
    if not tag:
        raise ValueError("Release payload missing tag_name")

    if not is_newer(tag, current):
        logger.info(f"Extended AFK is up to date at v{current}")
        return None

    asset = pick_exe_asset(payload.get("assets"))
    logger.info(
        f"Update available: {tag} (current v{current}, "
        f"exe asset: {'yes' if asset else 'no'})"
    )
    return {
        "version": tag.lstrip("vV"),
        "page_url": (payload.get("html_url") or RELEASES_PAGE_URL).strip(),
        "notes": (payload.get("body") or "").replace("\r\n", "\n").strip(),
        "asset": asset,
    }


def can_self_update():
    """
    Self-update only works from the built exe on Windows. From source there
    is no exe to replace, so the GUI offers the release page instead.
    """
    return sys.platform == "win32" and getattr(sys, "frozen", False)


def download_update(url, name, expected_size=0, progress_callback=None, cancel_event=None):
    """
    Download the new exe into the folder the running exe lives in.

    Args:
        url: Asset download URL
        name: Asset file name, e.g. ExtendedAFK-v1.0.3.exe
        expected_size: Size from the release payload, used when the server
            sends no Content-Length
        progress_callback: Optional callable(done_bytes, total_bytes)
        cancel_event: Optional threading.Event; set it to cancel

    Returns:
        str: Path to the downloaded exe

    Raises:
        UpdateCancelled: If cancel_event was set
        Exception: Network or disk errors
    """
    dest_dir = os.path.dirname(os.path.abspath(sys.executable))
    safe_name = os.path.basename(urllib.parse.unquote(name))
    if not safe_name.lower().endswith(".exe"):
        safe_name = "ExtendedAFK-update.exe"
    target = os.path.join(dest_dir, safe_name)
    part = target + ".part"

    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/octet-stream",
            "User-Agent": f"ExtendedAFK/{get_current_version()}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
            total = int(resp.headers.get("Content-Length") or 0) or expected_size
            done = 0
            with open(part, "wb") as fh:
                while True:
                    if cancel_event is not None and cancel_event.is_set():
                        raise UpdateCancelled("Download cancelled")
                    chunk = resp.read(DOWNLOAD_CHUNK_BYTES)
                    if not chunk:
                        break
                    fh.write(chunk)
                    done += len(chunk)
                    if progress_callback:
                        progress_callback(done, total)
        if total and done != total:
            raise IOError(f"Download incomplete ({done} of {total} bytes)")
        os.replace(part, target)
    except BaseException:
        try:
            os.remove(part)
        except OSError:
            pass
        raise

    logger.info(f"Update downloaded to {target}")
    return target


def launch_replacement(new_exe):
    """
    Start a helper that swaps the old exe for the new one once we exit.

    The batch script keeps trying to delete the running exe (it's locked
    until this process and PyInstaller's bootloader have both exited), then
    starts the new exe and deletes itself. The caller must close the app
    right after this returns.

    Args:
        new_exe: Path returned by download_update
    """
    old_exe = os.path.abspath(sys.executable)
    new_exe = os.path.abspath(new_exe)

    # chcp 65001 so cmd reads the paths below as UTF-8
    lines = ["@echo off", "chcp 65001 >NUL", "set tries=0"]
    if os.path.normcase(old_exe) != os.path.normcase(new_exe):
        lines += [
            ":retry",
            f'del /f /q "{old_exe}" >NUL 2>&1',
            f'if not exist "{old_exe}" goto launch',
            "set /a tries+=1",
            "if %tries% GEQ 60 goto launch",
            # timeout.exe refuses to run without a console; ping waits ~1s
            "ping -n 2 127.0.0.1 >NUL",
            "goto retry",
        ]
    lines += [
        ":launch",
        f'start "" "{new_exe}"',
        '(goto) 2>NUL & del "%~f0"',
    ]

    fd, script = tempfile.mkstemp(prefix="extended-afk-update-", suffix=".bat")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("\r\n".join(lines) + "\r\n")

    # Launching one PyInstaller onefile exe from another inherits the parent's
    # bootloader environment unless told to reset it.
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("_PYI") and k != "_MEIPASS2"}
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"

    subprocess.Popen(
        ["cmd.exe", "/c", script],
        env=env,
        close_fds=True,
        creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP,
    )
    logger.info(f"Update helper started ({script}); exiting so {new_exe} can take over")
