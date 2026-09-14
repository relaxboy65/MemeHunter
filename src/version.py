"""
version.py
مدیریت نسخه‌بندی معنایی به فرمت V1.2.3
- عدد اول (1): تغییرات بزرگ (Major) - بازنویسی کامل یا تغییرات شکستن رابط
- عدد دوم (2): تغییرات متوسط (Minor) - ویژگی‌های جدید سازگار با قبلی
- عدد سوم (3): رفع خطا (Patch) - باگ‌فیکس و بهبودهای کوچک
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

# مسیر فایل نسخه (در ریشه پروژه)
VERSION_FILE = Path(__file__).resolve().parent.parent / "VERSION"

# فرمت نسخه: V1.2.3 (حروف V الزامی است)
VERSION_PATTERN = re.compile(r"^V(\d+)\.(\d+)\.(\d+)$")


@dataclass(frozen=True)
class Version:
    """نسخه معنایی V1.2.3"""
    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        return f"V{self.major}.{self.minor}.{self.patch}"

    @classmethod
    def parse(cls, text: str) -> "Version":
        text = text.strip()
        m = VERSION_PATTERN.match(text)
        if not m:
            raise ValueError(
                f"نسخه نامعتبر: '{text}'. فرمت صحیح: V1.2.3 (با حرف V بزرگ)"
            )
        return cls(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    def bump(self, kind: str) -> "Version":
        """
        افزایش نسخه بر اساس نوع تغییر.
        kind: 'patch' | 'minor' | 'major'
        """
        if kind == "patch":
            return Version(self.major, self.minor, self.patch + 1)
        if kind == "minor":
            return Version(self.major, self.minor + 1, 0)
        if kind == "major":
            return Version(self.major + 1, 0, 0)
        raise ValueError(f"نوع bump نامعتبر: {kind}. باید patch/minor/major باشد.")


# --------------------------------------------------------------------------- #
# خواندن/نوشتن فایل VERSION
# --------------------------------------------------------------------------- #
def read_version() -> Version:
    """خواندن نسخه فعلی از فایل VERSION. اگر نبود، V0.1.0 برمی‌گرداند."""
    if not VERSION_FILE.exists():
        return Version(0, 1, 0)
    # فقط خطی که با V شروع می‌شود را بخوان (نادیده گرفتن کامنت‌ها)
    for line in VERSION_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return Version.parse(line)
    return Version(0, 1, 0)


def write_version(version: Version) -> None:
    """نوشتن نسخه در فایل VERSION."""
    VERSION_FILE.write_text(f"{version}\n", encoding="utf-8")


def current_version_string() -> str:
    """رشته نسخه فعلی برای نمایش در رابط کاربری."""
    return str(read_version())


# --------------------------------------------------------------------------- #
# توابع کمکی برای کنترل از CLI
# --------------------------------------------------------------------------- #
def bump_and_save(kind: str) -> Version:
    """
    افزایش نسخه و ذخیره در فایل VERSION.
    kind: 'patch' | 'minor' | 'major'
    """
    current = read_version()
    new = current.bump(kind)
    write_version(new)
    return new


def parse_kind(arg: str) -> str:
    """تبدیل آرگومان CLI به نوع bump معتبر."""
    # case-sensitive: 'M' برای major، 'm' برای minor
    if arg in ("patch", "p", "fix", "Patch", "PATCH"):
        return "patch"
    if arg in ("minor", "m", "feature", "Minor", "MINOR"):
        return "minor"
    if arg in ("major", "M", "breaking", "Major", "MAJOR"):
        return "major"
    raise ValueError(
        f"نوع نسخه نامعتبر: {arg}. باید patch/minor/major باشد."
    )
