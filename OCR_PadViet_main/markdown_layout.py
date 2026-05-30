"""
bo_cuc_markdown.py
Xử lý bố cục sau OCR và xuất Markdown.

Chức năng:
- Gộp dòng bị xuống dòng sai nhẹ.
- Nhận diện heading Chương/Điều/Mục/Phần/Quyết định/Quy định.
- Khôi phục bullet list thường gặp trong văn bản quy định, quyết định, công văn, biểu mẫu.
- Không phóng to tùy tiện dòng có chữ `Quy định` nếu nó nằm trong câu bình thường.
"""

from __future__ import annotations

import re
from config import CauHinhOCR, CAU_HINH_MAC_DINH, chuan_hoa_de_so_khop, lam_sach_dong, lam_sach_text


def la_heading_dieu(line: str) -> bool:
    """Nhận diện dòng bắt đầu bằng `Điều x.`."""

    line = lam_sach_dong(line)
    return bool(re.match(r"^(Điều|ĐIỀU|Dieu|DIEU)\s+\d+[\.:]?\s*", line))


def la_heading_chuong(line: str) -> bool:
    """Nhận diện dòng bắt đầu bằng `Chương I/1` hoặc `CHƯƠNG I`."""

    line = lam_sach_dong(line)
    return bool(re.match(r"^(Chương|CHƯƠNG|Chuong|CHUONG)\s+([IVXLCDM]+|\d+)", line))


def la_heading_muc(line: str) -> bool:
    """Nhận diện dòng bắt đầu bằng `Mục x` hoặc `MỤC x`."""

    line = lam_sach_dong(line)
    return bool(re.match(r"^(Mục|MỤC|Muc|MUC)\s+\d+", line))


def la_tieu_de_doc_lap(line: str) -> bool:
    """Nhận diện tiêu đề lớn độc lập như QUYẾT ĐỊNH, QUY ĐỊNH, THÔNG BÁO.

    Không dùng startswith để tránh lỗi phóng to dòng văn bản thường có chữ `quy định`.
    """

    key = chuan_hoa_de_so_khop(line)
    exact_titles = {
        "quyet dinh",
        "quy dinh",
        "thong bao",
        "cong van",
        "ke hoach",
        "huong dan",
        "quy che",
        "noi quy",
        "phu luc",
        "bieu mau",
    }
    return key in exact_titles


def la_dong_co_cau_truc(line: str) -> bool:
    """Kiểm tra dòng có phải marker cấu trúc cần giữ riêng hay không."""

    line = lam_sach_dong(line)
    if not line:
        return True
    if line.startswith("<!--") or line.startswith("#"):
        return True
    if line.startswith(("Kính gửi:", "Nơi nhận:", "KT.", "TM.", "TL.", "- ", "+ ", "• ")):
        return True
    if la_heading_dieu(line) or la_heading_chuong(line) or la_heading_muc(line) or la_tieu_de_doc_lap(line):
        return True
    return False


def dong_ket_thuc_mem(line: str) -> bool:
    """Dòng có vẻ chưa kết thúc câu, nên gộp với dòng sau nếu an toàn."""

    line = lam_sach_dong(line)
    if not line:
        return False
    if line.endswith((",", ";", ":", "-", "–")):
        return True
    last_words = (
        "và", "hoặc", "của", "theo", "gồm", "bao gồm", "để", "với", "từ", "đến",
        "trong", "ngoài", "khi", "nếu", "do", "bởi", "về", "cho", "tại", "chương",
        "ban", "quý", "các", "những", "đề nghị", "trân trọng", "nhà trường",
    )
    lower = line.lower()
    return any(lower.endswith(" " + word) or lower == word for word in last_words)


def bat_dau_bang_chu_thuong_hoac_tiep_noi(line: str) -> bool:
    """Dòng bắt đầu bằng chữ thường hoặc từ nối, thường là phần tiếp của dòng trước."""

    line = lam_sach_dong(line)
    if not line:
        return False
    first = line[0]
    if first.islower():
        return True
    return bool(re.match(r"^(và|hoặc|của|theo|với|trong|ngoài|để|nhằm|khi|nếu)\b", line, re.IGNORECASE))


def la_dong_muc_moi(line: str) -> bool:
    """Nhận diện dòng bắt đầu một mục/list mới."""

    line = lam_sach_dong(line)
    return bool(re.match(r"^(-|\+|•|\d+[\.)]|[a-zA-Z]\))\s+", line))


def nen_gop_dong(prev: str, cur: str, cau_hinh: CauHinhOCR = CAU_HINH_MAC_DINH) -> bool:
    """Quyết định có gộp dòng hiện tại vào dòng trước không."""

    prev = lam_sach_dong(prev)
    cur = lam_sach_dong(cur)
    if not prev or not cur:
        return False
    if la_dong_co_cau_truc(cur):
        return False
    if la_dong_muc_moi(cur):
        return False
    if prev.endswith((".", ";", ":", "!", "?", "/.", "./.")):
        return False
    if prev.isupper() and len(prev) > 8:
        return False
    if dong_ket_thuc_mem(prev):
        return True
    if bat_dau_bang_chu_thuong_hoac_tiep_noi(cur):
        return True
    if cau_hinh.che_do_gop_dong == "aggressive":
        return not cur.startswith(("Nơi nhận:", "KT.", "TM.", "PHÓ", "TỔNG"))
    return False


def khoi_phuc_bullet_hanh_chinh(lines: list[str]) -> list[str]:
    """Khôi phục gạch đầu dòng cho các dòng tiêu chí thường gặp trong công văn/biểu mẫu.

    Đây là rule chung theo ngữ cảnh văn bản hành chính, không phụ thuộc một file cụ thể.
    """

    bullet_starts = (
        "Sinh viên ",
        "Học sinh ",
        "Điểm trung bình",
        "Đánh giá rèn luyện",
        "Ưu tiên ",
        "Bản sao ",
        "Giấy xác nhận",
        "Đơn ",
        "Phiếu ",
        "Minh chứng ",
    )
    fixed: list[str] = []
    inside_after_colon = False
    for raw in lines:
        s = lam_sach_dong(raw)
        if not s:
            fixed.append(s)
            continue
        if s.endswith(":") or "các tiêu chí sau" in s.lower() or "hồ sơ gồm" in s.lower():
            inside_after_colon = True
            fixed.append(s)
            continue
        if inside_after_colon and s.startswith(bullet_starts) and not la_dong_muc_moi(s):
            s = "- " + s
        if s.endswith((".", ";", "./.")) and not s.endswith(":"):
            # Sau vài dòng có dấu kết thúc, vẫn để inside_after_colon cho list ngắn; không quá mạnh.
            pass
        fixed.append(s)
    return fixed


def gop_dong_bi_vo(raw_text: str, cau_hinh: CauHinhOCR = CAU_HINH_MAC_DINH) -> str:
    """Gộp các dòng OCR bị xuống dòng sai nhưng vẫn giữ heading/list/metadata."""

    lines = [lam_sach_dong(x) for x in raw_text.splitlines()]
    lines = [x for x in lines if x]
    lines = khoi_phuc_bullet_hanh_chinh(lines)

    merged: list[str] = []
    for line in lines:
        if not merged:
            merged.append(line)
            continue
        if nen_gop_dong(merged[-1], line, cau_hinh):
            merged[-1] = merged[-1].rstrip() + " " + line.lstrip()
        else:
            merged.append(line)

    text = "\n".join(merged)

    # Sửa trường hợp OCR làm mất dấu hai chấm trước list.
    text = re.sub(
        r"(các tiêu chí sau đây)\s+-\s+",
        r"\1:\n- ",
        text,
        flags=re.IGNORECASE,
    )
    text = text.replace("Trân trọng cảm ơn./ Nơi nhận:", "Trân trọng cảm ơn./.\nNơi nhận:")
    return lam_sach_text(text)


def format_dong_markdown(line: str) -> str:
    """Định dạng một dòng text thành Markdown theo cấu trúc nhận diện được."""

    line = lam_sach_dong(line)
    if not line:
        return ""
    if line.startswith("<!--"):
        return line
    if la_tieu_de_doc_lap(line):
        return f"# {line}"
    if la_heading_chuong(line):
        return f"## {line}"
    if la_heading_muc(line):
        return f"### {line}"
    if la_heading_dieu(line):
        return f"### {line}"
    return line


def format_text_sang_markdown(raw_text: str, cau_hinh: CauHinhOCR = CAU_HINH_MAC_DINH) -> str:
    """Chuyển text sau OCR/extract thành Markdown có cấu trúc nhẹ."""

    text = gop_dong_bi_vo(raw_text, cau_hinh)
    lines = [format_dong_markdown(x) for x in text.splitlines()]
    lines = [x for x in lines if x]
    return "\n\n".join(lines)


def chuan_hoa_header_footer(line: str) -> str:
    """Chuẩn hóa dòng để phát hiện header/footer lặp giữa nhiều trang."""

    line = lam_sach_dong(line).lower()
    line = re.sub(r"\d+", "#", line)
    return line


def tim_dong_lap(page_texts: list[str], min_ratio: float = 0.60) -> set[str]:
    """Tìm các dòng lặp trên nhiều trang, thường là header/footer."""

    if len(page_texts) < 3:
        return set()
    freq: dict[str, int] = {}
    for text in page_texts:
        seen_in_page = set()
        for raw_line in text.splitlines():
            line = lam_sach_dong(raw_line)
            if not line or len(line) < 5 or la_dong_co_cau_truc(line):
                continue
            seen_in_page.add(chuan_hoa_header_footer(line))
        for norm in seen_in_page:
            freq[norm] = freq.get(norm, 0) + 1
    threshold = max(2, int(len(page_texts) * min_ratio))
    return {line for line, count in freq.items() if count >= threshold}


def xoa_dong_lap(text: str, repeated_lines: set[str]) -> str:
    """Loại bỏ header/footer lặp đã phát hiện."""

    if not repeated_lines:
        return text
    kept = []
    for raw_line in text.splitlines():
        line = lam_sach_dong(raw_line)
        if chuan_hoa_header_footer(line) in repeated_lines:
            continue
        kept.append(raw_line)
    return "\n".join(kept)
