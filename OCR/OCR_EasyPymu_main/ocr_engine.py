"""
ocr_engine.py
Các hàm OCR ảnh và đọc kết quả EasyOCR.
"""

from __future__ import annotations

from typing import Any
from common_fix import clean_line, clean_text
from config import OCR_LANGS, USE_GPU

_reader = None


def get_easyocr_reader():
    """Khởi tạo EasyOCR Reader theo kiểu lazy để import module không bị nặng."""

    global _reader

    if _reader is None:
        import easyocr
        _reader = easyocr.Reader(OCR_LANGS, gpu=USE_GPU)

    return _reader


def easyocr_result_to_text(ocr_results: list[Any]) -> str:
    """Chuyển kết quả EasyOCR detail=1 thành text thường."""

    lines: list[str] = []

    for item in ocr_results:
        if len(item) >= 2:
            text = clean_line(item[1])
            if text:
                lines.append(text)

    return "\n".join(lines)


def ocr_image_plain(image_path: str) -> str:
    """OCR ảnh để lấy text thường."""

    reader = get_easyocr_reader()
    results = reader.readtext(image_path, detail=0, paragraph=True)
    text = "\n".join(results)
    return clean_text(text)


def ocr_image_detail(image_path: str) -> list[Any]:
    """OCR ảnh lấy cả text và tọa độ bbox, dùng cho dựng bảng."""

    reader = get_easyocr_reader()
    return reader.readtext(image_path, detail=1, paragraph=False)
