"""
main.py
Hàm chính để chạy pipeline OCR EasyOCR + PyMuPDF.

Ví dụ:
    python main.py
    python main.py "input/file.pdf"
    python main.py "input" --force
"""

from __future__ import annotations

import argparse
from pathlib import Path

from config import IMAGE_TEMP_FOLDER, INPUT_FOLDER, OUTPUT_FOLDER, PROJECT_ROOT, ensure_output_dirs
from file_processor import process_path


def resolve_input_path(path_value: str) -> Path:
    """Tìm đường dẫn input theo terminal hiện tại, sau đó fallback theo PROJECT_ROOT."""

    input_path = Path(path_value)

    if not input_path.exists() and not input_path.is_absolute():
        project_relative_path = PROJECT_ROOT / input_path
        if project_relative_path.exists():
            input_path = project_relative_path

    return input_path


def main() -> None:
    """Hàm chính: đọc tham số dòng lệnh và xử lý file/folder."""

    ensure_output_dirs()

    parser = argparse.ArgumentParser(
        description="Trích xuất text / OCR từ PDF hoặc ảnh sang Markdown."
    )

    parser.add_argument(
        "path",
        nargs="?",
        default=str(INPUT_FOLDER),
        help="Đường dẫn file cụ thể hoặc folder. Mặc định là folder input.",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Xử lý lại dù file output đã tồn tại.",
    )

    args = parser.parse_args()
    input_path = resolve_input_path(args.path)

    if not input_path.exists():
        print(f"[ERROR] Không tìm thấy đường dẫn: {input_path}")
        return

    print(f"[DEBUG] Project root: {PROJECT_ROOT}")
    print(f"[DEBUG] Output folder: {OUTPUT_FOLDER}")
    print(f"[DEBUG] Temp images folder: {IMAGE_TEMP_FOLDER}")

    process_path(input_path, force=args.force)


if __name__ == "__main__":
    main()
