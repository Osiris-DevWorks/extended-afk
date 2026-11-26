# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Osiris DevWorks development pipeline (universal)

This section is identical in every Osiris DevWorks repo's CLAUDE.md. Change it in all of them at once. The line just below it says how this repo applies it. Where an older section of this file conflicts with it, this section wins.

The goal is little friction and few GitHub Actions runs: checks and code review run once per release, not once per feature.

1. **Grill the idea.** When Amr brings a new idea, ask questions until it is ready to build. Ask every question as a multiple-choice decision card (`request_decision`, or `AskUserQuestion` in the CLI) with a recommended option, never as questions in prose. A few cards at a time is fine.
2. **Mock up any UI.** When a feature adds or changes UI, show an HTML Artifact mockup during grilling. Build it from the app's real colors, fonts, spacing and layout, read from the source, and show the current screen next to the changed one. Grilling isn't done until Amr approves the mockup.
3. **Grilling sign-off is the approval.** Once Amr says the idea is ready, build it without further check-ins: no step-by-step plan approvals, no code-block reviews, and no commit-message review. Ask again only if the work hits a choice that grilling did not settle.
4. **Push straight to the integration branch, with no feature PR.** Run the repo's tests, lint and type check in your own session. Update this repo's test plan, if it has one, with concrete pass/fail items for the feature. Then push **one squashed commit per feature** to the integration branch, with a message like `#123: short summary` (`Fixes #123` in the body when it closes the issue). A feature branch is fine while you work; only the squashed result lands. Never force-push the integration branch.
5. **Release: one PR, all checks, one review.** When Amr calls a release, open one PR from the integration branch to production. Every pre-release check and the code review run on that PR, once. Fix what they find with more commits on the integration branch. Amr runs the test plan (on preview builds or staging) and merges, or tells you to merge.
6. **Hotfixes.** For an urgent production fix, branch off production, open a PR straight to production (full checks and review run on it), and once it merges, merge production back into the integration branch.
7. **Outside PRs.** Contributor and Dependabot PRs get CI only, with no Claude review bot. Dependabot is grouped and runs monthly.
8. **Workflow triggers.** Keep workflows off feature work: no `push` triggers on integration branches except where a deploy needs one, and the Claude review workflow runs only on PRs into production. Don't add a workflow that runs on every push without Amr's OK.

**How this repo applies it: desktop app.** The integration branch is the active `release/X.Y.Z` (opened off `main` by `/start_release`, named for the version it will ship) and production is `main`. There are no automated tests, so "run the tests" means `python -m compileall -q src scripts`, a local build, and a run of the app. The test plan is `docs/TEST_PLAN.md`: each feature push adds its own `### #issue: short name` section of pass/fail items. Amr runs it on the exe that the release PR's **Build** workflow uploads, before the PR merges. The code review is a `/code-review` pass on that PR during `/release`. See `docs/RELEASE_PROCESS.md`.

## What this is

Extended AFK is a Windows-only GUI utility that presses configured keyboard keys at random intervals to prevent AFK timeouts in games. ttkbootstrap (tkinter) for the GUI, the `keyboard` library for simulating presses, `pynput` for detecting which key the user wants. Ships as a single portable `.exe` (PyInstaller onefile), no installer.

## Commands

```bash
pip install -r requirements.txt                          # install deps
python src/main.py                                       # run from source
python -m PyInstaller extended-afk.spec --clean --noconfirm  # build dist/ExtendedAFK-vX.Y.Z.exe
python scripts/release_tools.py check                    # VERSION.TXT, spec and changelog agree
```

There are no automated tests; verify changes by running the app and watching the Activity Log (and `%APPDATA%\extended-afk\logs\extended-afk.log`). The **Build** workflow (`.github/workflows/build.yml`) builds the exe on PRs into `main` and `release/**` (the release PR, hotfix and contributor PRs) and uploads it as an artifact for testing.

## Architecture

Small three-layer app under `src/`:

- `main.py`: entry point. **Imports `keyboard` before anything else, including tkinter**, so its low-level hooks initialize first; keep that import at the top. Also sets up rotating file logging to `%APPDATA%\extended-afk\logs\`.
- `core/key_presser.py`: `KeyPresser` runs a daemon thread that waits a random interval between the configured min/max minutes, then presses each configured key (optionally twice, 2 s apart, for "Use Toggle Behavior"). Each press is held for `KEY_HOLD_SECONDS` (100 ms) via `keyboard.press`/`release`, because games that poll once per frame miss an instant tap. It logs the foreground window each press went to and warns when not elevated (Windows blocks injected input to elevated games); those helpers live in `utils/windows.py`. All waits go through `threading.Event.wait` so Stop interrupts immediately. Status text flows back to the GUI via a callback, never by touching widgets from the worker thread.
- `core/settings.py`: `AppSettings` persists JSON to `%APPDATA%\extended-afk\settings.json`, merging loaded values over defaults and validating (positive intervals, min <= max). `set()` saves on every call.
- `gui/main_window.py`: the whole UI (branded header, dynamic key rows, interval fields, start/stop buttons, log panel, Osiris/Discord/donation footer, status bar with the version). Config widgets are disabled while the presser runs.
- `gui/theme.py`: the Osiris DevWorks theme ported from Smart Citizen's `odw` theme (`src/gui/theme.py` there): palette, title/tagline colors, action-button colors, and the bundled brand font `assets/fonts/HyperspaceRace-ExpandedBold.otf` (registered privately with GDI on Windows). Keep its hex values in step with Smart Citizen. Action buttons are flat `tk.Button`s from `theme.action_button`; use `theme.set_button_enabled` so disabled ones dim. Use `ttkbootstrap` widget classes (not plain `ttk`) for Spinbox/Checkbutton/Scrollbar/Progressbar, or ttkbootstrap 2.x leaves them unthemed.
- `core/updater.py`: auto-updater, modeled on Smart Citizen's `app_updater.py`. Checks `GET /repos/Osiris-DevWorks/extended-afk/releases/latest` (unauthenticated) against the bundled `VERSION.TXT`, finds the `ExtendedAFK-vX.Y.Z.exe` asset, downloads it next to the running exe (`.part` then rename), and starts a batch helper that deletes the old exe once it unlocks and launches the new one. Self-update only runs from the frozen exe on Windows; from source the dialog offers the release page. Tk-free.
- `gui/update_dialog.py`: release notes + Update Now / Open Release Page / Later, with download progress. `MainWindow` checks once ~1.5 s after launch (silent unless an update exists). Clicking the status bar's version label checks again, or reopens the dialog once an update is known. Worker threads report through queues polled with `after()`.
- `gui/key_selector.py`: modal "press any key" detection dialog built on a `pynput` listener.
- `gui/text_handler.py`: logging handler that mirrors log records into the GUI's Activity Log text widget.
- `utils/resource_path.py`: PyInstaller-aware asset path resolution (`sys._MEIPASS` vs source tree). Use it for anything under `assets/`.

## Versioning and release

Version lives in three places that must stay in sync: `VERSION.TXT`, `docs/CHANGELOG.md`, and the hardcoded exe name in `extended-afk.spec` (`name='ExtendedAFK-vX.Y.Z'`). Bump all three together.

The release flow is documented in `docs/RELEASE_PROCESS.md` and driven by `/start_release` (opens the next `release/X.Y.Z`) and `/release` (bumps the version on it and opens the release PR). Like Smart Citizen, merging the release branch, with its version bump, to `main` is the release: `.github/workflows/release.yml` runs on every push to main, and if no release exists for `VERSION.TXT`'s version it checks the three version files (`scripts/release_tools.py check`), builds the exe on Windows, creates and pushes the `vX.Y.Z` tag, publishes the GitHub release with the exe attached and the changelog section as notes, then announces via `scripts/discord_notify.py` (needs the `DISCORD_RELEASE_WEBHOOK_URL` repo secret, or `.env` when run locally). The GitHub release must be live before the Discord post fires. The asset must stay named `ExtendedAFK-vX.Y.Z.exe` or the in-app updater won't find it.

On every release, also update the Extended AFK entry in `../osiris-devworks-website/src/data/projects.ts` (sibling workspace repo): bump the static `version` fallback and refresh `features`/`status` for what shipped. The site auto-fetches the live version from this repo's `VERSION.TXT` on `main`, but everything else on the tile is manual. That repo's own pipeline publishes it.
