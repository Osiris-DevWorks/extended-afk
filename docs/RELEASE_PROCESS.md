# Release Process

**For:** Release managers - Creating and publishing new versions

Releases are built and published by GitHub Actions (`.github/workflows/release.yml`). Pushing a `vX.Y.Z` tag builds the exe on a Windows runner, publishes the GitHub Release with the exe attached, and posts the Discord announcement. Nothing needs to be built locally.

## Pre-Release Checklist

- [ ] All features for the release are complete and merged
- [ ] Application has been tested (download the exe from the PR's **Build** workflow artifacts)
- [ ] Documentation is updated (README.md)
- [ ] docs/CHANGELOG.md has entries for all changes

## Release Steps

### 1. Bump the Version (in a PR)

Update all three together:

- `VERSION.TXT` - the new version (e.g. `1.0.3`)
- `extended-afk.spec` - `name='ExtendedAFK-vX.Y.Z'`
- `docs/CHANGELOG.md` - move the `[Unreleased]` items into a new `## [X.Y.Z] - YYYY-MM-DD` section

Check they agree:
```bash
python scripts/release_tools.py check
```

The PR's **Build** workflow runs the same check and builds the exe.

### 2. Merge the PR to Main

### 3. Review the Release Notes

The release notes are the version's CHANGELOG section plus a downloads footer. Preview them and review them with the user before tagging:
```bash
python scripts/release_tools.py notes X.Y.Z
```

### 4. Tag and Push

```bash
git checkout main
git pull origin main
git tag -a vX.Y.Z -m "Release vX.Y.Z - <Brief Description>"
git push origin vX.Y.Z
```

The **Release** workflow then:
1. Fails if the tag doesn't match `VERSION.TXT`, the spec, and the changelog
2. Builds `dist/ExtendedAFK-vX.Y.Z.exe`
3. Publishes the GitHub Release with the exe attached
4. Posts to Discord with `scripts/discord_notify.py`, after the release is live (needs the `DISCORD_RELEASE_WEBHOOK_URL` repository secret; skipped if it isn't set)

Watch it at https://github.com/Osiris-DevWorks/extended-afk/actions.

**The exe asset must keep the `ExtendedAFK-vX.Y.Z.exe` name.** The in-app updater finds the download by that name; a release without it makes the updater fall back to opening the release page.

### 5. Verify

- [ ] The release is live at https://github.com/Osiris-DevWorks/extended-afk/releases/latest with the exe attached
- [ ] The Discord announcement posted
- [ ] An older version offers the update and restarts into the new one

### 6. Update the Website Tile

Update the Extended AFK entry in `../osiris-devworks-website/src/data/projects.ts`: bump the static `version` fallback and refresh `features`/`status` for what shipped. Pushing the website repo's `main` deploys it.

## Rebuilding a Release

To rebuild an existing tag (for example after a failed run), open **Actions > Release > Run workflow** and enter the tag.

## Manual Discord Post

If the Discord step failed or the secret wasn't set, post it from a machine with `DISCORD_RELEASE_WEBHOOK_URL` in `.env` (see `.env.example`):
```bash
python scripts/discord_notify.py vX.Y.Z https://github.com/Osiris-DevWorks/extended-afk/releases/tag/vX.Y.Z
```

## Building Locally

```bash
python -m PyInstaller extended-afk.spec --clean --noconfirm
```

This produces `dist/ExtendedAFK-vX.Y.Z.exe`. If the build fails, check `build/extended-afk/warn-extended-afk.txt`.

## Version Numbering

This project follows [Semantic Versioning](https://semver.org/):

- **MAJOR** (X.0.0) - Incompatible changes or major feature overhauls
- **MINOR** (0.X.0) - New functionality in a backward-compatible manner
- **PATCH** (0.0.X) - Backward-compatible bug fixes

## Troubleshooting

### Tag Already Exists or Points at the Wrong Commit
```bash
git tag -d vX.Y.Z
git push --delete origin vX.Y.Z
git tag -a vX.Y.Z -m "Release vX.Y.Z - <Description>"
git push origin vX.Y.Z
```

### Version Check Fails
Fix the mismatch on main in a PR, then delete and re-push the tag.
