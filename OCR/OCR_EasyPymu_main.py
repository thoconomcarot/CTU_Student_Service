import os
import math
import cv2
import re
import argparse
from pathlib import Path
from datetime import datetime

import fitz  # PyMuPDF
import easyocr

# =========================
# CẤU HÌNH
# =========================

# Luôn lấy đường dẫn theo thư mục gốc project, không phụ thuộc vào vị trí đang chạy terminal.
# Trường hợp file code nằm trong folder OCR:
#   SCRIPT_DIR   = D:/Code/CTU_Student_Service/OCR
#   PROJECT_ROOT = D:/Code/CTU_Student_Service
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent if SCRIPT_DIR.name.lower() == "ocr" else SCRIPT_DIR

input_folder = PROJECT_ROOT / "input"
output_folder = PROJECT_ROOT / "output"
image_temp_folder = output_folder / "temp_images"

output_folder.mkdir(parents=True, exist_ok=True)
image_temp_folder.mkdir(parents=True, exist_ok=True)

# Ngôn ngữ OCR: tiếng Việt + tiếng Anh
reader = easyocr.Reader(["vi", "en"], gpu=False)

# Nếu trang có số ký tự ít hơn mức này thì xem như cần OCR
MIN_TEXT_LENGTH = 30

# DPI khi chuyển PDF scan sang ảnh, 200 đỡ nặng máy hơn 300
RENDER_DPI = 200


# =========================
# HÀM LÀM SẠCH TEXT
# =========================


def clean_text(text):
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_line(line):
    line = line.strip()
    line = re.sub(r"\s+", " ", line)
    return line


# =========================
# HÀM XỬ LÝ BẢNG MARKDOWN
# =========================


def escape_md_cell(value):
    """
    Làm sạch nội dung ô trong bảng Markdown.
    """
    if value is None:
        return ""

    value = str(value)
    value = value.replace("\n", "<br>")
    value = value.replace("|", "\\|")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def table_to_markdown(table_data):
    """
    Chuyển dữ liệu bảng dạng list[list] thành Markdown table.
    """

    if not table_data:
        return ""

    # Xóa các dòng rỗng hoàn toàn
    cleaned_rows = []
    for row in table_data:
        if row is None:
            continue

        cleaned_row = [escape_md_cell(cell) for cell in row]

        if any(cell.strip() for cell in cleaned_row):
            cleaned_rows.append(cleaned_row)

    if not cleaned_rows:
        return ""

    # Chuẩn hóa số cột
    max_cols = max(len(row) for row in cleaned_rows)

    normalized_rows = []
    for row in cleaned_rows:
        row = row + [""] * (max_cols - len(row))
        normalized_rows.append(row)

    # Nếu bảng chỉ có 1 dòng thì vẫn tạo header tạm
    if len(normalized_rows) == 1:
        header = [f"Cột {i + 1}" for i in range(max_cols)]
        body = normalized_rows
    else:
        header = normalized_rows[0]
        body = normalized_rows[1:]

    md_lines = []

    md_lines.append("| " + " | ".join(header) + " |")
    md_lines.append("| " + " | ".join(["---"] * max_cols) + " |")

    for row in body:
        md_lines.append("| " + " | ".join(row) + " |")

    return "\n".join(md_lines)


def bbox_intersects(b1, b2):
    """
    Kiểm tra 2 bbox có giao nhau không.
    b = (x0, y0, x1, y1)
    """
    x0, y0, x1, y1 = b1
    a0, b0, a1, b1 = b2

    return not (x1 < a0 or a1 < x0 or y1 < b0 or b1 < y0)


def extract_tables_from_pdf_page(page):
    """
    Dùng PyMuPDF để tìm bảng trong trang PDF copy được text.
    Trả về:
    - markdown_tables: list[str]
    - table_bboxes: list[tuple]
    """

    markdown_tables = []
    table_bboxes = []

    try:
        tables = page.find_tables()

        for table_index, table in enumerate(tables):
            table_data = table.extract()
            table_md = table_to_markdown(table_data)

            if table_md:
                markdown_tables.append(f"### Bảng {table_index + 1}\n\n{table_md}")

                # Lưu vùng bbox của bảng để tránh lấy trùng text bảng
                if hasattr(table, "bbox") and table.bbox:
                    table_bboxes.append(tuple(table.bbox))

    except Exception as e:
        print(f"[WARN] Không trích xuất được bảng bằng PyMuPDF: {e}")

    return markdown_tables, table_bboxes


def extract_text_outside_tables(page, table_bboxes):
    """
    Lấy text ngoài vùng bảng để tránh bị lặp nội dung bảng.
    """

    blocks = page.get_text("blocks")
    outside_text_parts = []

    for block in blocks:
        if len(block) < 5:
            continue

        x0, y0, x1, y1, text = block[:5]
        block_bbox = (x0, y0, x1, y1)

        # Nếu block nằm trong bảng thì bỏ qua
        inside_table = False
        for table_bbox in table_bboxes:
            if bbox_intersects(block_bbox, table_bbox):
                inside_table = True
                break

        if not inside_table:
            text = clean_text(text)
            if text:
                outside_text_parts.append(text)

    return "\n".join(outside_text_parts)


def easyocr_result_to_text(ocr_results):
    """
    Chuyển kết quả EasyOCR detail=1 thành text thường.
    """
    lines = []

    for item in ocr_results:
        if len(item) >= 2:
            text = item[1]
            text = clean_line(text)
            if text:
                lines.append(text)

    return "\n".join(lines)


def get_ocr_box_info(item):
    """
    Lấy thông tin bbox từ EasyOCR item.
    item dạng:
    [
        [[x1,y1], [x2,y2], [x3,y3], [x4,y4]],
        text,
        confidence
    ]
    """

    box = item[0]
    text = clean_line(item[1])

    xs = [point[0] for point in box]
    ys = [point[1] for point in box]

    x_min = min(xs)
    x_max = max(xs)
    y_min = min(ys)
    y_max = max(ys)

    x_center = (x_min + x_max) / 2
    y_center = (y_min + y_max) / 2
    height = y_max - y_min

    return {
        "text": text,
        "x_min": x_min,
        "x_max": x_max,
        "y_min": y_min,
        "y_max": y_max,
        "x_center": x_center,
        "y_center": y_center,
        "height": height,
    }


def group_ocr_boxes_into_rows(boxes, y_threshold=18):
    """
    Gom các OCR box thành từng dòng dựa vào tọa độ y.
    """

    if not boxes:
        return []

    boxes = sorted(boxes, key=lambda b: b["y_center"])

    rows = []

    for box in boxes:
        placed = False

        for row in rows:
            row_y = sum(item["y_center"] for item in row) / len(row)

            if abs(box["y_center"] - row_y) <= y_threshold:
                row.append(box)
                placed = True
                break

        if not placed:
            rows.append([box])

    # Sắp xếp trong từng dòng theo trục x
    for row in rows:
        row.sort(key=lambda b: b["x_center"])

    return rows


def detect_column_centers(rows, x_threshold=45):
    """
    Tìm các cột dựa trên vị trí x của OCR boxes.
    """

    x_centers = []

    for row in rows:
        for box in row:
            x_centers.append(box["x_center"])

    if not x_centers:
        return []

    x_centers = sorted(x_centers)

    columns = []

    for x in x_centers:
        placed = False

        for col in columns:
            col_avg = sum(col) / len(col)

            if abs(x - col_avg) <= x_threshold:
                col.append(x)
                placed = True
                break

        if not placed:
            columns.append([x])

    column_centers = [sum(col) / len(col) for col in columns]
    column_centers = sorted(column_centers)

    return column_centers


def nearest_column_index(x, column_centers):
    """
    Tìm cột gần nhất với tọa độ x.
    """

    if not column_centers:
        return 0

    distances = [abs(x - col_x) for col_x in column_centers]
    return distances.index(min(distances))


def ocr_results_to_markdown_table(ocr_results):
    """
    Dựng bảng Markdown từ kết quả EasyOCR detail=1.
    Phù hợp với ảnh hoặc PDF scan có bảng.
    """

    boxes = []

    for item in ocr_results:
        if len(item) < 2:
            continue

        text = clean_line(item[1])

        if not text:
            continue

        boxes.append(get_ocr_box_info(item))

    if len(boxes) < 4:
        return ""

    avg_height = sum(b["height"] for b in boxes) / len(boxes)
    y_threshold = max(12, avg_height * 0.8)

    rows = group_ocr_boxes_into_rows(boxes, y_threshold=y_threshold)

    # Nếu ít hơn 2 dòng thì không xem là bảng
    if len(rows) < 2:
        return ""

    column_centers = detect_column_centers(rows, x_threshold=50)

    # Nếu ít hơn 2 cột thì không xem là bảng
    if len(column_centers) < 2:
        return ""

    table_data = []

    for row in rows:
        cells = [""] * len(column_centers)

        for box in row:
            col_index = nearest_column_index(box["x_center"], column_centers)

            if cells[col_index]:
                cells[col_index] += " " + box["text"]
            else:
                cells[col_index] = box["text"]

        table_data.append(cells)

    return table_to_markdown(table_data)


def looks_like_table_from_ocr(ocr_results):
    """
    Nhận diện bảng từ OCR theo cách chặt hơn.
    Chỉ xem là bảng nếu có nhiều dòng có cấu trúc cột lặp lại.
    Tránh lỗi văn bản thường bị biến thành bảng.
    """

    boxes = []

    for item in ocr_results:
        if len(item) < 2:
            continue

        text = clean_line(item[1])

        if not text:
            continue

        # Bỏ kết quả OCR quá yếu nếu EasyOCR có confidence
        if len(item) >= 3:
            conf = item[2]
            if conf is not None and conf < 0.25:
                continue

        boxes.append(get_ocr_box_info(item))

    # Ít box quá thì không đủ cơ sở xem là bảng
    if len(boxes) < 12:
        return False

    avg_height = sum(b["height"] for b in boxes) / len(boxes)
    y_threshold = max(12, avg_height * 0.8)

    rows = group_ocr_boxes_into_rows(boxes, y_threshold=y_threshold)

    # Bảng thật thường phải có nhiều dòng
    if len(rows) < 4:
        return False

    # Chỉ lấy các dòng có từ 2 cụm OCR trở lên
    multi_box_rows = [row for row in rows if len(row) >= 2]

    if len(multi_box_rows) < 4:
        return False

    # Tìm cột
    column_centers = detect_column_centers(multi_box_rows, x_threshold=45)

    if len(column_centers) < 2:
        return False

    table_like_rows = 0

    for row in multi_box_rows:
        used_cols = set()

        for box in row:
            distances = [abs(box["x_center"] - col_x) for col_x in column_centers]
            nearest_distance = min(distances)
            nearest_index = distances.index(nearest_distance)

            # Chỉ tính là thuộc cột nếu đủ gần trục cột
            if nearest_distance <= 45:
                used_cols.add(nearest_index)

        if len(used_cols) >= 2:
            table_like_rows += 1

    # Phải có ít nhất 4 dòng giống cấu trúc bảng
    if table_like_rows < 4:
        return False

    # Nếu chỉ vài dòng giống bảng nhưng cả trang chủ yếu là văn bản thì không ép thành bảng
    ratio = table_like_rows / max(1, len(rows))

    if ratio < 0.45:
        return False

    return True


# =========================
# HÀM NHẬN DIỆN MARKDOWN LAYOUT
# =========================


def format_line_to_markdown(line):
    line = clean_line(line)

    if not line:
        return ""

    upper_line = line.upper()

    major_titles = [
        "QUYẾT ĐỊNH",
        "QUY ĐỊNH",
        "THÔNG BÁO",
        "KẾ HOẠCH",
        "HƯỚNG DẪN",
        "QUY CHẾ",
        "HIỆU TRƯỞNG",
        "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
        "ĐỘC LẬP - TỰ DO - HẠNH PHÚC",
    ]

    for title in major_titles:
        if upper_line == title or upper_line.startswith(title):
            return f"# {line}"

    # Chương I / CHƯƠNG 1
    if re.match(r"^(CHƯƠNG|Chương)\s+([IVXLCDM]+|\d+)", line):
        return f"## {line}"

    # Mục 1
    if re.match(r"^(MỤC|Mục)\s+\d+", line):
        return f"### {line}"

    # Điều 1
    if re.match(r"^(ĐIỀU|Điều)\s+\d+", line):
        return f"### {line}"

    # Số hiệu văn bản
    if line.startswith("Số:") or line.startswith("Số "):
        return f"**{line}**"

    # Căn cứ
    if line.startswith("Căn cứ"):
        return f"**{line}**"

    # Theo đề nghị
    if line.startswith("Theo đề nghị"):
        return f"*{line}*"

    # Điểm a), b), c)
    if re.match(r"^[a-zA-ZđĐ]\)\s+", line):
        return f"- {line}"

    # Dòng toàn chữ hoa ngắn
    if line.isupper() and len(line) <= 80:
        return f"# {line}"

    return line


def is_heading_line(line):
    """
    Nhận diện các dòng nên giữ riêng, không gộp vào dòng trước.
    """
    line = clean_line(line)
    upper_line = line.upper()

    if not line:
        return True

    # Số trang đơn lẻ: 1, 2, 3...
    if re.match(r"^\d+$", line):
        return True

    # Điều, Chương, Mục
    if re.match(r"^(Điều|ĐIỀU)\s+\d+", line):
        return True

    if re.match(r"^(Chương|CHƯƠNG)\s+([IVXLCDM]+|\d+)", line):
        return True

    if re.match(r"^(Mục|MỤC)\s+\d+", line):
        return True

    # Các tiêu đề lớn
    title_keywords = [
        "NỘI QUY",
        "QUYẾT ĐỊNH",
        "QUY ĐỊNH",
        "PHỤ LỤC",
        "NỘI DUNG VI PHẠM",
        "TRUNG TÂM PHỤC VỤ SINH VIÊN",
    ]

    for keyword in title_keywords:
        if upper_line.startswith(keyword):
            return True

    return False


def is_new_item_line(line):
    """
    Nhận diện dòng bắt đầu một ý mới:
    1. ...
    1.
    2) ...
    a) ...
    - ...
    """
    line = clean_line(line)

    # 1. nội dung hoặc 1. đứng riêng
    if re.match(r"^\d+[\.\)](\s+.*)?$", line):
        return True

    # a) nội dung hoặc a) đứng riêng
    if re.match(r"^[a-zA-ZđĐ][\.\)](\s+.*)?$", line):
        return True

    if line.startswith("- "):
        return True

    if line.startswith(""):
        return True

    return False

def is_isolated_list_marker(line):
    """
    Nhận diện dòng chỉ có ký hiệu đánh số/bullet đứng riêng.
    Ví dụ:
    1.
    2.
    a)
    -
    
    """
    line = clean_line(line)

    if re.match(r"^\d+[\.\)]$", line):
        return True

    if re.match(r"^[a-zA-ZđĐ][\.\)]$", line):
        return True

    if line in ["-", "•", ""]:
        return True

    return False



def should_merge_lines(previous_line, current_line):
    """
    Quyết định có nên gộp current_line vào previous_line không.
    """

    previous_line = clean_line(previous_line)
    current_line = clean_line(current_line)

    if not previous_line or not current_line:
        return False

    # Không gộp nếu dòng hiện tại là tiêu đề
    if is_heading_line(current_line):
        return False

    # Không gộp nếu dòng hiện tại bắt đầu khoản mới / bullet mới
    if is_new_item_line(current_line):
        return False

    # Không gộp nếu dòng trước là tiêu đề
    if is_heading_line(previous_line):
        return False
    
    # Nếu dòng trước chỉ là số thứ tự/bullet đứng riêng,
    # thì phải nối dòng hiện tại vào.
    # Ví dụ:
    # 1.
    # Cơ sở thực hiện:
    # -> 1. Cơ sở thực hiện:
    if is_isolated_list_marker(previous_line):
        return True

    # Nếu dòng trước kết thúc bằng dấu câu mạnh thì thường là hết đoạn
    if previous_line.endswith((".", ":", ";", "!", "?", "./.")):
        return False

    # Còn lại nhiều khả năng là bị ngắt dòng trong PDF
    return True


def merge_broken_lines(raw_text):
    """
    Gộp các dòng bị xuống dòng do layout PDF.
    Ví dụ:
    'học viên sau'
    'đại học...'
    → 'học viên sau đại học...'
    """

    lines = raw_text.splitlines()
    merged_lines = []

    for line in lines:
        line = clean_line(line)

        if not line:
            continue

        # Bỏ số trang đơn lẻ
        if re.match(r"^\d+$", line):
            continue

        if not merged_lines:
            merged_lines.append(line)
            continue

        previous_line = merged_lines[-1]

        if should_merge_lines(previous_line, line):
            # Nếu dòng trước kết thúc bằng dấu gạch nối thì nối liền
            # Ví dụ: QĐ- + ĐHCT = QĐ-ĐHCT
            if previous_line.endswith("-"):
                merged_lines[-1] = previous_line + line
            else:
                merged_lines[-1] = previous_line + " " + line
        else:
            merged_lines.append(line)

    return "\n".join(merged_lines)


def format_text_to_markdown(text):
    """
    Gộp dòng bị ngắt trước,
    sau đó mới nhận diện heading / Điều / khoản / bullet.
    """

    # Gộp các dòng bị ngắt do layout PDF trước khi format markdown
    text = merge_broken_lines(text)

    lines = text.splitlines()
    formatted_lines = []

    for line in lines:
        line = clean_line(line)

        if not line:
            continue

        formatted_lines.append(format_line_to_markdown(line))

    return "\n\n".join(formatted_lines)


# =========================
# OCR ẢNH BẰNG EASYOCR
# =========================


def ocr_image_plain(image_path):
    """
    OCR ảnh để lấy text thường.
    """
    results = reader.readtext(image_path, detail=0, paragraph=True)
    text = "\n".join(results)
    return clean_text(text)


def ocr_image_detail(image_path):
    """
    OCR ảnh lấy cả text và tọa độ bbox.
    Dùng để dựng bảng từ ảnh / PDF scan.
    """
    results = reader.readtext(image_path, detail=1, paragraph=False)
    return results


# =========================
# XỬ LÝ FILE PDF
# =========================


def extract_pdf_hybrid(pdf_path):
    """
    Xử lý PDF:
    - PDF copy được text:
        + Lấy bảng bằng PyMuPDF find_tables()
        + Lấy text ngoài bảng bằng PyMuPDF
    - PDF scan:
        + Render trang thành ảnh
        + OCR bằng EasyOCR
        + Nếu giống bảng thì dựng Markdown table từ tọa độ OCR
    """

    doc = fitz.open(pdf_path)

    all_pages = []
    total_chars = 0
    pymupdf_pages = 0
    ocr_pages = 0
    table_pages = 0

    file_stem = Path(pdf_path).stem

    for page_index, page in enumerate(doc):
        page_number = page_index + 1

        raw_text = page.get_text("text").strip()
        raw_text = clean_text(raw_text)

        page_markdown = []
        page_markdown.append(f"## Trang {page_number}\n")

        # =========================
        # TRƯỜNG HỢP 1: PDF COPY ĐƯỢC TEXT
        # =========================
        if len(raw_text) >= MIN_TEXT_LENGTH:
            pymupdf_pages += 1
            total_chars += len(raw_text)

            page_markdown.append("<!-- extraction: pymupdf -->\n")

            # 1. Tìm bảng bằng PyMuPDF
            markdown_tables, table_bboxes = extract_tables_from_pdf_page(page)

            # 2. Nếu có bảng, lấy text ngoài bảng để tránh bị lặp nội dung bảng
            if markdown_tables:
                table_pages += 1
                page_markdown.append("<!-- table_extraction: pymupdf_find_tables -->\n")

                outside_text = extract_text_outside_tables(page, table_bboxes)
                outside_text = clean_text(outside_text)

                if outside_text:
                    page_markdown.append(format_text_to_markdown(outside_text))

                page_markdown.append("\n\n## Bảng trích xuất\n")

                for table_md in markdown_tables:
                    page_markdown.append(table_md)

            # 3. Nếu không có bảng thì xử lý text bình thường
            else:
                page_markdown.append(format_text_to_markdown(raw_text))

        # =========================
        # TRƯỜNG HỢP 2: PDF SCAN
        # =========================
        else:
            ocr_pages += 1

            image_path = image_temp_folder / f"{file_stem}_page_{page_number}.png"

            if image_path.exists():
                print(f"[CACHE] Dùng lại ảnh đã có: {image_path}")
            else:
                print(f"[RENDER] Đang chuyển trang {page_number} thành ảnh...")
                pix = page.get_pixmap(dpi=RENDER_DPI)
                pix.save(str(image_path))

            page_markdown.append("<!-- extraction: easyocr_pdf_scan -->\n")

            # OCR có tọa độ để kiểm tra bảng
            ocr_results = ocr_image_detail(str(image_path))
            ocr_text = easyocr_result_to_text(ocr_results)

            total_chars += len(ocr_text)

            is_table_page = False


            if ocr_results:
                is_table_page = looks_like_table_from_ocr(ocr_results)

            if is_table_page:
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

        # Sau khi xử lý xong MỌI loại trang (PDF text hoặc PDF scan),
        # luôn phải thêm page_markdown vào all_pages.
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


# =========================
# XỬ LÝ FILE ẢNH
# =========================


def extract_image_file(image_path):
    """
    Xử lý file ảnh:
    - OCR trực tiếp bằng EasyOCR
    - Nếu ảnh có dạng bảng thì dựng lại Markdown table
    """

    ocr_results = ocr_image_detail(str(image_path))
    text = easyocr_result_to_text(ocr_results)

    markdown_parts = []
    markdown_parts.append("## Trang 1\n")
    markdown_parts.append("<!-- extraction: easyocr_image -->\n")

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


# =========================
# GHI FILE MARKDOWN
# =========================


def save_markdown_output(source_path, content, metadata, extraction_mode):
    file_name = os.path.basename(source_path)
    file_stem = Path(file_name).stem

    output_path = output_folder / f"{file_stem}_structured.md"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# PDF / Image Text Document\n\n")

        f.write("## Metadata\n\n")
        f.write(f"- Source file: `{source_path}`\n")
        f.write(f"- Source name: `{file_name}`\n")
        f.write(f"- Extraction mode: {extraction_mode}\n")
        f.write("- Parser: PyMuPDF\n")
        f.write("- OCR engine: EasyOCR\n")
        f.write("- Language: vi\n")
        f.write(f"- Total pages: {metadata['total_pages']}\n")
        f.write(f"- Total characters: {metadata['total_characters']}\n")
        f.write(f"- PyMuPDF pages: {metadata['pymupdf_pages']}\n")
        f.write(f"- OCR pages: {metadata['ocr_pages']}\n")
        f.write(f"- Table pages: {metadata.get('table_pages', 0)}\n")
        f.write(f"- Created at: {datetime.now().isoformat(timespec='seconds')}\n\n")

        f.write("## Extracted Text\n\n")
        f.write(content)

    print(f"[OK] Đã lưu: {output_path}")


#

def get_output_path_for_source(source_path):
    """
    Tạo đường dẫn output tương ứng với file nguồn.
    Ví dụ:
    input/abc.pdf -> output/abc_structured.md
    """
    file_stem = Path(source_path).stem
    return Path(output_folder) / f"{file_stem}_structured.md"


def process_one_file(file_path, supported_pdf, supported_images, force=False):
    """
    Xử lý 1 file PDF hoặc ảnh cụ thể.
    Nếu output đã tồn tại thì bỏ qua, trừ khi dùng --force.
    """

    file_path = Path(file_path)
    file_name = file_path.name
    ext = file_path.suffix.lower()

    if not file_path.exists():
        print(f"[ERROR] Không tìm thấy file: {file_path}")
        return

    if ext not in supported_pdf and ext not in supported_images:
        print(f"[SKIP] Không hỗ trợ file: {file_name}")
        return

    output_path = get_output_path_for_source(file_path)

    if output_path.exists() and not force:
        print(f"[SKIP] Output đã tồn tại, không OCR lại: {output_path}")
        print("       Dùng thêm --force nếu cần xử lý lại file này.")
        return

    try:
        print(f"\nĐang xử lý: {file_path}")

        if ext in supported_pdf:
            content, metadata = extract_pdf_hybrid(str(file_path))
            save_markdown_output(
                source_path=str(file_path),
                content=content,
                metadata=metadata,
                extraction_mode="hybrid_pymupdf_easyocr"
            )

        elif ext in supported_images:
            content, metadata = extract_image_file(str(file_path))
            save_markdown_output(
                source_path=str(file_path),
                content=content,
                metadata=metadata,
                extraction_mode="easyocr_image"
            )

    except Exception as e:
        print(f"[ERROR] Lỗi khi xử lý {file_path}: {e}")

# =========================
# CHƯƠNG TRÌNH CHÍNH
# =========================


def main():
    supported_pdf = [".pdf"]
    supported_images = [".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"]

    parser = argparse.ArgumentParser(
        description="Trích xuất text / OCR từ PDF hoặc ảnh sang Markdown."
    )

    parser.add_argument(
        "path",
        nargs="?",
        default=input_folder,
        help="Đường dẫn file cụ thể hoặc folder. Mặc định là folder input."
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Xử lý lại dù file output đã tồn tại."
    )

    args = parser.parse_args()

    input_path = Path(args.path)

    # Nếu người dùng nhập đường dẫn tương đối, ưu tiên kiểm tra theo thư mục hiện tại.
    # Nếu không thấy, kiểm tra thêm theo PROJECT_ROOT để tránh lỗi khi chạy trong folder OCR.
    if not input_path.exists() and not input_path.is_absolute():
        project_relative_path = PROJECT_ROOT / input_path
        if project_relative_path.exists():
            input_path = project_relative_path

    if not input_path.exists():
        print(f"[ERROR] Không tìm thấy đường dẫn: {input_path}")
        return

    print(f"[DEBUG] Project root: {PROJECT_ROOT}")
    print(f"[DEBUG] Output folder: {output_folder}")
    print(f"[DEBUG] Temp images folder: {image_temp_folder}")

    # Trường hợp 1: Người dùng truyền vào 1 file cụ thể
    if input_path.is_file():
        print(f"[DEBUG] Chế độ xử lý 1 file: {input_path.resolve()}")
        process_one_file(
            file_path=input_path,
            supported_pdf=supported_pdf,
            supported_images=supported_images,
            force=args.force
        )

    # Trường hợp 2: Người dùng truyền vào 1 folder
    elif input_path.is_dir():
        print(f"[DEBUG] Chế độ xử lý folder: {input_path.resolve()}")

        all_files = [p for p in input_path.rglob("*") if p.is_file()]

        print(f"[DEBUG] Số file tìm thấy: {len(all_files)}")

        if not all_files:
            print("[INFO] Không tìm thấy file nào trong folder.")
            return

        for file_path in all_files:
            process_one_file(
                file_path=file_path,
                supported_pdf=supported_pdf,
                supported_images=supported_images,
                force=args.force
            )

        print("\nHoàn tất xử lý toàn bộ file trong folder.")

    else:
        print(f"[ERROR] Đường dẫn không hợp lệ: {input_path}")


if __name__ == "__main__":
    main()
