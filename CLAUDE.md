# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Extended AFK is a Windows-only GUI utility that presses configured keyboard keys at random intervals to prevent AFK timeouts in games. ttkbootstrap (tkinter) for the GUI, the `keyboard` library for simulating presses, `pynput` for detecting which key the user wants. Ships as a single portable `.exe` (PyInstaller onefile), no installer.

## Commands

```bash
pip install -r requirements.txt                          # install deps
python src/main.py                                       # run from source
python -m PyInstaller extended-afk.spec --clean --noconfirm  # build dist/ExtendedAFK-vX.Y.Z.exe
python scripts/release_tools.py check                    # VERSION.TXT, spec and changelog agree
```

There are no automated tests; verify changes by running the app and watching the Activity Log (and `%APPDATA%\extended-afk\logs\extended-afk.log`). The **Build** workflow (`.github/workflows/build.yml`) builds the exe on every PR and uploads it as an artifact for testing.

## Architecture

Small three-layer app under `src/`:

- `main.py`: entry point. **Imports `keyboard` before anything else, including tkinter**, so its low-level hooks initialize first; keep that import at the top. Also sets up rotating file logging to `%APPDATA%\extended-afk\logs\`.
- `core/key_presser.py`: `KeyPresser` runs a daemon thread that waits a random interval between the configured min/max minutes, then presses each configured key (optionally twice, 2 s apart, for "Use Toggle Behavior"). Each press is held for `KEY_HOLD_SECONDS` (100 ms) via `keyboard.press`/`release`, because games that poll once per frame miss an instant tap. It logs the foreground window each press went to and warns when not elevated (Windows blocks injected input to elevated games); those helpers live in `utils/windows.py`. All waits go through `threading.Event.wait` so Stop interrupts immediately. Status text flows back to the GUI via a callback, never by touching widgets from the worker thread.
- `core/settings.py`: `AppSettings` persists JSON to `%APPDATA%\extended-afk\settings.json`, merging loaded values over defaults and validating (positive intervals, min <= max). `set()` saves on every call.
- `gui/main_window.py`: the whole UI (dynamic key rows, interval fields, start/stop button, log panel). Config widgets are disabled while the presser runs. Color constants intentionally match the sibling `sc-profile-editor` project.
- `core/updater.py`: auto-updater, modeled on Smart Citizen's `app_updater.py`. Checks `GET /repos/Osiris-DevWorks/extended-afk/releases/latest` (unauthenticated) against the bundled `VERSION.TXT`, finds the `ExtendedAFK-vX.Y.Z.exe` asset, downloads it next to the running exe (`.part` then rename), and starts a batch helper that deletes the old exe once it unlocks and launches the new one. Self-update only runs from the frozen exe on Windows; from source the dialog offers the release page. Tk-free.
- `gui/update_dialog.py`: release notes + Update Now / Open Release Page / Later, with download progress. `MainWindow` checks once ~1.5 s after launch (silent unless an update exists) and from the footer's "Check for updates" link. Worker threads report through queues polled with `after()`.
- `gui/key_selector.py`: modal "press any key" detection dialog built on a `pynput` listener.
- `gui/text_handler.py`: logging handler that mirrors log records into the GUI's Activity Log text widget.
- `utils/resource_path.py`: PyInstaller-aware asset path resolution (`sys._MEIPASS` vs source tree). Use it for anything under `assets/`.

## Versioning and release

Version lives in three places that must stay in sync: `VERSION.TXT`, `docs/CHANGELOG.md`, and the hardcoded exe name in `extended-afk.spec` (`name='ExtendedAFK-vX.Y.Z'`). Bump all three together.

The release flow is documented in `docs/RELEASE_PROCESS.md` and driven by the `/release` command (`.claude/commands/release.md`). Like Smart Citizen, merging a version bump to `main` is the release: `.github/workflows/release.yml` runs on every push to main, and if no release exists for `VERSION.TXT`'s version it checks the three version files (`scripts/release_tools.py check`), builds the exe on Windows, creates and pushes the `vX.Y.Z` tag, publishes the GitHub release with the exe attached and the changelog section as notes, then announces via `scripts/discord_notify.py` (needs the `DISCORD_RELEASE_WEBHOOK_URL` repo secret, or `.env` when run locally). The GitHub release must be live before the Discord post fires. The asset must stay named `ExtendedAFK-vX.Y.Z.exe` or the in-app updater won't find it.

On every release, also update the Extended AFK entry in `../osiris-devworks-website/src/data/projects.ts` (sibling workspace repo): bump the static `version` fallback and refresh `features`/`status` for what shipped. The site auto-fetches the live version from this repo's `VERSION.TXT` on `main`, but everything else on the tile is manual. Pushing the website repo's `main` deploys it.
