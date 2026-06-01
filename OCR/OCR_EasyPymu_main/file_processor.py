"""
file_processor.py
Xử lý PDF/ảnh, điều phối PyMuPDF + EasyOCR + Markdown output.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

from common_fix import clean_text
from config import IMAGE_TEMP_FOLDER, MIN_TEXT_LENGTH, OUTPUT_FOLDER, RENDER_DPI, SUPPORTED_IMAGES, SUPPORTED_PDF
from markdown_layout import format_text_to_markdown
from ocr_engine import easyocr_result_to_text, ocr_image_detail
from table_utils import (
    extract_tables_from_pdf_page,
    extract_text_outside_tables,
    looks_like_table_from_ocr,
    ocr_results_to_markdown_table,
)


def extract_pdf_hybrid(pdf_path: str) -> tuple[str, dict[str, int]]:
    """Xử lý PDF text/scan theo hướng hybrid PyMuPDF + EasyOCR."""

    import fitz

    doc = fitz.open(pdf_path)

    all_pages: list[str] = []
    total_chars = 0
    pymupdf_pages = 0
    ocr_pages = 0
    table_pages = 0
    file_stem = Path(pdf_path).stem

    for page_index, page in enumerate(doc):
        page_number = page_index + 1
        raw_text = clean_text(page.get_text("text").strip())

        page_markdown: list[str] = [f"## Trang {page_number}\n"]

        if len(raw_text) >= MIN_TEXT_LENGTH:
            pymupdf_pages += 1
            total_chars += len(raw_text)
            page_markdown.append("<!-- extraction: pymupdf -->\n")

            markdown_tables, table_bboxes = extract_tables_from_pdf_page(page)

            if markdown_tables:
                table_pages += 1
                page_markdown.append("<!-- table_extraction: pymupdf_find_tables -->\n")

                outside_text = clean_text(extract_text_outside_tables(page, table_bboxes))

                if outside_text:
                    page_markdown.append(format_text_to_markdown(outside_text))

                page_markdown.append("\n\n## Bảng trích xuất\n")

                for table_md in markdown_tables:
                    page_markdown.append(table_md)
            else:
                page_markdown.append(format_text_to_markdown(raw_text))

        else:
            ocr_pages += 1
            image_path = IMAGE_TEMP_FOLDER / f"{file_stem}_page_{page_number}.png"

            if image_path.exists():
                print(f"[CACHE] Dùng lại ảnh đã có: {image_path}")
            else:
                print(f"[RENDER] Đang chuyển trang {page_number} thành ảnh...")
                pix = page.get_pixmap(dpi=RENDER_DPI)
                pix.save(str(image_path))

            page_markdown.append("<!-- extraction: easyocr_pdf_scan -->\n")

            ocr_results = ocr_image_detail(str(image_path))
            ocr_text = easyocr_result_to_text(ocr_results)
            total_chars += len(ocr_text)

            if ocr_results and looks_like_table_from_ocr(ocr_results):
                table_md = ocr_results_to_markdown_table(ocr_results)

                if table_md:
                    table_pages += 1
                    page_markdown.append("<!-- table_extraction: easyocr_bbox_rebuild -->\n")
                    page_markdown.append("## Bảng trích xuất từ OCR\n\n")
                    page_markdown.append(table_md)
                else:
                    page_markdown.append(format_text_to_markdown(ocr_text))
            else:
                if ocr_text:
                    page_markdown.append(format_text_to_markdown(ocr_text))
                else:
                    page_markdown.append("[Trang này không OCR được text]")

        page_markdown.append("\n---\n")
        all_pages.append("\n".join(page_markdown))

    doc.close()

    metadata = {
        "total_pages": len(all_pages),
        "total_characters": total_chars,
        "pymupdf_pages": pymupdf_pages,
        "ocr_pages": ocr_pages,
        "table_pages": table_pages,
    }

    return "\n\n".join(all_pages), metadata


def extract_image_file(image_path: str) -> tuple[str, dict[str, int]]:
    """Xử lý file ảnh bằng EasyOCR và dựng bảng Markdown nếu nhận diện được bảng."""

    ocr_results = ocr_image_detail(str(image_path))
    text = easyocr_result_to_text(ocr_results)

    markdown_parts: list[str] = ["## Trang 1\n", "<!-- extraction: easyocr_image -->\n"]
    table_pages = 0

    if ocr_results and looks_like_table_from_ocr(ocr_results):
        table_md = ocr_results_to_markdown_table(ocr_results)

        if table_md:
            table_pages = 1
            markdown_parts.append("<!-- table_extraction: easyocr_bbox_rebuild -->\n")
            markdown_parts.append("## Bảng trích xuất từ ảnh\n\n")
            markdown_parts.append(table_md)
        else:
            markdown_parts.append(format_text_to_markdown(text))
    else:
        if text:
            markdown_parts.append(format_text_to_markdown(text))
        else:
            markdown_parts.append("[Ảnh này không OCR được text]")

    markdown_parts.append("\n---\n")

    metadata = {
        "total_pages": 1,
        "total_characters": len(text),
        "pymupdf_pages": 0,
        "ocr_pages": 1,
        "table_pages": table_pages,
    }

    return "\n".join(markdown_parts), metadata


def get_output_path_for_source(source_path: str | Path) -> Path:
    """Tạo đường dẫn output tương ứng với file nguồn."""

    file_stem = Path(source_path).stem
    return OUTPUT_FOLDER / f"{file_stem}_structured.md"


def save_markdown_output(source_path: str | Path, content: str, metadata: dict[str, int], extraction_mode: str) -> Path:
    """Ghi kết quả Markdown ra file output."""

    file_name = os.path.basename(str(source_path))
    output_path = get_output_path_for_source(source_path)

    with open(output_path, "w", encoding="utf-8") as file:
        file.write("# PDF / Image Text Document\n\n")
        file.write("## Metadata\n\n")
        file.write(f"- Source file: `{source_path}`\n")
        file.write(f"- Source name: `{file_name}`\n")
        file.write(f"- Extraction mode: {extraction_mode}\n")
        file.write("- Parser: PyMuPDF\n")
        file.write("- OCR engine: EasyOCR\n")
        file.write("- Language: vi\n")
        file.write(f"- Total pages: {metadata['total_pages']}\n")
        file.write(f"- Total characters: {metadata['total_characters']}\n")
        file.write(f"- PyMuPDF pages: {metadata['pymupdf_pages']}\n")
        file.write(f"- OCR pages: {metadata['ocr_pages']}\n")
        file.write(f"- Table pages: {metadata.get('table_pages', 0)}\n")
        file.write(f"- Created at: {datetime.now().isoformat(timespec='seconds')}\n\n")
        file.write("## Extracted Text\n\n")
        file.write(content)

    print(f"[OK] Đã lưu: {output_path}")
    return output_path


def process_one_file(file_path: str | Path, force: bool = False) -> None:
    """Xử lý 1 file PDF hoặc ảnh cụ thể."""

    file_path = Path(file_path)
    file_name = file_path.name
    ext = file_path.suffix.lower()

    if not file_path.exists():
        print(f"[ERROR] Không tìm thấy file: {file_path}")
        return

    if ext not in SUPPORTED_PDF and ext not in SUPPORTED_IMAGES:
        print(f"[SKIP] Không hỗ trợ file: {file_name}")
        return

    output_path = get_output_path_for_source(file_path)

    if output_path.exists() and not force:
        print(f"[SKIP] Output đã tồn tại, không OCR lại: {output_path}")
        print("       Dùng thêm --force nếu cần xử lý lại file này.")
        return

    try:
        print(f"\nĐang xử lý: {file_path}")

        if ext in SUPPORTED_PDF:
            content, metadata = extract_pdf_hybrid(str(file_path))
            save_markdown_output(
                source_path=file_path,
                content=content,
                metadata=metadata,
                extraction_mode="hybrid_pymupdf_easyocr",
            )
        elif ext in SUPPORTED_IMAGES:
            content, metadata = extract_image_file(str(file_path))
            save_markdown_output(
                source_path=file_path,
                content=content,
                metadata=metadata,
                extraction_mode="easyocr_image",
            )

    except Exception as exc:
        print(f"[ERROR] Lỗi khi xử lý {file_path}: {exc}")


def process_path(input_path: str | Path, force: bool = False) -> None:
    """Xử lý một file cụ thể hoặc toàn bộ file trong một folder."""

    input_path = Path(input_path)

    if input_path.is_file():
        print(f"[DEBUG] Chế độ xử lý 1 file: {input_path.resolve()}")
        process_one_file(input_path, force=force)
        return

    if input_path.is_dir():
        print(f"[DEBUG] Chế độ xử lý folder: {input_path.resolve()}")
        all_files = [path for path in input_path.rglob("*") if path.is_file()]
        print(f"[DEBUG] Số file tìm thấy: {len(all_files)}")

        if not all_files:
            print("[INFO] Không tìm thấy file nào trong folder.")
            return

        for file_path in all_files:
            process_one_file(file_path, force=force)

        print("\nHoàn tất xử lý toàn bộ file trong folder.")
        return

    print(f"[ERROR] Đường dẫn không hợp lệ: {input_path}")
