#!/usr/bin/env python3
"""
enforce_law.py
اعمال قانون طلایی پروژه MemeHunter - V2.0.0

📜 قانون طلایی:
   همیشه فقط فایل زیپ 3 نسخه نهایی را نگه دار و هیچ چیز دیگری را نگه ندار.

این اسکریپت:
1. تمام فایل‌های خارج از پوشه releases/ را حذف می‌کند
2. فقط 3 نسخه ZIP اخیر را نگه می‌دارد
3. نسخه‌های قدیمی‌تر را خودکار حذف می‌کند

اجرا:
    python scripts/enforce_law.py              # اعمال قانون
    python scripts/enforce_law.py --dry-run    # فقط نمایش، بدون حذف
    python scripts/enforce_law.py --check      # فقط بررسی وضعیت
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


# قانون طلایی پروژه
GOLDEN_RULE = """
📜 قانون طلایی MemeHunter:
   همیشه فقط فایل زیپ 3 نسخه نهایی را نگه دار و هیچ چیز دیگری را نگه ندار.
"""

# حداکثر تعداد نسخه‌های ZIP قابل نگهداری
MAX_VERSIONS = 3

# فایل‌های مجاز در ریشه پروژه (داخل زیپ)
ALLOWED_ROOT_FILES = {
    "main.py", "VERSION", "CHANGELOG.md", "RELEASE_RULES.md",
    "requirements.txt", "README.md", "LICENSE", ".env.example",
    ".gitignore",
}

# پوشه‌های مجاز در ریشه
ALLOWED_ROOT_DIRS = {
    "src", "tests", "scripts", "data", "reports",
    "releases", ".github",
}


def find_project_root() -> Path:
    """پیدا کردن ریشه پروژه (محل فایل VERSION)."""
    current = Path(__file__).resolve().parent.parent
    if (current / "VERSION").exists():
        return current
    return Path.cwd()


def list_zips(releases_dir: Path) -> list:
    """لیست فایل‌های ZIP مرتب بر اساس زمان تغییر (جدیدترین اول)."""
    if not releases_dir.exists():
        return []
    zips = sorted(
        releases_dir.glob("*.zip"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return zips


def enforce_max_versions(releases_dir: Path, max_versions: int = MAX_VERSIONS,
                          dry_run: bool = False) -> list:
    """حذف نسخه‌های قدیمی‌تر از max_versions."""
    zips = list_zips(releases_dir)
    if len(zips) <= max_versions:
        return []

    to_delete = zips[max_versions:]
    deleted = []
    for f in to_delete:
        if dry_run:
            print(f"  [DRY-RUN] خواهد حذف شد: {f.name}")
        else:
            try:
                f.unlink()
                print(f"  ✓ حذف شد: {f.name}")
                deleted.append(f.name)
            except OSError as exc:
                print(f"  ✗ خطا در حذف {f.name}: {exc}")
    return deleted


def check_outside_releases(project_root: Path, dry_run: bool = False) -> list:
    """بررسی ZIPهای خارج از releases/."""
    issues = []
    releases_dir = project_root / "releases"

    for item in project_root.rglob("*.zip"):
        try:
            if not item.is_relative_to(releases_dir):
                issues.append(item)
                if dry_run:
                    print(f"  [DRY-RUN] ZIP خارج از releases/: {item}")
                else:
                    try:
                        item.unlink()
                        print(f"  ✓ حذف شد: {item}")
                    except OSError:
                        pass
        except (OSError, ValueError):
            continue

    return issues


def enforce_law(project_root: Path, dry_run: bool = False) -> dict:
    """اعمال قانون طلایی."""
    print(GOLDEN_RULE)
    print("=" * 60)
    print(f"  اعمال قانون طلایی در: {project_root}")
    print("=" * 60)
    print()

    releases_dir = project_root / "releases"
    releases_dir.mkdir(parents=True, exist_ok=True)

    # مرحله 1: حذف ZIPهای خارج از releases/
    print("📋 مرحله 1: بررسی ZIPهای خارج از releases/")
    outside_zips = check_outside_releases(project_root, dry_run)
    print(f"  تعداد: {len(outside_zips)}")
    print()

    # مرحله 2: فقط 3 نسخه ZIP نگه دار
    print(f"📋 مرحله 2: نگهداری حداکثر {MAX_VERSIONS} نسخه ZIP")
    deleted_versions = enforce_max_versions(releases_dir, MAX_VERSIONS, dry_run)
    print(f"  حذف شده: {len(deleted_versions)}")
    print()

    # خلاصه نهایی
    zips_remaining = list_zips(releases_dir)
    print("=" * 60)
    print("  📊 خلاصه:")
    print(f"  ZIPهای باقیمانده: {len(zips_remaining)}")
    for i, z in enumerate(zips_remaining, 1):
        size_kb = z.stat().st_size / 1024
        marker = " ← جدیدترین" if i == 1 else ""
        print(f"    {i}. {z.name} ({size_kb:.0f} KB){marker}")
    print("=" * 60)

    return {
        "outside_zips_deleted": len(outside_zips),
        "old_versions_deleted": len(deleted_versions),
        "zips_remaining": len(zips_remaining),
        "remaining_zips": [z.name for z in zips_remaining],
    }


def check_status(project_root: Path) -> bool:
    """بررسی وضعیت - آیا قانون رعایت می‌شود؟"""
    releases_dir = project_root / "releases"
    zips = list_zips(releases_dir)

    issues = []

    if len(zips) > MAX_VERSIONS:
        issues.append(f"تعداد ZIPها {len(zips)} > {MAX_VERSIONS}")

    outside = []
    for p in project_root.rglob("*.zip"):
        try:
            if not p.is_relative_to(releases_dir):
                outside.append(p)
        except (OSError, ValueError):
            continue
    if outside:
        issues.append(f"{len(outside)} ZIP خارج از releases/")

    if issues:
        print(f"❌ قانون نقض شده:")
        for i in issues:
            print(f"  • {i}")
        return False
    else:
        print(f"✅ قانون رعایت می‌شود")
        print(f"  ZIPهای موجود: {len(zips)}")
        for z in zips:
            print(f"    • {z.name}")
        return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="اعمال قانون طلایی MemeHunter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=GOLDEN_RULE,
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="فقط نمایش، بدون حذف واقعی",
    )
    parser.add_argument(
        "--check", "-c",
        action="store_true",
        help="فقط بررسی وضعیت",
    )
    args = parser.parse_args()

    project_root = find_project_root()

    if args.check:
        ok = check_status(project_root)
        return 0 if ok else 1

    enforce_law(project_root, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
