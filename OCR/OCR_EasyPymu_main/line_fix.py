"""
line_fix.py
Xử lý lỗi xuống dòng chung do layout PDF/OCR.

Module này tách riêng để sau này chỉnh rule gộp dòng mà không đụng OCR engine
hoặc markdown layout.
"""

from __future__ import annotations

import re
from common_fix import clean_line


TITLE_KEYWORDS = [
    "NỘI QUY",
    "QUYẾT ĐỊNH",
    "QUY ĐỊNH",
    "THÔNG BÁO",
    "KẾ HOẠCH",
    "HƯỚNG DẪN",
    "QUY CHẾ",
    "PHỤ LỤC",
    "NỘI DUNG VI PHẠM",
    "TRUNG TÂM PHỤC VỤ SINH VIÊN",
    "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
    "ĐỘC LẬP - TỰ DO - HẠNH PHÚC",
]


def is_page_number_line(line: str) -> bool:
    """Nhận diện dòng chỉ chứa số trang."""

    return bool(re.match(r"^\d+$", clean_line(line)))


def is_heading_line(line: str) -> bool:
    """Nhận diện dòng nên giữ riêng, không gộp vào dòng trước.

    Rule đã được làm chặt hơn bản gốc: không xem mọi dòng bắt đầu bằng
    "Quy định..." là tiêu đề, vì trong thân văn bản có rất nhiều câu dạng này.
    """

    line = clean_line(line)
    upper_line = line.upper()

    if not line:
        return True

    if is_page_number_line(line):
        return True

    if re.match(r"^(Điều|ĐIỀU)\s+\d+", line):
        return True

    if re.match(r"^(Chương|CHƯƠNG)\s+([IVXLCDM]+|\d+)", line):
        return True

    if re.match(r"^(Mục|MỤC)\s+\d+", line):
        return True

    if upper_line.startswith("PHỤ LỤC"):
        return True

    # Chỉ xem keyword lớn là heading khi dòng ngắn/toàn chữ hoa/không kết thúc như câu văn.
    for keyword in TITLE_KEYWORDS:
        if upper_line == keyword:
            return True
        if upper_line.startswith(keyword) and len(line) <= 90 and not line.endswith((".", ",", ";")):
            uppercase_ratio = sum(ch.isupper() for ch in line if ch.isalpha()) / max(1, sum(ch.isalpha() for ch in line))
            if uppercase_ratio >= 0.65:
                return True

    return False


def is_new_item_line(line: str) -> bool:
    """Nhận diện dòng bắt đầu một ý mới: 1., 2), a), -, ..."""

    line = clean_line(line)

    if re.match(r"^\d+[\.)](\s+.*)?$", line):
        return True

    if re.match(r"^[a-zA-ZđĐ][\.)](\s+.*)?$", line):
        return True

    if line.startswith("- "):
        return True

    return False


def is_isolated_list_marker(line: str) -> bool:
    """Nhận diện dòng chỉ có ký hiệu đánh số/bullet đứng riêng."""

    line = clean_line(line)

    if re.match(r"^\d+[\.)]$", line):
        return True

    if re.match(r"^[a-zA-ZđĐ][\.)]$", line):
        return True

    return line in {"-", "•", "-"}


def should_merge_lines(previous_line: str, current_line: str) -> bool:
    """Quyết định có nên gộp current_line vào previous_line không."""

    previous_line = clean_line(previous_line)
    current_line = clean_line(current_line)

    if not previous_line or not current_line:
        return False

    if is_isolated_list_marker(previous_line):
        return True

    if is_heading_line(current_line):
        return False

    if is_new_item_line(current_line):
        return False

    if is_heading_line(previous_line):
        return False

    # Nếu dòng trước kết thúc bằng dấu câu mạnh thì thường là hết đoạn.
    if previous_line.endswith((".", ":", ";", "!", "?")):
        return False

    # Không gộp nếu dòng hiện tại bắt đầu bằng từ báo hiệu một câu/đoạn mới trong văn bản hành chính.
    if re.match(r"^(Căn cứ|Theo đề nghị|QUYẾT ĐỊNH|Điều|Chương|Mục)\b", current_line, flags=re.IGNORECASE):
        return False

    # Còn lại nhiều khả năng là bị ngắt dòng trong PDF/OCR.
    return True


def merge_broken_lines(raw_text: str) -> str:
    """Gộp các dòng bị xuống dòng do layout PDF/OCR."""

    lines = raw_text.splitlines()
    merged_lines: list[str] = []

    for line in lines:
        line = clean_line(line)

        if not line:
            continue

        if is_page_number_line(line):
            continue

        if not merged_lines:
            merged_lines.append(line)
            continue

        previous_line = merged_lines[-1]

        if should_merge_lines(previous_line, line):
            if previous_line.endswith("-"):
                merged_lines[-1] = previous_line + line
            else:
                merged_lines[-1] = previous_line + " " + line
        else:
            merged_lines.append(line)

    return "\n".join(merged_lines)
