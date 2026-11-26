---
description: Release the active release/X.Y.Z of Extended AFK — bump the version, open the release PR, run the code review, and merge on Amr's OK
---

# /release

One release PR, `release/X.Y.Z` → `main`, where the Build workflow and the code review run once. Amr calling the release is the approval for every step up to the merge; the merge waits for Amr's explicit OK.

1. **Check out** the active `release/X.Y.Z` (the only open `release/*` branch) and pull it.
2. **Bump** on the release branch, as one commit pushed straight to it (see `docs/RELEASE_PROCESS.md` step 1): `VERSION.TXT`, `extended-afk.spec` and `docs/CHANGELOG.md` (`[Unreleased]` → `## [X.Y.Z] - YYYY-MM-DD`). `python scripts/release_tools.py check` must pass.
3. **Open the release PR** `release/X.Y.Z` → `main`, titled `Release X.Y.Z`. Body: `python scripts/release_tools.py notes X.Y.Z`, then the sections of `docs/TEST_PLAN.md` as a checklist. The **Build** workflow builds the exe.
4. **Review**: run `/code-review` on the PR. Fix what it finds with more commits on the release branch (each rebuilds the exe).
5. **Amr tests**: Amr downloads the exe from the PR's Build artifacts and runs the test plan. Merge only when Amr says to, with a merge commit (`gh pr merge <N> --merge`), never squash.
6. **Watch** the Release workflow until the GitHub release is live with `ExtendedAFK-vX.Y.Z.exe` and the Discord post has gone out; if the Discord step was skipped or failed, post it manually.
7. **Website tile**: update the Extended AFK entry in `../osiris-devworks-website/src/data/projects.ts`, following that repo's own pipeline.
8. Offer `/start_release patch|minor|major` for the next branch.
