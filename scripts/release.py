#!/usr/bin/env python3
"""
release.py
اسکریپت مدیریت نسخه‌بندی و انتشار پروژه MemeHunter.

قوانین نسخه‌بندی (Semantic Versioning V1.2.3):
  - عدد اول (Major): تغییرات خیلی بزرگ (بازنویسی، تغییرات شکستن رابط)
  - عدد دوم (Minor): تغییرات متوسط (ویژگی‌های جدید سازگار)
  - عدد سوم (Patch): رفع خطا و بهبودهای کوچک

استفاده:
    python scripts/release.py patch          # V1.0.0 -> V1.0.1
    python scripts/release.py minor          # V1.0.0 -> V1.1.0
    python scripts/release.py major          # V1.0.0 -> V2.0.0
    python scripts/release.py current        # نمایش نسخه فعلی
    python scripts/release.py list           # لیست نسخه‌های موجود
    python scripts/release.py cleanup        # حذف نسخه‌های قدیمی (نگهداری 3 نسخه)

مراحل اجرا در حالت patch/minor/major:
    1. افزایش نسخه در فایل VERSION
    2. به‌روزرسانی README.md و فایل workflow با نسخه جدید
    3. ثبت در CHANGELOG.md
    4. ساخت فایل زیپ در releases/MemeHunter-V1.2.3.zip
    5. اجرای cleanup: نگهداری حداکثر 3 نسخه اخیر
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.version import Version, read_version, write_version, parse_kind
from src.config import PROJECT_NAME, PROJECT_SLUG


# --------------------------------------------------------------------------- #
# ثابت‌ها
# --------------------------------------------------------------------------- #
RELEASES_DIR = PROJECT_ROOT / "releases"
CHANGELOG_FILE = PROJECT_ROOT / "CHANGELOG.md"
README_FILE = PROJECT_ROOT / "README.md"
WORKFLOW_FILE = PROJECT_ROOT / ".github" / "workflows" / "daily-scan.yml"
VERSION_FILE = PROJECT_ROOT / "VERSION"

MAX_RELEASES = 3

EXCLUDE_DIRS = {
    "__pycache__", ".git", ".pytest_cache", "releases",
    "venv", "env", ".venv", ".env", ".idea", ".vscode",
    "data",      # پوشه دیتا شامل لاگ و دیتابیس است، در زیپ قرار نمی‌گیرد
    "reports",   # خروجی موقت گزارش‌ها در زیپ قرار نمی‌گیرد
}
EXCLUDE_FILE_EXTS = {".pyc", ".pyo", ".log"}


# --------------------------------------------------------------------------- #
# توابع کمکی
# --------------------------------------------------------------------------- #
def run(cmd: List[str], cwd: Path = PROJECT_ROOT, check: bool = True) -> Tuple[int, str]:
    result = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"خطا در اجرای دستور: {' '.join(cmd)}")
        print(result.stderr)
        sys.exit(1)
    return result.returncode, result.stdout.strip()


def update_readme_version(new_version: Version) -> bool:
    """به‌روزرسانی نسخه در README.md."""
    if not README_FILE.exists():
        return False
    content = README_FILE.read_text(encoding="utf-8")
    pattern = re.compile(r"V\d+\.\d+\.\d+")
    new_content, count = pattern.subn(str(new_version), content)
    if count > 0:
        README_FILE.write_text(new_content, encoding="utf-8")
        print(f"  README.md: {count} مورد نسخه جایگزین شد")
        return True
    return False


def update_workflow_version(new_version: Version) -> bool:
    """به‌روزرسانی نسخه در فایل workflow."""
    if not WORKFLOW_FILE.exists():
        return False
    content = WORKFLOW_FILE.read_text(encoding="utf-8")
    pattern = re.compile(r"V\d+\.\d+\.\d+")
    new_content, count = pattern.subn(str(new_version), content)
    if count > 0:
        WORKFLOW_FILE.write_text(new_content, encoding="utf-8")
        print(f"  workflow YAML: {count} مورد نسخه جایگزین شد")
        return True
    return False


def update_changelog(new_version: Version, kind: str) -> None:
    """افزودن رکورد به CHANGELOG.md."""
    today = datetime.now().strftime("%Y-%m-%d")
    kind_label = {
        "patch": "Patch (رفع خطا)",
        "minor": "Minor (ویژگی جدید)",
        "major": "Major (تغییر بزرگ)",
    }[kind]

    entry = f"""## {new_version} - {today} - {kind_label}

- نسخه جدید انتشار یافت.
- به‌روزرسانی README.md و GitHub Actions workflow.
- ساخت فایل زیپ در releases/MemeHunter-{new_version}.zip

"""
    if CHANGELOG_FILE.exists():
        content = CHANGELOG_FILE.read_text(encoding="utf-8")
        if content.startswith("# "):
            lines = content.split("\n", 2)
            new_content = lines[0] + "\n\n" + entry + (lines[2] if len(lines) > 2 else "")
        else:
            new_content = entry + content
        CHANGELOG_FILE.write_text(new_content, encoding="utf-8")
    else:
        CHANGELOG_FILE.write_text(f"# تغییرات نسخه‌های {PROJECT_NAME}\n\n" + entry, encoding="utf-8")
    print(f"  CHANGELOG.md: ورودی {new_version} اضافه شد")


def should_exclude_dir(name: str) -> bool:
    return name in EXCLUDE_DIRS


def should_exclude_file(name: str) -> bool:
    ext = Path(name).suffix.lower()
    return ext in EXCLUDE_FILE_EXTS


def create_zip(new_version: Version) -> Path:
    """ساخت فایل زیپ از کل پروژه."""
    RELEASES_DIR.mkdir(parents=True, exist_ok=True)
    zip_name = f"MemeHunter-{new_version}.zip"
    zip_path = RELEASES_DIR / zip_name

    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(PROJECT_ROOT):
            root_path = Path(root)
            dirs[:] = [d for d in dirs if not should_exclude_dir(d)]
            for file in files:
                if should_exclude_file(file):
                    continue
                file_path = root_path / file
                arcname = Path(PROJECT_SLUG) / file_path.relative_to(PROJECT_ROOT)
                zf.write(file_path, arcname=str(arcname))

    size_kb = zip_path.stat().st_size / 1024
    print(f"  ZIP ساخته شد: {zip_path.name} ({size_kb:.1f} KB)")
    return zip_path


def cleanup_releases() -> int:
    """حذف نسخه‌های قدیمی، نگهداری حداکثر MAX_RELEASES نسخه اخیر."""
    if not RELEASES_DIR.exists():
        return 0

    zips = sorted(
        RELEASES_DIR.glob("MemeHunter-V*.zip"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if len(zips) <= MAX_RELEASES:
        return 0

    to_delete = zips[MAX_RELEASES:]
    deleted = 0
    for f in to_delete:
        try:
            f.unlink()
            deleted += 1
            print(f"  حذف نسخه قدیمی: {f.name}")
        except OSError as exc:
            print(f"  خطا در حذف {f.name}: {exc}")
    return deleted


def list_releases() -> None:
    """نمایش لیست نسخه‌های موجود در releases/."""
    if not RELEASES_DIR.exists():
        print("هیچ نسخه‌ای منتشر نشده است.")
        return
    zips = sorted(
        RELEASES_DIR.glob("MemeHunter-V*.zip"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not zips:
        print("هیچ نسخه‌ای منتشر نشده است.")
        return
    print(f"نسخه‌های موجود در {RELEASES_DIR.name}/ (حداکثر {MAX_RELEASES} نگهداری می‌شود):")
    print("-" * 60)
    for i, z in enumerate(zips, 1):
        marker = " <- جدیدترین" if i == 1 else ""
        size_kb = z.stat().st_size / 1024
        print(f"  {i}. {z.name}  [{size_kb:.1f} KB]{marker}")
    print("-" * 60)


# --------------------------------------------------------------------------- #
# دستورات CLI
# --------------------------------------------------------------------------- #
def cmd_bump(kind: str) -> int:
    """افزایش نسخه و ساخت فایل زیپ."""
    current = read_version()
    new_version = current.bump(kind)

    print()
    print("=" * 60)
    print(f"  {PROJECT_NAME} - انتشار نسخه جدید")
    print(f"  {current}  ->  {new_version}  ({kind})")
    print("=" * 60)
    print()

    # مرحله 1: به‌روزرسانی فایل VERSION
    write_version(new_version)
    print(f"  VERSION: {new_version} ذخیره شد")

    # مرحله 2: به‌روزرسانی README و workflow
    update_readme_version(new_version)
    update_workflow_version(new_version)

    # مرحله 3: ثبت در CHANGELOG
    update_changelog(new_version, kind)

    # مرحله 4: ساخت زیپ
    print()
    print("ساخت فایل زیپ...")
    zip_path = create_zip(new_version)

    # مرحله 5: cleanup نسخه‌های قدیمی
    print()
    print(f"بررسی نگهداری حداکثر {MAX_RELEASES} نسخه...")
    deleted = cleanup_releases()
    if deleted > 0:
        print(f"  {deleted} نسخه قدیمی حذف شد")
    else:
        print("  همه نسخه‌ها در محدوده مجاز هستند")

    print()
    print("=" * 60)
    print(f"  انتشار {new_version} با موفقیت انجام شد!")
    print(f"  فایل زیپ: {zip_path}")
    print("=" * 60)
    return 0


def cmd_current() -> int:
    v = read_version()
    print(f"{PROJECT_NAME} نسخه فعلی: {v}")
    return 0


def cmd_list() -> int:
    list_releases()
    return 0


def cmd_cleanup() -> int:
    print(f"پاکسازی نسخه‌های قدیمی (نگهداری {MAX_RELEASES} نسخه اخیر)...")
    deleted = cleanup_releases()
    if deleted > 0:
        print(f"  {deleted} نسخه قدیمی حذف شد")
    else:
        print("  همه نسخه‌ها در محدوده مجاز هستند")
    list_releases()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="release.py",
        description=f"مدیریت نسخه‌بندی پروژه {PROJECT_NAME}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("patch", help="افزایش نسخه رفع خطا (V1.0.0 -> V1.0.1)")
    sub.add_parser("minor", help="افزایش نسخه ویژگی جدید (V1.0.0 -> V1.1.0)")
    sub.add_parser("major", help="افزایش نسخه بزرگ (V1.0.0 -> V2.0.0)")
    sub.add_parser("current", help="نمایش نسخه فعلی")
    sub.add_parser("list", help="لیست نسخه‌های منتشر شده")
    sub.add_parser("cleanup", help="حذف نسخه‌های قدیمی (نگهداری 3 نسخه)")

    args = parser.parse_args()
    cmd = args.command

    if cmd in ("patch", "minor", "major"):
        return cmd_bump(cmd)
    if cmd == "current":
        return cmd_current()
    if cmd == "list":
        return cmd_list()
    if cmd == "cleanup":
        return cmd_cleanup()

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
