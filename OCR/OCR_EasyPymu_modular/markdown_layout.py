"""
markdown_layout.py
Nhận diện layout văn bản và chuyển sang Markdown.
"""

from __future__ import annotations

import re
from common_fix import clean_line, apply_common_fixes
from ctu_terms import apply_ctu_term_fixes
from rare_fix import apply_rare_fixes
from line_fix import merge_broken_lines


MAJOR_TITLES = [
    "QUYẾT ĐỊNH",
    "QUY ĐỊNH",
    "THÔNG BÁO",
    "KẾ HOẠCH",
    "HƯỚNG DẪN",
    "QUY CHẾ",
    "HIỆU TRƯỞNG",
    "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
    "ĐỘC LẬP - TỰ DO - HẠNH PHÚC",
]


def _looks_like_major_title(line: str) -> bool:
    """Kiểm tra tiêu đề lớn nhưng tránh lỗi biến câu thường thành heading."""

    upper_line = line.upper()

    for title in MAJOR_TITLES:
        if upper_line == title:
            return True
        if upper_line.startswith(title) and len(line) <= 90 and not line.endswith((".", ",", ";")):
            letters = [ch for ch in line if ch.isalpha()]
            uppercase_ratio = sum(ch.isupper() for ch in letters) / max(1, len(letters))
            if uppercase_ratio >= 0.65:
                return True

    return False


def format_line_to_markdown(line: str) -> str:
    """Định dạng một dòng thành Markdown heading/list/emphasis nếu phù hợp."""

    line = clean_line(line)

    if not line:
        return ""

    if _looks_like_major_title(line):
        return f"# {line}"

    if re.match(r"^(CHƯƠNG|Chương)\s+([IVXLCDM]+|\d+)", line):
        return f"## {line}"

    if re.match(r"^(MỤC|Mục)\s+\d+", line):
        return f"### {line}"

    if re.match(r"^(ĐIỀU|Điều)\s+\d+", line):
        return f"### {line}"

    if line.startswith("Số:") or line.startswith("Số "):
        return f"**{line}**"

    if line.startswith("Căn cứ"):
        return f"**{line}**"

    if line.startswith("Theo đề nghị"):
        return f"*{line}*"

    if re.match(r"^[a-zA-ZđĐ]\)\s+", line):
        return f"- {line}"

    if line.startswith("- "):
        return line

    if line.isupper() and len(line) <= 80:
        return f"# {line}"

    return line


def apply_all_text_fixes(text: str) -> str:
    """Chạy toàn bộ các lớp sửa lỗi chung -> thuật ngữ CTU -> lỗi hiếm."""

    text = apply_common_fixes(text)
    text = apply_ctu_term_fixes(text)
    text = apply_rare_fixes(text)
    text = apply_common_fixes(text)
    return text


def format_text_to_markdown(text: str) -> str:
    """Gộp dòng bị ngắt, sửa lỗi chung và nhận diện heading/list."""

    text = apply_all_text_fixes(text)
    text = merge_broken_lines(text)
    text = apply_all_text_fixes(text)

    formatted_lines: list[str] = []

    for line in text.splitlines():
        line = clean_line(line)

        if not line:
            continue

        formatted_lines.append(format_line_to_markdown(line))

    return "\n\n".join(formatted_lines)
