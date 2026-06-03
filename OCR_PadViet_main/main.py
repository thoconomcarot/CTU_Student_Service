"""
chay_ocr.py
File chạy chính cho OCR CTU sạch và dễ mở rộng.

Pipeline tổng quát:
1. PDF text -> PyMuPDF extract.
2. PDF scan / ảnh -> render ảnh -> PaddleOCR detect + VietOCR recognize.
3. Lớp 1: sửa lỗi OCR phổ biến trong văn bản hành chính.
4. Lớp 2: chuẩn hóa từ điển/thuật ngữ CTU.
5. Lớp 3: lỗi riêng/ít gặp -> cảnh báo review hoặc sửa bằng JSON ngoài source.
6. Gộp dòng, định dạng Markdown, ghi output + review report.
"""



from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF

from config import (
    CAU_HINH_MAC_DINH,
    DUOI_ANH,
    DUOI_PDF,
    CauHinhOCR,
    ghi_text_unicode,
    lam_sach_text,
    tao_thu_muc_can_thiet,
    ten_file_an_toan,
    tinh_checksum,
)
from markdown_layout import format_text_sang_markdown, tim_dong_lap, xoa_dong_lap
from common_fix import hau_xu_ly_loi_chung
from rare_fix import ghi_bao_cao_review, hau_xu_ly_loi_rieng, tao_bao_cao_review
from ocr_engine import danh_gia_chat_luong_text_layer, ocr_anh_bang_paddle_vietocr, ocr_anh_paddle_thuan
from ctu_terms import canh_bao_thuat_ngu_ctu, hau_xu_ly_tu_dien_ctu


# =========================================================
# HẬU XỬ LÝ 3 LỚP
# =========================================================


def chay_ba_lop_hau_xu_ly(text: str, cau_hinh: CauHinhOCR) -> str:
    """Chạy 3 lớp hậu xử lý theo đúng thứ tự: lỗi chung -> từ điển CTU -> lỗi riêng."""

    text = lam_sach_text(text)
    if cau_hinh.dung_loi_chung:
        text = hau_xu_ly_loi_chung(text)
    if cau_hinh.dung_tu_dien_ctu:
        text = hau_xu_ly_tu_dien_ctu(text)
    if cau_hinh.dung_loi_rieng:
        text = hau_xu_ly_loi_rieng(text, cau_hinh)
    return lam_sach_text(text)


# =========================================================
# BẢNG MARKDOWN NHẸ TỪ PYMUPDF
# =========================================================


def escape_o_bang(value: Any) -> str:
    """Làm sạch một ô bảng để không phá Markdown table."""

    if value is None:
        return ""
    value = str(value).replace("\n", "<br>").replace("|", "\\|")
    value = " ".join(value.split())
    return value.strip()


def bang_sang_markdown(table_data: list[list[Any]]) -> str:
    """Chuyển list[list] từ PyMuPDF table thành Markdown table."""

    if not table_data:
        return ""
    rows: list[list[str]] = []
    for row in table_data:
        if row is None:
            continue
        cleaned = [escape_o_bang(cell) for cell in row]
        if any(cleaned):
            rows.append(cleaned)
    if not rows:
        return ""
    max_cols = max(len(row) for row in rows)
    rows = [row + [""] * (max_cols - len(row)) for row in rows]
    header = rows[0] if len(rows) > 1 else [f"Cột {i + 1}" for i in range(max_cols)]
    body = rows[1:] if len(rows) > 1 else rows
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---"] * max_cols) + " |",
    ]
    for row in body:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def trich_bang_pymupdf(page: fitz.Page) -> list[str]:
    """Trích bảng bằng PyMuPDF nếu phiên bản hiện tại hỗ trợ find_tables()."""

    markdown_tables: list[str] = []
    try:
        finder = page.find_tables()
        tables = getattr(finder, "tables", []) or []
        for table in tables:
            try:
                data = table.extract()
                md = bang_sang_markdown(data)
                if md:
                    markdown_tables.append(md)
            except Exception:
                continue
    except Exception:
        return []
    return markdown_tables


# =========================================================
# RENDER PDF / OCR TRANG
# =========================================================


def render_trang_pdf(page: fitz.Page, file_stem: str, page_number: int, cau_hinh: CauHinhOCR) -> str | None:
    """Render một trang PDF thành ảnh PNG, có cache để không render lại."""

    image_path = os.path.join(cau_hinh.thu_muc_anh_tam, f"{ten_file_an_toan(file_stem)}_page_{page_number}.png")
    if cau_hinh.dung_cache_anh and os.path.exists(image_path):
        print(f"[CACHE] Dùng lại ảnh trang đã có: {image_path}")
        return image_path
    if cau_hinh.chi_dung_anh_cache:
        print(f"[SKIP] Chưa có ảnh cache trang {page_number}, bỏ qua render.")
        return None

    print(f"[RENDER] Trang {page_number} -> ảnh, dpi={cau_hinh.dpi}")
    try:
        pix = page.get_pixmap(dpi=cau_hinh.dpi, alpha=False)
    except TypeError:
        pix = page.get_pixmap(dpi=cau_hinh.dpi)
    Path(image_path).parent.mkdir(parents=True, exist_ok=True)
    pix.save(image_path)
    return image_path


def ocr_anh(image_path: str, cau_hinh: CauHinhOCR) -> tuple[str, str]:
    """OCR ảnh bằng Paddle+VietOCR; nếu không có VietOCR thì fallback PaddleOCR thuần."""

    text = ocr_anh_bang_paddle_vietocr(image_path, cau_hinh)
    method = "paddle_detect_vietocr_recognize"
    if not text:
        text = ocr_anh_paddle_thuan(image_path, cau_hinh)
        method = "paddleocr_plain"
    text = chay_ba_lop_hau_xu_ly(text, cau_hinh)
    return text, method


def xu_ly_trang_pdf_text(page: fitz.Page, raw_text: str, cau_hinh: CauHinhOCR) -> tuple[str, int, int]:
    """Xử lý một trang PDF có text copy được: hậu xử lý text và trích bảng nếu có."""

    parts = ["<!-- extraction: pymupdf_text -->"]
    text = chay_ba_lop_hau_xu_ly(raw_text, cau_hinh)
    text_md = format_text_sang_markdown(text, cau_hinh)
    if text_md:
        parts.append(text_md)

    tables = trich_bang_pymupdf(page)
    if tables:
        parts.append("\n## Bảng trích xuất bằng PyMuPDF")
        parts.extend(tables)
    return "\n\n".join(parts), len(text), len(tables)


def xu_ly_trang_pdf_scan(page: fitz.Page, file_stem: str, page_number: int, cau_hinh: CauHinhOCR) -> tuple[str, int, int]:
    """Xử lý một trang PDF scan: render sang ảnh rồi OCR."""

    image_path = render_trang_pdf(page, file_stem, page_number, cau_hinh)
    parts = ["<!-- extraction: ocr_pdf_scan -->"]
    if image_path is None:
        parts.append("[Không có ảnh cache để OCR trang này]")
        return "\n\n".join(parts), 0, 0

    text, method = ocr_anh(image_path, cau_hinh)
    parts.append(f"<!-- ocr_method: {method} -->")
    if text:
        parts.append(format_text_sang_markdown(text, cau_hinh))
        return "\n\n".join(parts), len(text), 0
    parts.append("[Trang này không OCR được text]")
    return "\n\n".join(parts), 0, 0


# =========================================================
# XỬ LÝ FILE
# =========================================================


def tinh_khoang_trang(total_pages: int, cau_hinh: CauHinhOCR) -> tuple[int, int]:
    """Tính khoảng trang cần xử lý theo cấu hình, đánh số trang bắt đầu từ 1."""

    start_page = int(cau_hinh.trang_bat_dau or 0)
    end_page = int(cau_hinh.trang_ket_thuc or 0)
    if start_page <= 0:
        start_page = 1
    if end_page <= 0 or end_page > total_pages:
        end_page = total_pages
    if start_page > total_pages:
        start_page = total_pages
    if end_page < start_page:
        end_page = start_page
    return start_page, end_page




def tinh_ti_le_anh_tren_trang(page: fitz.Page) -> tuple[float, float]:
    """
    Ước lượng trang PDF có phải dạng scan/ảnh hay không.

    Trả về:
    - total_image_ratio: tổng diện tích block ảnh / diện tích trang.
    - max_image_ratio: diện tích block ảnh lớn nhất / diện tích trang.

    PDF scan thường có một ảnh lớn phủ gần hết trang. PDF text thật thường không có
    ảnh phủ toàn trang, dù có thể có logo hoặc con dấu nhỏ.
    """

    try:
        page_area = max(float(page.rect.width * page.rect.height), 1.0)
        data = page.get_text("dict")
        total_area = 0.0
        max_area = 0.0
        for block in data.get("blocks", []):
            if block.get("type") != 1:
                continue
            bbox = block.get("bbox")
            if not bbox or len(bbox) != 4:
                continue
            rect = fitz.Rect(bbox)
            area = max(float(rect.width * rect.height), 0.0)
            total_area += area
            max_area = max(max_area, area)
        return min(total_area / page_area, 1.0), min(max_area / page_area, 1.0)
    except Exception:
        return 0.0, 0.0


def nen_bo_text_layer_pdf(
    raw_text: str,
    page: fitz.Page,
    cau_hinh: CauHinhOCR,
) -> tuple[bool, dict[str, object]]:
    """
    Quyết định có bỏ text layer PyMuPDF của một trang hay không.

    Đây là rule tổng quát:
    1. Nếu người dùng bật --force-ocr -> bỏ luôn text layer.
    2. Nếu trang không có text đủ dài -> không gọi là lỗi text layer, nhưng vẫn OCR vì thiếu text.
    3. Nếu text layer có điểm nhiễu cao -> OCR lại từ ảnh render.
    4. Nếu trang giống PDF scan vì có ảnh phủ gần hết trang và text layer có dấu hiệu yếu
       -> OCR lại, tránh lấy text layer OCR cũ.
    """

    if cau_hinh.bo_qua_text_layer_pdf:
        return True, {"reason": "force_ocr"}

    raw_text = raw_text or ""
    if len(raw_text.strip()) < cau_hinh.do_dai_text_toi_thieu:
        return False, {"reason": "text_too_short"}

    quality = danh_gia_chat_luong_text_layer(raw_text)
    total_image_ratio, max_image_ratio = tinh_ti_le_anh_tren_trang(page)
    quality["total_image_ratio"] = round(total_image_ratio, 4)
    quality["max_image_ratio"] = round(max_image_ratio, 4)

    if not cau_hinh.tu_dong_bo_text_layer_loi:
        return False, quality

    # Lỗi mạnh thì OCR lại, dù PDF có phải scan hay không.
    if bool(quality.get("is_bad")):
        return True, quality

    # Trường hợp nhẹ hơn: trang là scan/full-page image và text layer hơi yếu.
    # Điều này xử lý các PDF scan có OCR layer cũ nhưng chưa đủ tệ để bị bắt bằng score.
    score = int(quality.get("score", 0) or 0)
    suspicious_ratio = float(quality.get("suspicious_token_ratio", 0.0) or 0.0)
    mark_ratio = float(quality.get("mark_ratio", 0.0) or 0.0)
    common_ratio = float(quality.get("common_ratio", 0.0) or 0.0)
    looks_like_scan = max_image_ratio >= 0.55 or total_image_ratio >= 0.70

    if looks_like_scan and common_ratio >= 0.10 and mark_ratio < 0.04 and (score >= 2 or suspicious_ratio >= 0.02):
        quality["is_bad"] = True
        quality["reason"] = str(quality.get("reason", "")) + ",scan_page_with_weak_text_layer"
        return True, quality

    return False, quality

def xu_ly_pdf(pdf_path: str | Path, cau_hinh: CauHinhOCR) -> tuple[str, dict[str, int]]:
    """Xử lý PDF hybrid: tự chọn PyMuPDF text hoặc OCR theo từng trang."""

    doc = fitz.open(pdf_path)
    file_stem = Path(pdf_path).stem
    total_pages = len(doc)

    # Không phải PDF nào có page.get_text("text") cũng là PDF text thật.
    # Có loại PDF scan được OCR sẵn từ trước: ảnh nhìn rõ nhưng text layer ẩn bị sai.
    # Phần dưới đánh giá theo tiêu chí tổng quát, không bắt lỗi riêng từng file:
    # - text layer có nhiều ký tự/ký hiệu bất thường;
    # - nhiều token bị chen số/ký hiệu vào giữa chữ;
    # - dấu tiếng Việt quá thấp trong văn bản có ngữ cảnh tiếng Việt;
    # - trang có ảnh phủ gần hết trang nhưng text layer yếu.
    raw_page_texts_goc: list[str] = []
    bad_text_layer_flags: list[bool] = []
    text_layer_reports: list[dict[str, object]] = []

    for page_index, page in enumerate(doc):
        page_number = page_index + 1
        raw_text = lam_sach_text(page.get_text("text"))
        raw_page_texts_goc.append(raw_text)

        should_skip, report = nen_bo_text_layer_pdf(raw_text, page, cau_hinh)
        text_layer_reports.append(report)
        bad_text_layer_flags.append(should_skip)

        if should_skip and raw_text:
            reason = report.get("reason", "unknown")
            score = report.get("score", "-")
            print(f"[OCR] Trang {page_number} -> bỏ text layer, OCR lại từ ảnh (score={score}, reason={reason})")

    raw_text_pages = sum(1 for text in raw_page_texts_goc if len(text.strip()) >= cau_hinh.do_dai_text_toi_thieu)
    bad_pages = [i + 1 for i, is_bad in enumerate(bad_text_layer_flags) if is_bad]

    force_ocr_whole_pdf = False
    if cau_hinh.bo_qua_text_layer_pdf:
        force_ocr_whole_pdf = True
    elif cau_hinh.tu_dong_bo_text_layer_loi and raw_text_pages > 0 and bad_pages:
        bad_ratio = len(bad_pages) / max(raw_text_pages, 1)
        # Nếu nhiều trang trong cùng PDF có text layer không đáng tin, coi cả PDF là
        # nhóm scan/OCR-layer cũ và OCR lại toàn bộ để không sót các trang ngắn.
        if len(bad_pages) >= 2 or bad_ratio >= 0.35:
            force_ocr_whole_pdf = True
            print(
                f"[OCR] PDF có text layer không đáng tin ở các trang {bad_pages} "
                f"({len(bad_pages)}/{raw_text_pages} trang có text) -> OCR lại toàn bộ PDF"
            )

    raw_page_texts: list[str] = []
    for page_index, raw_text in enumerate(raw_page_texts_goc):
        page_number = page_index + 1

        if force_ocr_whole_pdf:
            raw_page_texts.append("")
            continue

        if bad_text_layer_flags[page_index]:
            print(f"[OCR] Trang {page_number} -> text layer lỗi, OCR lại từ ảnh scan")
            raw_page_texts.append("")
            continue

        raw_page_texts.append(raw_text)

    repeated_lines = set()
    if cau_hinh.xoa_header_footer_lap:
        repeated_lines = tim_dong_lap(raw_page_texts, min_ratio=cau_hinh.ti_le_lap_header_footer)

    start_page, end_page = tinh_khoang_trang(total_pages, cau_hinh)
    if start_page != 1 or end_page != total_pages:
        print(f"[INFO] Chỉ xử lý trang {start_page} đến {end_page} / {total_pages} trang")

    pages_md: list[str] = []
    total_chars = 0
    pymupdf_pages = 0
    ocr_pages = 0
    table_pages = 0

    for page_index in range(start_page - 1, end_page):
        page = doc[page_index]
        page_number = page_index + 1
        raw_text = xoa_dong_lap(raw_page_texts[page_index], repeated_lines)
        raw_text = chay_ba_lop_hau_xu_ly(raw_text, cau_hinh)

        page_parts = [f"## Trang {page_number}", f"<!-- page: {page_number} -->"]
        if len(raw_text) >= cau_hinh.do_dai_text_toi_thieu:
            pymupdf_pages += 1
            content, chars, tables = xu_ly_trang_pdf_text(page, raw_text, cau_hinh)
            total_chars += chars
            table_pages += tables
        else:
            ocr_pages += 1
            content, chars, tables = xu_ly_trang_pdf_scan(page, file_stem, page_number, cau_hinh)
            total_chars += chars
            table_pages += tables
        page_parts.append(content)
        page_parts.append("\n---\n")
        pages_md.append("\n\n".join(page_parts))

    doc.close()
    metadata = {
        "total_pages": end_page - start_page + 1,
        "total_characters": total_chars,
        "pymupdf_pages": pymupdf_pages,
        "ocr_pages": ocr_pages,
        "table_pages": table_pages,
        "source_total_pages": total_pages,
        "page_start": start_page,
        "page_end": end_page,
    }
    return "\n\n".join(pages_md), metadata


def xu_ly_file_anh(image_path: str | Path, cau_hinh: CauHinhOCR) -> tuple[str, dict[str, int]]:
    """Xử lý một file ảnh đơn lẻ và xuất Markdown."""

    text, method = ocr_anh(str(image_path), cau_hinh)
    parts = ["## Trang 1", "<!-- page: 1 -->", f"<!-- extraction: {method} -->"]
    parts.append(format_text_sang_markdown(text, cau_hinh) if text else "[Ảnh này không OCR được text]")
    parts.append("\n---\n")
    metadata = {
        "total_pages": 1,
        "total_characters": len(text),
        "pymupdf_pages": 0,
        "ocr_pages": 1,
        "table_pages": 0,
        "source_total_pages": 1,
        "page_start": 1,
        "page_end": 1,
    }
    return "\n\n".join(parts), metadata


def tao_metadata_markdown(file_path: str | Path, metadata: dict[str, int], cau_hinh: CauHinhOCR) -> str:
    """Tạo khối metadata Markdown ở đầu file output."""

    lines = [
        "# PDF / Image Text Document",
        "",
        "## Metadata",
        "",
        f"- Source file: `{file_path}`",
        f"- Source name: `{Path(file_path).name}`",
        "- Extraction mode: ocr_ctu_sach_se_v1",
        "- Parser: PyMuPDF",
        "- OCR engine: PaddleOCR detection + VietOCR recognition; fallback PaddleOCR recognition",
        f"- OCR language: {cau_hinh.ngon_ngu_ocr}",
        f"- Render DPI: {cau_hinh.dpi}",
        f"- Force OCR PDF text layer: {cau_hinh.bo_qua_text_layer_pdf}",
        f"- Auto skip bad PDF text layer: {cau_hinh.tu_dong_bo_text_layer_loi}",
        "- Text layer check: generic quality score + scan page image ratio",
        f"- Layout merge mode: {cau_hinh.che_do_gop_dong}",
        f"- Total pages: {metadata.get('total_pages', 0)}",
        f"- Total characters: {metadata.get('total_characters', 0)}",
        f"- PyMuPDF pages: {metadata.get('pymupdf_pages', 0)}",
        f"- OCR pages: {metadata.get('ocr_pages', 0)}",
        f"- Table pages: {metadata.get('table_pages', 0)}",
        f"- Checksum: {tinh_checksum(file_path)}",
        "",
        "## Extracted Text",
        "",
    ]
    return "\n".join(lines)


def xu_ly_mot_file(file_path: str | Path, cau_hinh: CauHinhOCR, force: bool = False) -> str | None:
    """Xử lý một file PDF/ảnh, ghi Markdown và review report."""

    path = Path(file_path)
    ext = path.suffix.lower()
    if ext not in DUOI_PDF and ext not in DUOI_ANH:
        print(f"[SKIP] Không hỗ trợ: {path}")
        return None

    out_path = Path(cau_hinh.thu_muc_output) / f"{ten_file_an_toan(path.stem)}_structured.md"
    if out_path.exists() and not force:
        print(f"[SKIP] Output đã tồn tại: {out_path}")
        return str(out_path)

    print(f"[PROCESS] {path}")
    if ext in DUOI_PDF:
        body, metadata = xu_ly_pdf(path, cau_hinh)
    else:
        body, metadata = xu_ly_file_anh(path, cau_hinh)

    final_md = tao_metadata_markdown(path, metadata, cau_hinh) + body
    ghi_text_unicode(out_path, final_md)

    extra_warnings = canh_bao_thuat_ngu_ctu(final_md) if cau_hinh.dung_tu_dien_ctu else []
    warnings = tao_bao_cao_review(final_md, extra_warnings)
    review_path = ghi_bao_cao_review(path, warnings, cau_hinh)

    print(f"[DONE] Markdown: {out_path}")
    if review_path:
        print(f"[REVIEW] Báo cáo dòng nghi ngờ: {review_path}")
    return str(out_path)


def tim_file_ho_tro(path: str | Path) -> list[Path]:
    """Tìm các file PDF/ảnh được hỗ trợ trong một file hoặc thư mục."""

    p = Path(path)
    if p.is_file():
        return [p]
    files: list[Path] = []
    for item in sorted(p.rglob("*")):
        if item.is_file() and item.suffix.lower() in DUOI_PDF.union(DUOI_ANH):
            files.append(item)
    return files


# =========================================================
# CLI
# =========================================================


DEFAULT_INPUT_PATH = r"D:\Code\CTU_Student_Service\Dataset\02_Attachments\PDFs\PDT"


def tao_parser() -> argparse.ArgumentParser:
    """Tạo bộ đọc tham số dòng lệnh cho chương trình."""

    parser = argparse.ArgumentParser(description="OCR CTU sạch: PyMuPDF + PaddleOCR + VietOCR + hậu xử lý 3 lớp.")
    parser.add_argument(
        "path",
        nargs="?",
        default=DEFAULT_INPUT_PATH,
        help="Đường dẫn file PDF/ảnh/docx hoặc thư mục input. Nếu không nhập path thì dùng DEFAULT_INPUT_PATH trong code."
    )
    
    parser.add_argument("--output", default=CAU_HINH_MAC_DINH.thu_muc_output, help="Thư mục lưu Markdown output.")
    parser.add_argument("--force", action="store_true", help="Xử lý lại dù output đã tồn tại.")
    parser.add_argument(
        "--force-ocr",
        action="store_true",
        help="Bỏ qua text layer có sẵn trong PDF và OCR lại từ ảnh scan. Dùng cho PDF scan bị lỗi font/text layer.",
    )
    parser.add_argument(
        "--no-auto-bad-text-layer-check",
        action="store_true",
        help="Tắt tự động phát hiện text layer OCR cũ bị lỗi. Mặc định đang bật.",
    )
    parser.add_argument("--dpi", type=int, default=CAU_HINH_MAC_DINH.dpi, help="DPI render PDF scan.")
    parser.add_argument("--page-start", type=int, default=0, help="Trang bắt đầu, đánh số từ 1. 0 = từ đầu.")
    parser.add_argument("--page-end", type=int, default=0, help="Trang kết thúc, đánh số từ 1. 0 = đến cuối.")
    parser.add_argument("--lang", default=CAU_HINH_MAC_DINH.ngon_ngu_ocr, help="Ngôn ngữ PaddleOCR: vi, latin, en.")
    parser.add_argument("--gpu", action="store_true", help="Bật GPU nếu đã cài Paddle GPU/Torch GPU.")
    parser.add_argument("--no-vietocr", action="store_true", help="Tắt VietOCR, dùng PaddleOCR thuần.")
    parser.add_argument("--vietocr-model", default=CAU_HINH_MAC_DINH.vietocr_model, choices=["vgg_transformer", "vgg_seq2seq"], help="Model VietOCR.")
    parser.add_argument("--vietocr-weights", default="", help="Đường dẫn weights VietOCR custom nếu có.")
    parser.add_argument("--crop-padding", type=int, default=CAU_HINH_MAC_DINH.padding_crop, help="Padding quanh crop OCR.")
    parser.add_argument("--save-crops", action="store_true", help="Lưu crop VietOCR để debug.")
    parser.add_argument("--no-image-cache", action="store_true", help="Không dùng cache ảnh render/ảnh tiền xử lý.")
    parser.add_argument("--existing-images-only", action="store_true", help="Chỉ dùng ảnh cache đã có, không render trang mới.")
    parser.add_argument("--no-red-stamp-clean", action="store_true", help="Không xóa con dấu đỏ trước OCR.")
    parser.add_argument("--no-symbol-fallback", action="store_true", help="Không fallback PaddleOCR cho dòng nghi ký tự đặc biệt.")
    parser.add_argument("--layout-merge-mode", default="conservative", choices=["conservative", "aggressive"], help="Chế độ gộp dòng.")
    parser.add_argument("--loi-rieng-json", default="", help="File JSON chứa rule sửa lỗi riêng, nếu muốn auto-fix ngoài source.")
    parser.add_argument("--no-loi-chung", action="store_true", help="Tắt lớp 1 xử lý lỗi chung.")
    parser.add_argument("--no-tu-dien-ctu", action="store_true", help="Tắt lớp 2 từ điển CTU.")
    parser.add_argument("--no-loi-rieng", action="store_true", help="Tắt lớp 3 lỗi riêng/review.")
    parser.add_argument("--no-debug-images", action="store_true", help="Không giữ ảnh biến thể debug.")
    return parser


def cau_hinh_tu_args(args: argparse.Namespace) -> CauHinhOCR:
    """Chuyển argparse Namespace thành CauHinhOCR."""

    output = args.output
    return CauHinhOCR(
        thu_muc_output=output,
        thu_muc_anh_tam=os.path.join(output, "temp_images"),
        thu_muc_bao_cao=os.path.join(output, "review_reports"),
        dpi=args.dpi,
        trang_bat_dau=args.page_start,
        trang_ket_thuc=args.page_end,
        bo_qua_text_layer_pdf=args.force_ocr,
        tu_dong_bo_text_layer_loi=not args.no_auto_bad_text_layer_check,
        ngon_ngu_ocr=args.lang,
        dung_gpu=args.gpu,
        dung_vietocr=not args.no_vietocr,
        vietocr_model=args.vietocr_model,
        vietocr_weights=args.vietocr_weights,
        padding_crop=args.crop_padding,
        dung_cache_anh=not args.no_image_cache,
        chi_dung_anh_cache=args.existing_images_only,
        luu_anh_debug=not args.no_debug_images,
        luu_crop_vietocr=args.save_crops,
        xoa_con_dau_do=not args.no_red_stamp_clean,
        fallback_ky_tu_dac_biet=not args.no_symbol_fallback,
        dung_loi_chung=not args.no_loi_chung,
        dung_tu_dien_ctu=not args.no_tu_dien_ctu,
        dung_loi_rieng=not args.no_loi_rieng,
        file_loi_rieng_json=args.loi_rieng_json,
        che_do_gop_dong=args.layout_merge_mode,
    )


def main() -> None:
    """Entry point CLI."""

    parser = tao_parser()
    args = parser.parse_args()
    cau_hinh = cau_hinh_tu_args(args)
    tao_thu_muc_can_thiet(cau_hinh)

    files = tim_file_ho_tro(args.path)
    if not files:
        print(f"[WARN] Không tìm thấy file PDF/ảnh trong: {args.path}")
        return

    print(f"[INFO] Tìm thấy {len(files)} file cần xử lý")
    for file_path in files:
        try:
            xu_ly_mot_file(file_path, cau_hinh, force=args.force)
        except Exception as exc:
            print(f"[ERROR] Lỗi khi xử lý {file_path}: {exc}")


if __name__ == "__main__":
    main()
