import fitz  # PyMuPDF
import os
import re
from pathlib import Path

# =========================
# CẤU HÌNH ĐƯỜNG DẪN
# =========================

pdf_path = r"input/Noi quy KTX nam 2016.pdf"
output_folder = "output"

os.makedirs(output_folder, exist_ok=True)


# =========================
# HÀM LÀM SẠCH TEXT
# =========================

def clean_line(line):
    """
    Làm sạch từng dòng text:
    - Xóa khoảng trắng thừa
    - Chuẩn hóa dấu cách
    """
    line = line.strip()
    line = re.sub(r"\s+", " ", line)
    return line


# =========================
# HÀM NHẬN DIỆN LAYOUT MARKDOWN
# =========================

def format_line_to_markdown(line):
    """
    Nhận diện từng dòng và chuyển sang Markdown có cấu trúc.
    """

    line = clean_line(line)

    if not line:
        return ""

    upper_line = line.upper()

    # 1. Nhận diện tên văn bản lớn
    major_titles = [
        "QUYẾT ĐỊNH",
        "QUY ĐỊNH",
        "THÔNG BÁO",
        "KẾ HOẠCH",
        "HƯỚNG DẪN",
        "HIỆU TRƯỞNG",
        "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
        "ĐỘC LẬP - TỰ DO - HẠNH PHÚC",
    ]

    for title in major_titles:
        if upper_line == title or upper_line.startswith(title):
            return f"# {line}"

    # 2. Nhận diện Chương
    # Ví dụ: Chương I, CHƯƠNG 1, Chương II. QUY ĐỊNH CHUNG
    if re.match(r"^(CHƯƠNG|Chương)\s+([IVXLCDM]+|\d+)", line):
        return f"## {line}"

    # 3. Nhận diện Mục
    # Ví dụ: Mục 1, MỤC 2
    if re.match(r"^(MỤC|Mục)\s+\d+", line):
        return f"### {line}"

    # 4. Nhận diện Điều
    # Ví dụ: Điều 1. Nội dung...
    if re.match(r"^(ĐIỀU|Điều)\s+\d+", line):
        return f"### {line}"

    # 5. Nhận diện Khoản dạng số
    # Ví dụ: 1. Sinh viên phải...
    if re.match(r"^\d+\.\s+", line):
        return f"{line}"

    # 6. Nhận diện điểm a), b), c)
    # Ví dụ: a) Nội dung...
    if re.match(r"^[a-zA-ZđĐ]\)\s+", line):
        return f"- {line}"

    # 7. Nhận diện dòng số hiệu văn bản
    # Ví dụ: Số: 3266/QĐ-ĐHCT
    if line.startswith("Số:") or line.startswith("Số "):
        return f"**{line}**"

    # 8. Nhận diện dòng căn cứ
    if line.startswith("Căn cứ"):
        return f"**{line}**"

    # 9. Nhận diện dòng theo đề nghị
    if line.startswith("Theo đề nghị"):
        return f"*{line}*"

    # 10. Nhận diện nơi nhận, hiệu trưởng, ký tên
    footer_keywords = [
        "Nơi nhận",
        "HIỆU TRƯỞNG",
        "KT. HIỆU TRƯỞNG",
        "PHÓ HIỆU TRƯỞNG",
        "TRƯỞNG PHÒNG",
        "Lưu:",
    ]

    for keyword in footer_keywords:
        if upper_line.startswith(keyword.upper()):
            return f"**{line}**"

    # 11. Dòng toàn chữ hoa và khá ngắn thì xem như tiêu đề phụ
    # Ví dụ: QUYẾT ĐỊNH:, NỘI DUNG, PHỤ LỤC
    if line.isupper() and len(line) <= 80:
        return f"# {line}"

    # 12. Mặc định là đoạn văn bình thường
    return line


# =========================
# HÀM XỬ LÝ TEXT CỦA 1 TRANG
# =========================

def format_page_text(raw_text):
    """
    Nhận text thô từ PyMuPDF,
    tách dòng,
    xử lý layout Markdown.
    """

    lines = raw_text.splitlines()
    formatted_lines = []

    for line in lines:
        line = clean_line(line)

        if not line:
            continue

        markdown_line = format_line_to_markdown(line)
        formatted_lines.append(markdown_line)

    return "\n".join(formatted_lines)


# =========================
# CHƯƠNG TRÌNH CHÍNH
# =========================

if not os.path.exists(pdf_path):
    print(f"[ERROR] Không tìm thấy file: {pdf_path}")

else:
    file_name = os.path.basename(pdf_path)
    file_stem = Path(file_name).stem
    output_path = os.path.join(output_folder, f"{file_stem}_structured.md")

    print(f"Đang trích xuất text từ PDF: {file_name}")

    doc = fitz.open(pdf_path)

    all_pages = []
    total_chars = 0
    empty_pages = 0

    for page_index, page in enumerate(doc):
        raw_text = page.get_text("text").strip()
        total_chars += len(raw_text)

        page_markdown = []
        page_markdown.append(f"## Trang {page_index + 1}\n")

        if raw_text:
            formatted_text = format_page_text(raw_text)
            page_markdown.append(formatted_text)
        else:
            empty_pages += 1
            page_markdown.append("[Trang này không trích xuất được text]")

        page_markdown.append("\n---\n")

        all_pages.append("\n".join(page_markdown))

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# PDF Text Document\n\n")

        f.write("## Metadata\n\n")
        f.write(f"- Source file: `{pdf_path}`\n")
        f.write("- Extraction tool: PyMuPDF\n")
        f.write("- OCR used: No\n")
        f.write("- Document type: unknown\n")
        f.write("- Classification status: pending\n")
        f.write(f"- Total pages: {len(doc)}\n")
        f.write(f"- Total characters: {total_chars}\n")
        f.write(f"- Empty pages: {empty_pages}\n\n")

        f.write("## Extracted Text\n\n")
        f.write("\n\n".join(all_pages))

    doc.close()

    print(f"Đã lưu kết quả vào: {output_path}")
    print("Hoàn tất trích xuất text từ PDF.")