"""
table_utils.py
Xử lý bảng Markdown, bảng từ PyMuPDF và bảng từ bbox EasyOCR.
"""

from __future__ import annotations

from typing import Any
from common_fix import clean_line, clean_text


def escape_md_cell(value: Any) -> str:
    """Làm sạch nội dung ô trong bảng Markdown."""

    if value is None:
        return ""

    value = str(value)
    value = value.replace("\n", "<br>")
    value = value.replace("|", "\\|")
    value = clean_line(value)
    return value.strip()


def table_to_markdown(table_data: list[list[Any]]) -> str:
    """Chuyển dữ liệu bảng dạng list[list] thành Markdown table."""

    if not table_data:
        return ""

    cleaned_rows: list[list[str]] = []

    for row in table_data:
        if row is None:
            continue

        cleaned_row = [escape_md_cell(cell) for cell in row]

        if any(cell.strip() for cell in cleaned_row):
            cleaned_rows.append(cleaned_row)

    if not cleaned_rows:
        return ""

    max_cols = max(len(row) for row in cleaned_rows)
    normalized_rows = []

    for row in cleaned_rows:
        normalized_rows.append(row + [""] * (max_cols - len(row)))

    if len(normalized_rows) == 1:
        header = [f"Cột {i + 1}" for i in range(max_cols)]
        body = normalized_rows
    else:
        header = normalized_rows[0]
        body = normalized_rows[1:]

    md_lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---"] * max_cols) + " |",
    ]

    for row in body:
        md_lines.append("| " + " | ".join(row) + " |")

    return "\n".join(md_lines)


def bbox_intersects(bbox_1: tuple[float, float, float, float], bbox_2: tuple[float, float, float, float]) -> bool:
    """Kiểm tra 2 bbox có giao nhau không."""

    x0, y0, x1, y1 = bbox_1
    a0, b0, a1, b1 = bbox_2
    return not (x1 < a0 or a1 < x0 or y1 < b0 or b1 < y0)


def extract_tables_from_pdf_page(page: Any) -> tuple[list[str], list[tuple[float, float, float, float]]]:
    """Dùng PyMuPDF để tìm bảng trong trang PDF copy được text."""

    markdown_tables: list[str] = []
    table_bboxes: list[tuple[float, float, float, float]] = []

    try:
        tables = page.find_tables()

        for table_index, table in enumerate(tables):
            table_data = table.extract()
            table_md = table_to_markdown(table_data)

            if table_md:
                markdown_tables.append(f"### Bảng {table_index + 1}\n\n{table_md}")

                if hasattr(table, "bbox") and table.bbox:
                    table_bboxes.append(tuple(table.bbox))

    except Exception as exc:
        print(f"[WARN] Không trích xuất được bảng bằng PyMuPDF: {exc}")

    return markdown_tables, table_bboxes


def extract_text_outside_tables(page: Any, table_bboxes: list[tuple[float, float, float, float]]) -> str:
    """Lấy text ngoài vùng bảng để tránh bị lặp nội dung bảng."""

    blocks = page.get_text("blocks")
    outside_text_parts: list[str] = []

    for block in blocks:
        if len(block) < 5:
            continue

        x0, y0, x1, y1, text = block[:5]
        block_bbox = (x0, y0, x1, y1)

        inside_table = any(bbox_intersects(block_bbox, table_bbox) for table_bbox in table_bboxes)

        if not inside_table:
            text = clean_text(text)
            if text:
                outside_text_parts.append(text)

    return "\n".join(outside_text_parts)


def get_ocr_box_info(item: Any) -> dict[str, float | str]:
    """Lấy thông tin bbox từ EasyOCR item detail=1."""

    box = item[0]
    text = clean_line(item[1])

    xs = [point[0] for point in box]
    ys = [point[1] for point in box]

    x_min = min(xs)
    x_max = max(xs)
    y_min = min(ys)
    y_max = max(ys)

    return {
        "text": text,
        "x_min": x_min,
        "x_max": x_max,
        "y_min": y_min,
        "y_max": y_max,
        "x_center": (x_min + x_max) / 2,
        "y_center": (y_min + y_max) / 2,
        "height": y_max - y_min,
    }


def group_ocr_boxes_into_rows(boxes: list[dict[str, float | str]], y_threshold: float = 18) -> list[list[dict[str, float | str]]]:
    """Gom OCR box thành từng dòng dựa vào tọa độ y."""

    if not boxes:
        return []

    boxes = sorted(boxes, key=lambda b: float(b["y_center"]))
    rows: list[list[dict[str, float | str]]] = []

    for box in boxes:
        placed = False

        for row in rows:
            row_y = sum(float(item["y_center"]) for item in row) / len(row)

            if abs(float(box["y_center"]) - row_y) <= y_threshold:
                row.append(box)
                placed = True
                break

        if not placed:
            rows.append([box])

    for row in rows:
        row.sort(key=lambda b: float(b["x_center"]))

    return rows


def detect_column_centers(rows: list[list[dict[str, float | str]]], x_threshold: float = 45) -> list[float]:
    """Tìm các cột dựa trên vị trí x của OCR boxes."""

    x_centers: list[float] = []

    for row in rows:
        for box in row:
            x_centers.append(float(box["x_center"]))

    if not x_centers:
        return []

    columns: list[list[float]] = []

    for x in sorted(x_centers):
        placed = False

        for col in columns:
            col_avg = sum(col) / len(col)

            if abs(x - col_avg) <= x_threshold:
                col.append(x)
                placed = True
                break

        if not placed:
            columns.append([x])

    return sorted(sum(col) / len(col) for col in columns)


def nearest_column_index(x: float, column_centers: list[float]) -> int:
    """Tìm cột gần nhất với tọa độ x."""

    if not column_centers:
        return 0

    distances = [abs(x - col_x) for col_x in column_centers]
    return distances.index(min(distances))


def _filter_ocr_boxes_for_table(ocr_results: list[Any], min_confidence: float | None = None) -> list[dict[str, float | str]]:
    """Lọc OCR result thành danh sách bbox hợp lệ để xét bảng."""

    boxes = []

    for item in ocr_results:
        if len(item) < 2:
            continue

        text = clean_line(item[1])

        if not text:
            continue

        if min_confidence is not None and len(item) >= 3:
            conf = item[2]
            if conf is not None and conf < min_confidence:
                continue

        boxes.append(get_ocr_box_info(item))

    return boxes


def ocr_results_to_markdown_table(ocr_results: list[Any]) -> str:
    """Dựng bảng Markdown từ kết quả EasyOCR detail=1."""

    boxes = _filter_ocr_boxes_for_table(ocr_results)

    if len(boxes) < 4:
        return ""

    avg_height = sum(float(b["height"]) for b in boxes) / len(boxes)
    y_threshold = max(12, avg_height * 0.8)
    rows = group_ocr_boxes_into_rows(boxes, y_threshold=y_threshold)

    if len(rows) < 2:
        return ""

    column_centers = detect_column_centers(rows, x_threshold=50)

    if len(column_centers) < 2:
        return ""

    table_data: list[list[str]] = []

    for row in rows:
        cells = [""] * len(column_centers)

        for box in row:
            col_index = nearest_column_index(float(box["x_center"]), column_centers)
            text = str(box["text"])
            cells[col_index] = f"{cells[col_index]} {text}".strip() if cells[col_index] else text

        table_data.append(cells)

    return table_to_markdown(table_data)


def looks_like_table_from_ocr(ocr_results: list[Any]) -> bool:
    """Nhận diện bảng từ OCR theo cách chặt để tránh biến văn bản thường thành bảng."""

    boxes = _filter_ocr_boxes_for_table(ocr_results, min_confidence=0.25)

    if len(boxes) < 12:
        return False

    avg_height = sum(float(b["height"]) for b in boxes) / len(boxes)
    y_threshold = max(12, avg_height * 0.8)
    rows = group_ocr_boxes_into_rows(boxes, y_threshold=y_threshold)

    if len(rows) < 4:
        return False

    multi_box_rows = [row for row in rows if len(row) >= 2]

    if len(multi_box_rows) < 4:
        return False

    column_centers = detect_column_centers(multi_box_rows, x_threshold=45)

    if len(column_centers) < 2:
        return False

    table_like_rows = 0

    for row in multi_box_rows:
        used_cols = set()

        for box in row:
            distances = [abs(float(box["x_center"]) - col_x) for col_x in column_centers]
            nearest_distance = min(distances)
            nearest_index = distances.index(nearest_distance)

            if nearest_distance <= 45:
                used_cols.add(nearest_index)

        if len(used_cols) >= 2:
            table_like_rows += 1

    if table_like_rows < 4:
        return False

    ratio = table_like_rows / max(1, len(rows))
    return ratio >= 0.45
