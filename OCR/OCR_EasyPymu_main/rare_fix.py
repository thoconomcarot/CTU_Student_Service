"""
rare_fix.py
Các lỗi ít gặp hoặc khó tổng quát hóa.

Chỉ thêm rule ở đây khi lỗi đó xuất hiện lặp lại nhiều lần ở nhiều tài liệu,
nhưng không đủ phổ biến để đưa vào common_fix.py hoặc ctu_terms.py.
"""

from __future__ import annotations

import re

RARE_FIX_RULES: list[tuple[str, str]] = [
    # Một số OCR nhầm ký tự trong cụm văn bản hành chính.
    (r"\bC0NG\s+H[OÒ]A\b", "CỘNG HÒA"),
    (r"\bXA\s+H[OỘ]I\b", "XÃ HỘI"),
    (r"\bH[OỌ]ANH\s+PH[UÚ]C\b", "HẠNH PHÚC"),
    # Lỗi hay gặp khi OCR số hiệu quyết định/quy định.
    (r"\bQÐ\b", "QĐ"),
    (r"\bQD\b(?=\s*[-/])", "QĐ"),
]


def apply_rare_fixes(text: str) -> str:
    """Áp dụng nhóm lỗi ít gặp, có thể mở rộng dần nhưng không phụ thuộc từng file."""

    if not text:
        return ""

    for pattern, replacement in RARE_FIX_RULES:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    return text
