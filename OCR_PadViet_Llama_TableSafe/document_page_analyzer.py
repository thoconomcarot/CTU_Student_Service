"""
document_page_analyzer.py

Nhận diện trang có bảng/lưu đồ thật để router quyết định khi nào cần gọi LlamaParse.
Module này CHỈ PHÂN TÍCH layout, tuyệt đối không trích bảng bằng PyMuPDF.

Mục tiêu:
- Trang văn bản thường -> dùng PyMuPDF text/Paddle+VietOCR local.
- Trang có bảng/lưu đồ/ô kẻ thật -> dùng LlamaParse để xuất bảng Markdown.
- Không tạo bảng khi file gốc không có bảng.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

import fitz  # PyMuPDF


@dataclass
class PageLayoutSignal:
    """Kết quả phân tích layout của một trang PDF.

    page_number: số trang 1-based.
    likely_table: True nếu có đủ bằng chứng trang có bảng/lưu đồ thật.
    reasons: các lý do giúp debug vì sao trang bị route sang LlamaParse.
    """

    page_number: int
    likely_table: bool
    text_chars: int
    vector_line_count: int = 0
    raster_line_score: float = 0.0
    keyword_score: int = 0
    reasons: list[str] = field(default_factory=list)


def normalize_text_for_match(text: str) -> str:
    """Chuẩn hóa text nhẹ để so khớp keyword layout.

    Không bỏ dấu hoàn toàn để tránh match quá rộng. Hàm chỉ lower-case và gộp khoảng trắng.
    """
    text = str(text or "").lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def count_vector_line_items(page: fitz.Page) -> int:
    """Đếm số đường kẻ vector trong trang PDF.

    Hàm dùng page.get_drawings() nhưng chỉ đọc các item dạng line/curve để phát hiện
    bảng/lưu đồ. Không dùng page.find_tables() nên không sinh bảng giả.
    """
    try:
        drawings = page.get_drawings()
    except Exception:
        return 0

    count = 0
    for drawing in drawings:
        for item in drawing.get("items", []):
            kind = item[0]
            if kind in {"l", "c", "qu"}:  # line, curve, quad/shape
                count += 1
    return count


def keyword_score_for_table_or_flow(text: str) -> tuple[int, list[str]]:
    """Tính điểm keyword cho trang có bảng/lưu đồ thật.

    Rule cố tình chặt: chỉ cho điểm cao khi có các cụm đặc trưng của bảng quy trình
    như `Bước`, `Lưu đồ`, `Nội dung công việc`, `Người thực hiện`, `Thời gian`.
    Các mục văn bản thường như `1. Cơ sở thực hiện`, `1.1 Mục đích` không đủ điều kiện.
    """
    t = normalize_text_for_match(text)
    score = 0
    reasons: list[str] = []

    strong_phrases = [
        "ii. lưu đồ",
        "lưu đồ",
        "khung kế hoạch thực hiện",
    ]
    header_terms = [
        "bước",
        "nội dung công việc",
        "người thực hiện",
        "thời gian thực hiện",
        "ghi chú",
        "đơn vị",
        "phối hợp",
    ]

    if any(p in t for p in strong_phrases):
        score += 2
        reasons.append("keyword_luu_do_or_khung_ke_hoach")

    matched_headers = [term for term in header_terms if term in t]
    if len(matched_headers) >= 3:
        score += len(matched_headers)
        reasons.append("many_table_header_terms:" + ",".join(matched_headers[:5]))

    # Dấu hiệu lưu đồ có trạng thái hồ sơ đạt/không đạt thường nằm trong bảng flowchart.
    if "hồ sơ đạt" in t and "hồ sơ không đạt" in t:
        score += 2
        reasons.append("flowchart_decision_labels")

    return score, reasons


def render_page_for_analysis(page: fitz.Page, dpi: int = 120) -> bytes:
    """Render trang PDF ở DPI thấp để phân tích đường kẻ raster.

    DPI thấp giúp phân tích nhanh, không dùng ảnh này cho OCR chính.
    """
    pix = page.get_pixmap(dpi=dpi, alpha=False)
    return pix.tobytes("png")


def raster_line_score(page: fitz.Page, dpi: int = 120) -> float:
    """Ước lượng mật độ đường kẻ ngang/dọc trên trang scan hoặc PDF render.

    Trả điểm 0..1 dựa trên số contour đường ngang/dọc tìm được bằng OpenCV.
    Nếu không cài cv2/numpy thì trả 0 để pipeline vẫn chạy được.
    """
    try:
        import cv2
        import numpy as np
    except Exception:
        return 0.0

    try:
        png_bytes = render_page_for_analysis(page, dpi=dpi)
        arr = np.frombuffer(png_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return 0.0

        # Binarize đảo màu: đường kẻ/chữ thành trắng trên nền đen.
        binary = cv2.adaptiveThreshold(
            img, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 31, 15
        )
        h, w = binary.shape[:2]

        # Kernel dài để chỉ giữ đường ngang/dọc dài, giảm nhiễu chữ.
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(20, w // 25), 1))
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(20, h // 35)))
        horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel, iterations=1)
        vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel, iterations=1)

        h_contours, _ = cv2.findContours(horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        v_contours, _ = cv2.findContours(vertical, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        line_count = len(h_contours) + len(v_contours)

        # Chuẩn hóa thô: bảng/lưu đồ thường có nhiều hơn 15 đường dài.
        return min(line_count / 40.0, 1.0)
    except Exception:
        return 0.0


def analyze_page(page: fitz.Page, page_number: int) -> PageLayoutSignal:
    """Phân tích một trang PDF và quyết định có khả năng là bảng/lưu đồ thật không."""
    raw_text = page.get_text("text") or ""
    vector_lines = count_vector_line_items(page)
    r_score = raster_line_score(page)
    k_score, k_reasons = keyword_score_for_table_or_flow(raw_text)

    reasons: list[str] = []
    reasons.extend(k_reasons)
    if vector_lines >= 20:
        reasons.append(f"many_vector_lines:{vector_lines}")
    if r_score >= 0.45:
        reasons.append(f"raster_line_score:{r_score:.2f}")

    # Quy tắc chặt để tránh false positive:
    # - Nếu có keyword bảng/lưu đồ + đường kẻ thật -> chắc chắn route LlamaParse.
    # - Nếu không có keyword nhưng line score rất cao -> có thể là biểu mẫu/bảng scan.
    likely = False
    if k_score >= 3 and (vector_lines >= 10 or r_score >= 0.30):
        likely = True
    elif vector_lines >= 45 or r_score >= 0.75:
        likely = True

    return PageLayoutSignal(
        page_number=page_number,
        likely_table=likely,
        text_chars=len(raw_text.strip()),
        vector_line_count=vector_lines,
        raster_line_score=r_score,
        keyword_score=k_score,
        reasons=reasons,
    )


def page_range(total_pages: int, page_start: Optional[int], page_end: Optional[int]) -> range:
    """Tạo range index trang 0-based từ page_start/page_end 1-based."""
    start = max(1, int(page_start or 1))
    end = int(page_end or total_pages)
    end = min(end, total_pages)
    if end < start:
        end = start
    return range(start - 1, end)


def analyze_pdf_pages(
    pdf_path: str | Path,
    page_start: Optional[int] = None,
    page_end: Optional[int] = None,
) -> list[PageLayoutSignal]:
    """Phân tích các trang PDF để tìm trang cần LlamaParse xử lý bảng/lưu đồ."""
    path = Path(pdf_path)
    if path.suffix.lower() != ".pdf":
        return []

    doc = fitz.open(str(path))
    try:
        signals: list[PageLayoutSignal] = []
        for idx in page_range(len(doc), page_start, page_end):
            signals.append(analyze_page(doc[idx], idx + 1))
        return signals
    finally:
        doc.close()


def group_contiguous_pages(pages: Iterable[int]) -> list[tuple[int, int]]:
    """Gộp danh sách trang 1-based thành các khoảng liên tiếp để giảm số lần gọi engine."""
    sorted_pages = sorted(set(int(p) for p in pages))
    if not sorted_pages:
        return []

    groups: list[tuple[int, int]] = []
    start = prev = sorted_pages[0]
    for page in sorted_pages[1:]:
        if page == prev + 1:
            prev = page
        else:
            groups.append((start, prev))
            start = prev = page
    groups.append((start, prev))
    return groups


def table_pages_from_signals(signals: list[PageLayoutSignal]) -> list[int]:
    """Lấy danh sách trang được đánh giá là có bảng/lưu đồ thật."""
    return [s.page_number for s in signals if s.likely_table]
