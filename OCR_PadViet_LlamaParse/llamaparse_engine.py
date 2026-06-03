"""
llamaparse_engine.py

Module tích hợp LlamaParse v2 vào pipeline OCR hiện có.
- Dùng khi PDF scan / bảng / biểu mẫu / layout phức tạp.
- Trả về Markdown có page marker để đưa tiếp qua clean/chunking/RAG.

Bản SAFE cập nhật:
- Mặc định KHÔNG bật aggressive_table_extraction để tránh biến văn bản thường thành bảng.
- Prompt ràng buộc rõ: chỉ tạo Markdown table khi trang thật sự có bảng/cell/đường kẻ.
- Có hậu xử lý loại bỏ một số bảng giả do LlamaParse tạo từ đoạn văn bản thường.

Cài đặt:
    pip install "llama-cloud>=2.1" python-dotenv

Thiết lập API key trên PowerShell:
    setx LLAMA_CLOUD_API_KEY "llx-..."
    # đóng/mở lại PowerShell sau khi setx
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional


Tier = Literal["fast", "cost_effective", "agentic", "agentic_plus"]
ChartMode = Literal["efficient", "agentic", "agentic_plus"]


@dataclass
class LlamaParseConfig:
    """Cấu hình parse cho LlamaParse v2."""

    tier: Tier = "agentic"
    version: str = "latest"
    language: str = "vi"

    # Chỉ parse một đoạn trang để tiết kiệm credits. LlamaParse v2 dùng page 1-based.
    page_start: Optional[int] = None
    page_end: Optional[int] = None

    # Bảng / hình / layout
    output_tables_as_markdown: bool = True
    merge_continued_tables: bool = True
    export_tables_as_xlsx: bool = False
    preserve_spatial_text: bool = False
    save_images: bool = False
    specialized_chart_parsing: Optional[ChartMode] = None

    # SAFE DEFAULT: False để tránh nhầm đoạn văn bản thẳng hàng thành bảng.
    # Chỉ bật True cho trang thật sự nhiều bảng/lưu đồ phức tạp.
    aggressive_table_extraction: bool = False

    # Nếu True, hậu xử lý sẽ cố chuyển các markdown table giả thành text thường.
    repair_false_tables: bool = True

    # Cache và custom prompt
    disable_cache: bool = False
    custom_prompt: Optional[str] = None

    # Timeout an toàn cho file nhiều trang
    base_timeout_seconds: int = 300
    extra_timeout_per_page_seconds: int = 30


def _validate_file(input_path: str | Path) -> Path:
    """Kiểm tra file input có tồn tại không."""
    path = Path(input_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {path}")
    if not path.is_file():
        raise ValueError(f"Đường dẫn không phải file: {path}")
    return path


def _build_target_pages(page_start: Optional[int], page_end: Optional[int]) -> Optional[str]:
    """Tạo chuỗi page_ranges.target_pages cho LlamaParse v2, dùng page 1-based."""
    if page_start is None and page_end is None:
        return None

    start = page_start or 1
    end = page_end or start

    if start < 1 or end < 1:
        raise ValueError("LlamaParse v2 dùng số trang bắt đầu từ 1. page_start/page_end phải >= 1.")
    if end < start:
        raise ValueError("page_end phải >= page_start.")

    return str(start) if start == end else f"{start}-{end}"


def _default_ctu_prompt() -> str:
    """Prompt để LlamaParse giữ cấu trúc văn bản hành chính CTU và không tạo bảng giả."""
    return (
        "Đây là văn bản hành chính, quy định, quy trình, thủ tục hoặc biểu mẫu của Trường Đại học Cần Thơ. "
        "Hãy giữ đúng tiếng Việt có dấu, số hiệu văn bản, ngày tháng, đơn vị ban hành, tiêu đề, mục Chương/Điều/Khoản/Điểm, danh sách đánh số. "
        "Không tự tóm tắt nội dung. Xuất Markdown sạch để dùng cho RAG. "
        "QUY TẮC BẢNG RẤT QUAN TRỌNG: Chỉ tạo Markdown table khi trên trang thật sự có bảng rõ ràng, có đường kẻ/cell/cột/hàng hoặc header cột như Bước, Lưu đồ, Nội dung công việc, Người thực hiện, Thời gian, Ghi chú. "
        "Không được biến tiêu đề, mục 1/1.1/a/b/c, hoặc đoạn văn bản thường thành bảng. "
        "Nếu chỉ là văn bản bình thường, hãy giữ thành heading, paragraph và bullet list."
    )


def _build_parse_kwargs(file_id: str, cfg: LlamaParseConfig) -> dict:
    """Chuyển dataclass config thành kwargs cho client.parsing.parse()."""
    kwargs: dict = {
        "file_id": file_id,
        "tier": cfg.tier,
        "version": cfg.version,
        "expand": ["markdown", "text", "items", "metadata"],
        "processing_options": {
            "ocr_parameters": {"languages": [cfg.language]},
            "aggressive_table_extraction": cfg.aggressive_table_extraction,
        },
        "output_options": {
            "markdown": {
                "tables": {
                    "output_tables_as_markdown": cfg.output_tables_as_markdown,
                    "merge_continued_tables": cfg.merge_continued_tables,
                }
            },
            "extract_printed_page_number": True,
        },
        "processing_control": {
            "timeouts": {
                "base_in_seconds": cfg.base_timeout_seconds,
                "extra_time_per_page_in_seconds": cfg.extra_timeout_per_page_seconds,
            },
            "job_failure_conditions": {"allowed_page_failure_ratio": 0.05},
        },
        "disable_cache": cfg.disable_cache,
    }

    target_pages = _build_target_pages(cfg.page_start, cfg.page_end)
    if target_pages:
        kwargs["page_ranges"] = {"target_pages": target_pages}

    # Spatial text giúp giữ bố cục bằng khoảng trắng; hữu ích cho form/phiếu/bảng khó.
    if cfg.preserve_spatial_text:
        kwargs["output_options"]["spatial_text"] = {
            "preserve_layout_alignment_across_pages": True,
            "preserve_very_small_text": True,
            "do_not_unroll_columns": False,
        }

    if cfg.export_tables_as_xlsx:
        kwargs["output_options"]["tables_as_spreadsheet"] = {"enable": True}
        kwargs["expand"].append("xlsx_content_metadata")

    if cfg.save_images:
        kwargs["output_options"]["images_to_save"] = ["screenshot", "embedded", "layout"]
        kwargs["expand"].append("images_content_metadata")

    if cfg.specialized_chart_parsing:
        kwargs["processing_options"]["specialized_chart_parsing"] = cfg.specialized_chart_parsing

    # custom_prompt chỉ dùng cho cost_effective/agentic/agentic_plus, không dùng fast.
    prompt = cfg.custom_prompt or _default_ctu_prompt()
    if cfg.tier != "fast" and prompt:
        kwargs["agentic_options"] = {"custom_prompt": prompt}

    # Loại bỏ expand trùng lặp nhưng giữ thứ tự.
    kwargs["expand"] = list(dict.fromkeys(kwargs["expand"]))
    return kwargs


def _join_pages_as_markdown(result) -> str:
    """Ghép Markdown theo từng trang và thêm page marker cho citation trong RAG."""
    if not getattr(result, "markdown", None) or not getattr(result.markdown, "pages", None):
        raise RuntimeError("LlamaParse không trả về markdown.pages. Hãy kiểm tra expand=['markdown'] hoặc job parse.")

    blocks: list[str] = []
    for idx, page in enumerate(result.markdown.pages, start=1):
        page_no = getattr(page, "page", None) or getattr(page, "page_number", None) or idx
        page_md = getattr(page, "markdown", "") or ""
        page_md = page_md.strip()
        blocks.append(f"<!-- page: {page_no} -->\n\n{page_md}".strip())

    return "\n\n".join(blocks).strip() + "\n"


_TABLE_HEADER_HINTS = {
    "bước", "lưu đồ", "nội dung", "công việc", "người", "thực hiện", "thời gian",
    "ghi chú", "đơn vị", "phối hợp", "biểu mẫu", "minh chứng", "hồ sơ",
}


def _is_table_separator(line: str) -> bool:
    """Nhận diện dòng phân cách của markdown table."""
    return bool(re.match(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{1,}:?\s*)+\|?\s*$", line))


def _split_table_row(line: str) -> list[str]:
    """Tách cell của một dòng markdown table."""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [re.sub(r"\s+", " ", c).strip(" *") for c in s.split("|")]


def _looks_like_false_table(table_lines: list[str]) -> bool:
    """
    Heuristic nhận diện bảng giả do OCR/parser tạo nhầm từ văn bản thường.

    Không chuyển các bảng thật nếu có header/cột rõ như Bước, Lưu đồ, Nội dung công việc...
    Chủ yếu bắt trường hợp 1-2 cột, nhiều cell rỗng, dòng dạng heading/mục văn bản.
    """
    data_rows = [ln for ln in table_lines if "|" in ln and not _is_table_separator(ln)]
    if not data_rows:
        return False

    rows = [_split_table_row(ln) for ln in data_rows]
    max_cols = max((len(r) for r in rows), default=0)
    all_text = " ".join(" ".join(r) for r in rows).lower()

    # Nếu có dấu hiệu bảng thật thì không động vào.
    if any(h in all_text for h in _TABLE_HEADER_HINTS):
        return False

    non_empty_cells = [c for r in rows for c in r if c]
    empty_cells = [c for r in rows for c in r if not c]
    empty_ratio = len(empty_cells) / max(sum(len(r) for r in rows), 1)

    first_cells = [r[0] for r in rows if r]
    section_like = sum(
        1 for c in first_cells
        if re.match(r"^(\d+(\.\d+)*\.?\s+|[a-zA-Zà-ỹ]\.|[IVXLCDM]+\.|I+\.|V+\.)", c.strip(), flags=re.I)
    )

    # Bảng giả thường rất ít cột, nhiều ô rỗng hoặc ô cột phải chỉ là 1-2 từ bị tách sai.
    short_right_cells = 0
    right_cells = []
    for r in rows:
        if len(r) > 1:
            right_cells.extend(r[1:])
    for c in right_cells:
        if c and len(c.split()) <= 2:
            short_right_cells += 1
    short_right_ratio = short_right_cells / max(len([c for c in right_cells if c]), 1)

    return (
        max_cols <= 2
        and (
            empty_ratio >= 0.35
            or section_like >= 1
            or short_right_ratio >= 0.7
        )
    )


def _table_to_plain_text(table_lines: list[str]) -> list[str]:
    """Chuyển bảng giả thành các dòng text thường bằng cách ghép cell không rỗng."""
    plain: list[str] = []
    for ln in table_lines:
        if _is_table_separator(ln):
            continue
        cells = [c for c in _split_table_row(ln) if c]
        if not cells:
            continue
        plain.append(" ".join(cells).strip())
    return plain


def repair_false_markdown_tables(text: str) -> str:
    """Loại bỏ các markdown table giả nhưng giữ bảng thật."""
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if "|" not in line or line.strip().startswith("<!--"):
            out.append(line)
            i += 1
            continue

        block: list[str] = []
        j = i
        while j < len(lines) and ("|" in lines[j] or _is_table_separator(lines[j]) or not lines[j].strip()):
            if not lines[j].strip() and block:
                break
            if lines[j].strip():
                block.append(lines[j])
            j += 1

        if len(block) >= 2 and any(_is_table_separator(ln) for ln in block) and _looks_like_false_table(block):
            out.extend(_table_to_plain_text(block))
            i = j
        else:
            out.append(line)
            i += 1

    return "\n".join(out)


def normalize_llamaparse_markdown(markdown: str, repair_false_tables: bool = True) -> str:
    """Hậu xử lý nhẹ sau LlamaParse để hợp với pipeline CTU."""
    text = markdown.replace("\r\n", "\n").replace("\r", "\n")

    if repair_false_tables:
        text = repair_false_markdown_tables(text)

    # Chuẩn hóa khoảng trắng nhưng không phá markdown table thật.
    lines: list[str] = []
    for line in text.split("\n"):
        if "|" in line and re.match(r"^\s*\|?.+\|", line):
            lines.append(line.rstrip())
        else:
            line = re.sub(r"[ \t]+", " ", line).strip()
            lines.append(line)

    text = "\n".join(lines)

    # Chuẩn hóa tiêu đề hành chính phổ biến nếu LlamaParse chưa gắn heading.
    heading_patterns = [
        r"^(CHƯƠNG\s+[IVXLCDM]+\b.*)$",
        r"^(Chương\s+[IVXLCDM]+\b.*)$",
        r"^(Điều\s+\d+\.?\s+.*)$",
        r"^(PHỤ LỤC\s+.*)$",
        r"^(QUYẾT ĐỊNH\b.*)$",
        r"^(QUY ĐỊNH\b.*)$",
        r"^(QUY TRÌNH\b.*)$",
    ]

    normalized_lines: list[str] = []
    in_table = False
    for line in text.split("\n"):
        stripped = line.strip()
        if "|" in stripped and re.match(r"^\|?.+\|", stripped):
            in_table = True
        elif stripped == "":
            in_table = False

        if not stripped or stripped.startswith("#") or stripped.startswith("<!-- page:") or in_table:
            normalized_lines.append(line)
            continue
        if any(re.match(p, stripped) for p in heading_patterns):
            normalized_lines.append(f"## {stripped}")
        else:
            normalized_lines.append(line)

    text = "\n".join(normalized_lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def parse_with_llamaparse(input_path: str | Path, cfg: Optional[LlamaParseConfig] = None) -> str:
    """Upload file lên LlamaCloud, chạy LlamaParse và trả về Markdown."""
    cfg = cfg or LlamaParseConfig()
    file_path = _validate_file(input_path)

    if not os.getenv("LLAMA_CLOUD_API_KEY"):
        raise EnvironmentError(
            "Thiếu biến môi trường LLAMA_CLOUD_API_KEY. "
            "PowerShell: setx LLAMA_CLOUD_API_KEY \"llx-...\" rồi mở lại terminal."
        )

    try:
        from llama_cloud import LlamaCloud
    except ImportError as exc:
        raise ImportError(
            "Chưa cài llama-cloud. Hãy chạy: pip install \"llama-cloud>=2.1\" python-dotenv"
        ) from exc

    client = LlamaCloud()
    uploaded_file = client.files.create(file=str(file_path), purpose="parse")
    parse_kwargs = _build_parse_kwargs(file_id=uploaded_file.id, cfg=cfg)

    result = client.parsing.parse(**parse_kwargs)
    markdown = _join_pages_as_markdown(result)
    return normalize_llamaparse_markdown(markdown, repair_false_tables=cfg.repair_false_tables)


def save_llamaparse_markdown(
    input_path: str | Path,
    output_path: str | Path,
    cfg: Optional[LlamaParseConfig] = None,
) -> Path:
    """Parse file bằng LlamaParse và lưu Markdown ra output_path."""
    markdown = parse_with_llamaparse(input_path, cfg)
    out = Path(output_path).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(markdown, encoding="utf-8")
    return out
