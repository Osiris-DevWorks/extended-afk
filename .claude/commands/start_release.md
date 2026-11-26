---
description: Open the next release/X.Y.Z integration branch off main (major|minor|patch)
---

# /start_release

Open the next integration branch, per the Osiris DevWorks pipeline in CLAUDE.md. Features are then pushed straight to it as one squashed commit each.

## Argument

`$ARGUMENTS`: one of `major`, `minor`, `patch`, applied to the current `VERSION.TXT` on `main` (`X.Y.Z` → `(X+1).0.0`, `X.(Y+1).0` or `X.Y.(Z+1)`). Anything else: abort and ask.

## Steps

Stop on the first failure.

1. `git fetch origin main`. Abort if another `release/*` branch is still open on origin (`git ls-remote --heads origin 'release/*'`) and not yet merged to `main`; name it.
2. Compute `NEW_VERSION` and check `release/NEW_VERSION` does not exist locally or on origin.
3. `git checkout -b release/NEW_VERSION origin/main`.
4. Clear the shipped release's sections from `docs/TEST_PLAN.md` (keep `## Next release` with `_No features yet._`), commit `Open release/NEW_VERSION`, and push: `git push -u origin release/NEW_VERSION`.
5. Report the branch and the scope: a patch branch takes bug fixes and polish only; features wait for a minor.

`VERSION.TXT`, the spec and the changelog section are bumped together by `/release`, at the end of the cycle, because `scripts/release_tools.py check` wants all three to agree.
