# Release Process

**Version:** 1.0
**Date:** 2024-12-17
**For:** Release managers - Creating and publishing new versions

This document outlines the standard process for creating a new release of Extended AFK.

## Pre-Release Checklist

- [ ] All features for the release are complete and merged
- [ ] Application has been tested
- [ ] Documentation is updated (README.md)
- [ ] docs/CHANGELOG.md has entries for all changes

## Release Steps

### 1. Prepare Release Branch

If working on a feature branch:
```bash
# Ensure branch is up to date
git checkout <feature-branch>
git pull origin <feature-branch>
```

### 2. Update Version Files

Update the following files with the new version number:

- `VERSION.TXT` - Update to new version (e.g., `1.0.2`)
- `docs/CHANGELOG.md` - Move unreleased items to new version section with date

### 3. Clean Up Repository

- Remove temporary/scratch files and directories
- Update `.gitignore` if needed
- Stage documentation and utility files for commit

### 4. Build the Executable

```bash
python -m PyInstaller extended-afk.spec --clean --noconfirm
```

Verify the build:
```bash
# Check that dist/ExtendedAFK.exe exists
ls dist/ExtendedAFK.exe
```

### 5. Create Release Commit

On the feature branch, commit all version updates:
```bash
git add VERSION.TXT docs/CHANGELOG.md [other-files]
git commit -m "Release vX.Y.Z - <Brief Description>"
```

### 6. Merge to Main

**Option A: Pull Request (Recommended)**
```bash
git push origin <feature-branch>
# Create PR on GitHub to merge into main
# After PR is approved and merged, proceed to step 7
```

**Option B: Direct Merge**
```bash
git checkout main
git merge <feature-branch>
git push origin main
```

### 7. Create Version Commit on Main

After merging, ensure version files are correct on main:
```bash
git checkout main
git pull origin main

# Verify VERSION.TXT and docs/CHANGELOG.md are at correct version
# If not, update them and commit:
git add VERSION.TXT docs/CHANGELOG.md
git commit -m "Update version to X.Y.Z"
git push origin main
```

### 8. Create Git Tag

```bash
git tag -a vX.Y.Z -m "Release vX.Y.Z - <Brief Description>"
git push origin vX.Y.Z
```

### 9. Create GitHub Release

**⚠️ IMPORTANT:** You must COMPLETE this step (including publishing the release) BEFORE running the Discord notification in step 10. The Discord notification includes a link to the release, which must exist for users.

1. **Go to GitHub Release Page:**
   ```
   https://github.com/Osiris-RK/extended-afk/releases/new?tag=vX.Y.Z
   ```

2. **Fill in Release Information:**
   - **Tag:** vX.Y.Z (should be auto-selected)
   - **Release Title:** `Extended AFK vX.Y.Z - <Brief Description>`
   - **Description:** Use the docs/CHANGELOG.md content for this version (see template below)

3. **Attach Build Artifacts:**
   - Upload `dist/ExtendedAFK.exe` (standalone executable)

4. **Publish Release**
   - Look at previous release notes to make sure you're including sections included before
   - Before officially publishing the release, review the release notes with the user
   - Ask the user what the testing focus should be for the release
   - Publish the release when user gives approval

5. **Verify Release is Live:**
   - Visit the release URL to confirm it's accessible
   - Verify download links work
   - Only proceed to step 10 after confirmation

### 10. Post Release to Discord

**⚠️ PREREQUISITE:** The GitHub release from step 9 MUST be published and live before running this step.

**Prerequisites:**
- Set up Discord webhook URL in `.env` file (copy from `.env.example`)
- Create webhook: Discord Server → Server Settings → Integrations → Webhooks → New Webhook

**Post the release:**
```bash
python scripts/discord_notify.py vX.Y.Z https://github.com/Osiris-RK/extended-afk/releases/tag/vX.Y.Z
```

Example:
```bash
python scripts/discord_notify.py v1.0.2 https://github.com/Osiris-RK/extended-afk/releases/tag/v1.0.2
```

The script will:
- Parse docs/CHANGELOG.md for the version's changes
- Create a formatted Discord embed with release info
- Post to the configured Discord channel
- Skip gracefully if webhook URL is not configured

## GitHub Release Notes Template

```markdown
# Extended AFK vX.Y.Z - <Brief Description>

[1-2 sentence summary of the release]

## 🆕 What's New

### Added
- Feature 1
- Feature 2

### Changed
- Change 1
- Change 2

### Fixed
- Fix 1
- Fix 2

## 📥 Downloads

- **Standalone:** [ExtendedAFK.exe](link) - Portable version (no installation required)

## 📋 System Requirements

- Windows 10 or later (64-bit)
- No additional dependencies required

## 🐛 Known Issues

[List any known issues, limitations, or workarounds]

## 🧪 Testing Focus

[Areas the community should focus testing on for this release]

## 📝 Full Changelog

See [CHANGELOG.md](https://github.com/Osiris-RK/extended-afk/blob/main/docs/CHANGELOG.md) for complete version history.

---

**First time using Extended AFK?** Check out the [README](https://github.com/Osiris-RK/extended-afk/blob/main/README.md) to get started!

**Need help?** Join our [Discord community](https://discord.gg/BNzRegKZ7k) for support and discussions.

**Support this project:** [PayPal](https://www.paypal.com/ncp/payment/YAWXHMGZH8T76) | [Venmo](https://venmo.com/u/Amr-Abouelleil)
```

## Version Numbering

This project follows [Semantic Versioning](https://semver.org/):

- **MAJOR** (X.0.0) - Incompatible API changes or major feature overhauls
- **MINOR** (0.X.0) - New functionality in a backward-compatible manner
- **PATCH** (0.0.X) - Backward-compatible bug fixes

## Post-Release

- [ ] Verify GitHub release is published
- [ ] Test executable download
- [ ] **Post to Discord** (see step 10 - this is REQUIRED, not optional):
  ```bash
  python scripts/discord_notify.py vX.Y.Z https://github.com/Osiris-RK/extended-afk/releases/tag/vX.Y.Z
  ```
- [ ] Create new development branch for next version (if needed)
- [ ] Update docs/CHANGELOG.md with new `[Unreleased]` section

## Troubleshooting

### Tag Already Exists
```bash
# Delete local tag
git tag -d vX.Y.Z

# Delete remote tag
git push --delete origin vX.Y.Z

# Recreate tag
git tag -a vX.Y.Z -m "Release vX.Y.Z - <Description>"
git push origin vX.Y.Z
```

### Version Mismatch
If version files don't match after merge, update them on main and create a new commit before tagging.

### Build Fails
Check `build/extended-afk/warn-extended-afk.txt` for warnings and errors.
