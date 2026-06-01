"""
common_fix.py
Các lỗi chung thường gặp sau khi extract/OCR, dùng cho mọi loại tài liệu.

Nhóm này KHÔNG phụ thuộc vào một file PDF cụ thể, chỉ xử lý các lỗi phổ biến:
- ký tự null, khoảng trắng dư, xuống dòng dư;
- bullet/ký tự gạch đầu dòng lạ;
- dấu câu bị tách khoảng trắng;
- lỗi dấu gạch ngang và dấu ngoặc thường gặp trong văn bản hành chính.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any


COMMON_REPLACEMENTS: dict[str, str] = {
    "\uf0b7": "- ",
    "": "- ",
    "•": "- ",
    "–": "-",
    "—": "-",
    "−": "-",
    "“": '"',
    "”": '"',
    "‘": "'",
    "’": "'",
    "…": "...",
}


COMMON_REGEX_REPLACEMENTS: list[tuple[str, str]] = [
    # Bỏ khoảng trắng trước dấu câu.
    (r"\s+([,.;:!?])", r"\1"),
    # Thêm đúng 1 khoảng trắng sau dấu câu nếu phía sau là chữ/số.
    (r"([,.;:!?])(?=[^\s\n])", r"\1 "),
    # Chuẩn hóa khoảng trắng quanh dấu gạch nối trong số hiệu, ví dụ QĐ - ĐHCT -> QĐ-ĐHCT.
    (r"\b([A-ZĐ]{1,6})\s*-\s*([A-ZĐ]{1,10})\b", r"\1-\2"),
    # Chuẩn hóa dấu / trong cụm số hiệu.
    (r"\s*/\s*", "/"),
    # Không để khoảng trắng ngay sau mở ngoặc hoặc trước đóng ngoặc.
    (r"\(\s+", "("),
    (r"\s+\)", ")"),
    # Gộp nhiều khoảng trắng thành một.
    (r"[ \t]+", " "),
]


def clean_text(text: Any) -> str:
    """Làm sạch text nhiều dòng: bỏ null, chuẩn hóa Unicode, khoảng trắng và xuống dòng."""

    if text is None:
        return ""

    text = unicodedata.normalize("NFC", str(text))
    text = text.replace("\x00", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    for old, new in COMMON_REPLACEMENTS.items():
        text = text.replace(old, new)

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_line(line: Any) -> str:
    """Làm sạch một dòng: strip, chuẩn hóa ký tự và gộp khoảng trắng."""

    if line is None:
        return ""

    line = unicodedata.normalize("NFC", str(line)).strip()

    for old, new in COMMON_REPLACEMENTS.items():
        line = line.replace(old, new)

    line = re.sub(r"\s+", " ", line)
    return line.strip()


def apply_common_fixes(text: str) -> str:
    """Áp dụng các rule sửa lỗi chung không phụ thuộc domain CTU."""

    text = clean_text(text)

    for pattern, replacement in COMMON_REGEX_REPLACEMENTS:
        text = re.sub(pattern, replacement, text)

    # Sau các regex có thể sinh khoảng trắng dư.
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
