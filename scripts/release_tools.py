"""
Release helpers used by the GitHub Actions workflows (and handy locally).

Usage:
    python scripts/release_tools.py check [vX.Y.Z]
        Fail unless VERSION.TXT, the exe name in extended-afk.spec and a
        docs/CHANGELOG.md section all agree (and match the tag, if given).

    python scripts/release_tools.py notes X.Y.Z
        Print that version's CHANGELOG.md section as release notes.
"""

import re
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent


def read_version():
    return (project_root / "VERSION.TXT").read_text(encoding="utf-8").strip()


def changelog_section(version):
    """Return the body of '## [version]' in the changelog, or None."""
    text = (project_root / "docs" / "CHANGELOG.md").read_text(encoding="utf-8")
    match = re.search(
        rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    return match.group(1).strip() if match else None


def check(tag=None):
    version = read_version()
    errors = []

    spec = (project_root / "extended-afk.spec").read_text(encoding="utf-8")
    spec_match = re.search(r"name='ExtendedAFK-v([^']+)'", spec)
    if not spec_match:
        errors.append("extended-afk.spec has no name='ExtendedAFK-vX.Y.Z'")
    elif spec_match.group(1) != version:
        errors.append(f"extended-afk.spec builds v{spec_match.group(1)} but VERSION.TXT is {version}")

    if not changelog_section(version):
        errors.append(f"docs/CHANGELOG.md has no '## [{version}]' section")

    if tag and tag.lstrip("v") != version:
        errors.append(f"Tag {tag} does not match VERSION.TXT ({version})")

    if errors:
        for e in errors:
            print(f"[ERROR] {e}")
        sys.exit(1)
    print(f"[OK] Version {version} is consistent")


def notes(version):
    section = changelog_section(version.lstrip("v"))
    if not section:
        print(f"[ERROR] No changelog section for {version}", file=sys.stderr)
        sys.exit(1)
    print(section)
    print()
    print("## Downloads")
    print()
    print(f"- **ExtendedAFK-v{version.lstrip('v')}.exe**: portable, no installation required. "
          "Extended AFK v1.0.3 and later update themselves from inside the app.")
    print()
    print("See [CHANGELOG.md](https://github.com/Osiris-DevWorks/extended-afk/blob/main/docs/CHANGELOG.md) "
          "for the full history. Need help? Join our [Discord](https://discord.gg/BNzRegKZ7k).")


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "check":
        check(sys.argv[2] if len(sys.argv) > 2 else None)
    elif len(sys.argv) == 3 and sys.argv[1] == "notes":
        notes(sys.argv[2])
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
