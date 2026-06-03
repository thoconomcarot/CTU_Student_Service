"""
main_hybrid_llama.py

CLI mới để chạy hybrid: local Paddle+VietOCR hoặc LlamaParse.
Đặt file này cùng thư mục với source cũ, rồi chạy từ terminal.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from hybrid_router import run_hybrid_parse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hybrid OCR/parser: Paddle+VietOCR local + LlamaParse cloud")
    parser.add_argument("input", help="Đường dẫn PDF/ảnh/DOCX/PPTX/XLSX cần xử lý")
    parser.add_argument("-o", "--output", default=None, help="File Markdown output")
    parser.add_argument("--engine", choices=["auto", "local", "llamaparse"], default="auto")
    parser.add_argument("--page-start", type=int, default=None, help="Trang bắt đầu, dùng số trang 1-based")
    parser.add_argument("--page-end", type=int, default=None, help="Trang kết thúc, dùng số trang 1-based")
    parser.add_argument(
        "--llama-tier",
        choices=["fast", "cost_effective", "agentic", "agentic_plus"],
        default="agentic",
        help="Tier của LlamaParse khi dùng engine llamaparse/auto",
    )
    parser.add_argument("--xlsx", action="store_true", help="Yêu cầu LlamaParse xuất bảng dạng spreadsheet metadata")
    parser.add_argument("--spatial", action="store_true", help="Bật spatial text để giữ bố cục form/bảng/cột")
    parser.add_argument("--disable-cache", action="store_true", help="Không dùng cache LlamaParse")
    parser.add_argument("--aggressive-tables", action="store_true", help="Bật aggressive table extraction của LlamaParse; chỉ dùng cho trang thật sự nhiều bảng/lưu đồ")
    parser.add_argument("--no-repair-false-tables", action="store_true", help="Tắt hậu xử lý sửa bảng giả do LlamaParse tạo nhầm")
    return parser


def default_output_path(input_path: Path) -> Path:
    return Path("output") / f"{input_path.stem}_structured.md"


def main() -> None:
    args = build_parser().parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else default_output_path(input_path)

    out = run_hybrid_parse(
        input_path=input_path,
        output_path=output_path,
        engine=args.engine,
        page_start=args.page_start,
        page_end=args.page_end,
        llama_tier=args.llama_tier,
        export_tables_as_xlsx=args.xlsx,
        preserve_spatial_text=args.spatial,
        disable_cache=args.disable_cache,
        aggressive_tables=args.aggressive_tables,
        repair_false_tables=not args.no_repair_false_tables,
    )

    print(f"[OK] Đã tạo Markdown: {out.resolve()}")


if __name__ == "__main__":
    main()
