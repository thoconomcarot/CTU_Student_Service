"""
main_table_safe.py

CLI chính cho pipeline TableSafe.
Dùng file này khi muốn tránh lỗi PyMuPDF tự tạo bảng giả:
- Trang text thường: PyMuPDF text-only / Paddle+VietOCR local.
- Trang có bảng/lưu đồ thật: LlamaParse.

Ví dụ:
    python main_table_safe.py "file.pdf" --page-start 1 --page-end 4
    python main_table_safe.py "file.pdf" --table-pages 4,6,8-10
"""

from __future__ import annotations

import argparse
from pathlib import Path

from hybrid_page_router import run_table_safe_pdf


def build_parser() -> argparse.ArgumentParser:
    """Tạo parser đọc tham số dòng lệnh cho pipeline TableSafe."""
    parser = argparse.ArgumentParser(
        description="TableSafe OCR/parser: local text/OCR cho văn bản thường, LlamaParse cho trang bảng/lưu đồ."
    )
    parser.add_argument("input", help="Đường dẫn file PDF cần xử lý")
    parser.add_argument("-o", "--output", default=None, help="File Markdown output. Mặc định: output/<ten_file>_structured.md")
    parser.add_argument(
        "--engine",
        choices=["auto-page", "local", "llamaparse"],
        default="auto-page",
        help="auto-page: tự chọn từng trang; local: không dùng LlamaParse; llamaparse: dùng LlamaParse toàn bộ",
    )
    parser.add_argument("--page-start", type=int, default=None, help="Trang bắt đầu, 1-based")
    parser.add_argument("--page-end", type=int, default=None, help="Trang kết thúc, 1-based")
    parser.add_argument(
        "--table-pages",
        default=None,
        help="Chỉ định thủ công trang dùng LlamaParse, ví dụ: 4,6,8-10. Bỏ trống thì tự detect.",
    )
    parser.add_argument(
        "--llama-tier",
        choices=["fast", "cost_effective", "agentic", "agentic_plus"],
        default="agentic",
        help="Tier LlamaParse cho trang bảng/lưu đồ",
    )
    parser.add_argument("--xlsx", action="store_true", help="Yêu cầu LlamaParse xuất metadata bảng dạng XLSX nếu SDK hỗ trợ")
    parser.add_argument("--spatial", action="store_true", help="Bật spatial text cho trang bảng/form khó")
    parser.add_argument("--disable-cache", action="store_true", help="Không dùng cache của LlamaParse")
    parser.add_argument(
        "--aggressive-tables",
        action="store_true",
        help="Bật aggressive table extraction của LlamaParse. Chỉ dùng khi trang thật sự là bảng/lưu đồ phức tạp.",
    )
    parser.add_argument("--no-repair-false-tables", action="store_true", help="Tắt hậu xử lý sửa bảng giả của LlamaParse")
    return parser


def default_output_path(input_path: Path) -> Path:
    """Tạo đường dẫn output mặc định theo tên file input."""
    return Path("output") / f"{input_path.stem}_structured.md"


def main() -> None:
    """Entry point CLI."""
    args = build_parser().parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else default_output_path(input_path)

    out = run_table_safe_pdf(
        input_path=input_path,
        output_path=output_path,
        engine=args.engine,
        page_start=args.page_start,
        page_end=args.page_end,
        manual_table_pages=args.table_pages,
        llama_tier=args.llama_tier,
        export_tables_as_xlsx=args.xlsx,
        preserve_spatial_text=args.spatial,
        disable_cache=args.disable_cache,
        aggressive_tables=args.aggressive_tables,
        repair_false_tables=not args.no_repair_false_tables,
    )
    print(f"[OK] Đã tạo Markdown TableSafe: {out.resolve()}")


if __name__ == "__main__":
    main()
