# README OCR – CTU Student Service

Tài liệu này mô tả module **OCR/Parser** trong project **CTU Student Service**. Mục tiêu là chuyển PDF, ảnh scan, văn bản quy định, quyết định, biểu mẫu của CTU thành file Markdown có cấu trúc để phục vụ xử lý dữ liệu, chunking và RAG.

---

## 1. Giới thiệu

Module OCR cần xử lý:

- PDF có thể copy text.
- PDF scan không copy được text.
- Ảnh văn bản `.jpg`, `.png`, `.jpeg`.
- Văn bản có bảng, danh sách, chương, điều, khoản, điểm.
- Văn bản hành chính như quy định, quyết định, biểu mẫu, hướng dẫn thủ tục.

Output mong muốn:

```text
output/<ten_file>_structured.md
```

Nội dung cần giữ:

- Tiêu đề, heading, mục lớn/mục nhỏ.
- Chương, Điều, Khoản, Điểm.
- Danh sách, bảng nếu nhận diện được.
- Page marker để citation:

```markdown
<!-- page: 1 -->
```

Không cần giữ: font chữ, căn lề, header/footer lặp lại, dấu trang trí, khoảng trắng thừa.

---

## 2. Các phương pháp OCR/Parser

### 2.1. PyMuPDF – cho PDF copy text được

Dùng khi PDF có text thật, có thể bôi đen/copy.

**Ưu điểm:** nhanh, nhẹ, chính xác cao với PDF text.  
**Nhược điểm:** không đọc được ảnh scan, có thể lỗi xuống dòng hoặc vỡ bảng.

File liên quan:

```text
OCR/extract_pdf_text.py
OCR/OCR_EasyPymu_main.py
OCR_PadViet_main/main.py
```

Cách chạy:

```powershell
python OCR_PadViet_main/main.py "input/PDF_text/ten_file.pdf"
```

---

### 2.2. EasyOCR – cho ảnh/PDF scan

Dùng cho ảnh hoặc PDF scan đã convert từng trang thành ảnh.

**Ưu điểm:** dễ cài, nhận diện tiếng Việt khá ổn, phù hợp máy CPU.  
**Nhược điểm:** chậm hơn PyMuPDF, giữ bảng/layout chưa tốt.

File liên quan:

```text
OCR/hybrid_pymupdf_easyocr.py
OCR/OCR_EasyPymu_main.py
OCR_PadViet_main/ocr_engine.py
OCR_PadViet_main/image_preprocess.py
OCR_PadViet_main/markdown_layout.py
```

Cách chạy:

```powershell
python OCR_PadViet_main/main.py "input/PDF_scan/ten_file.pdf"
python OCR_PadViet_main/main.py "input/images/ten_anh.jpg"
```

---

### 2.3. PaddleOCR – OCR nâng cao

Dùng cho ảnh/PDF scan, có thể kết hợp PP-Structure để xử lý bảng/layout.

**Ưu điểm:** OCR mạnh, có khả năng mở rộng tốt.  
**Nhược điểm:** cài đặt phức tạp hơn, dễ lỗi version, chạy CPU có thể chậm.

Cách chạy bằng pipeline chính:

```powershell
python OCR_PadViet_main/main.py "input/PDF_scan/ten_file.pdf"
```

Test nhanh vài trang:

```powershell
python OCR_PadViet_main/main.py "input/PDF_scan/ten_file.pdf" --page-start 1 --page-end 2
```

---

### 2.4. PP-Structure – nhận diện bảng/layout

Dùng khi tài liệu có bảng, biểu mẫu hoặc layout phức tạp.

**Ưu điểm:** hỗ trợ table/layout tốt hơn OCR thường.  
**Nhược điểm:** cần hậu xử lý, không phải file nào cũng nhận diện chính xác.

---

## 3. Pipeline khuyến nghị

```text
Input file
    |
    |-- PDF copy text được
    |       -> PyMuPDF extract text
    |       -> Gộp dòng / sửa lỗi xuống dòng
    |       -> Chuẩn hóa Markdown
    |
    |-- PDF scan
    |       -> Convert từng trang sang ảnh
    |       -> OCR bằng EasyOCR hoặc PaddleOCR
    |       -> Nếu có bảng thì thử PP-Structure
    |       -> Chuẩn hóa Markdown
    |
    |-- Ảnh
            -> Tiền xử lý ảnh
            -> OCR bằng EasyOCR hoặc PaddleOCR
            -> Chuẩn hóa Markdown
```

Output cuối:

```text
output/<ten_file>_structured.md
```

---

## 4. Cấu trúc thư mục gợi ý

```text
CTU_Student_Service/
│
├── OCR/
│   ├── OCR_EasyPymu_main.py
│   ├── extract_pdf_text.py
│   └── hybrid_pymupdf_easyocr.py
│
├── OCR_PadViet_main/
│   ├── main.py
│   ├── config.py
│   ├── common_fix.py
│   ├── ctu_terms.py
│   ├── image_preprocess.py
│   ├── markdown_layout.py
│   ├── ocr_engine.py
│   └── README.md
│
├── input/
│   ├── PDF_text/
│   ├── PDF_scan/
│   └── images/
│
├── output/
└── temp_images/
```

---

## 5. Vai trò các file chính

| File | Chức năng |
|---|---|
| `main.py` | File chạy chính, nhận input và điều phối pipeline. |
| `config.py` | Lưu cấu hình chung như DPI, thư mục, engine OCR. |
| `common_fix.py` | Sửa lỗi xuống dòng, khoảng trắng, dấu câu, ký tự sai. |
| `ctu_terms.py` | Từ điển thuật ngữ CTU để sửa cụm từ hay gặp. |
| `image_preprocess.py` | Tiền xử lý ảnh trước OCR. |
| `ocr_engine.py` | Gọi EasyOCR/PaddleOCR. |
| `markdown_layout.py` | Chuyển text OCR thành Markdown có cấu trúc. |
| `extract_pdf_text.py` | Extract text từ PDF copy được bằng PyMuPDF. |
| `hybrid_pymupdf_easyocr.py` | Kết hợp PyMuPDF và EasyOCR. |

---

## 6. Cài đặt môi trường

Khuyến nghị dùng Python 3.11.

```powershell
cd D:\Code\CTU_Student_Service
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip setuptools wheel
```

Kiểm tra:

```powershell
python --version
pip --version
```

Thoát môi trường ảo:

```powershell
deactivate
```

---

## 7. Cài các thư viện chính

### PyMuPDF

```powershell
pip install pymupdf
python -c "import fitz; print('PyMuPDF OK')"
```

### EasyOCR

```powershell
pip install easyocr
python -c "import easyocr; print('EasyOCR OK')"
```

Ví dụ trong code:

```python
import easyocr
reader = easyocr.Reader(['vi', 'en'], gpu=False)
result = reader.readtext('input/images/test.jpg', detail=0)
print(result)
```

### PaddleOCR

```powershell
pip install paddlepaddle
pip install paddleocr
python -c "from paddleocr import PaddleOCR; print('PaddleOCR OK')"
```

Ví dụ:

```python
from paddleocr import PaddleOCR
ocr = PaddleOCR(use_angle_cls=True, lang='vi')
result = ocr.ocr('input/images/test.jpg', cls=True)
print(result)
```

### PP-Structure

```powershell
python -c "from paddleocr import PPStructure; print('PP-Structure OK')"
```

Ví dụ:

```python
from paddleocr import PPStructure
engine = PPStructure(lang='en', show_log=True)
result = engine('input/images/page_001.png')
print(result)
```

### Thư viện hỗ trợ

```powershell
pip install pillow opencv-python numpy pandas tqdm python-dotenv
```

---

## 8. File requirements gợi ý

```text
pymupdf
easyocr
paddlepaddle
paddleocr
pillow
opencv-python
numpy
pandas
tqdm
python-dotenv
```

Cài toàn bộ:

```powershell
pip install -r requirements.txt
```

Nếu PaddleOCR lỗi, nên cài riêng theo thứ tự:

```powershell
pip install pymupdf pillow opencv-python numpy pandas tqdm python-dotenv
pip install easyocr
pip install paddlepaddle
pip install paddleocr
```

---

## 9. Hướng dẫn chạy

### PDF copy text được

```powershell
python OCR_PadViet_main/main.py "input/PDF_text/qt_xep_TKB.pdf"
```

### PDF scan

```powershell
python OCR_PadViet_main/main.py "input/PDF_scan/QD3266.pdf"
```

### Chạy vài trang để test nhanh

```powershell
python OCR_PadViet_main/main.py "input/PDF_scan/QD3266.pdf" --page-start 1 --page-end 2
```

### Ảnh đơn

```powershell
python OCR_PadViet_main/main.py "input/images/dongioithieu.jpg"
```

### OCR toàn bộ folder

```powershell
python OCR_PadViet_main/main.py "D:\Code\CTU_Student_Service\Dataset\02_Attachments\PDFs"
```

---

## 10. Cache ảnh trang PDF

Với PDF scan, chương trình convert từng trang thành ảnh trước khi OCR:

```text
temp_images/<ten_file>/page_001.png
temp_images/<ten_file>/page_002.png
...
```

Nếu ảnh đã tồn tại thì nên dùng lại, không convert lại. Cách này giúp chạy lại nhanh hơn và dễ debug từng trang.

---

## 11. Markdown output mong muốn

```markdown
# QUY ĐỊNH CÔNG TÁC HỌC VỤ

<!-- page: 1 -->

## Chương I. QUY ĐỊNH CHUNG

### Điều 1. Phạm vi điều chỉnh

Nội dung văn bản...

1. Khoản thứ nhất...
2. Khoản thứ hai...

| Cột 1 | Cột 2 | Cột 3 |
|---|---|---|
| Nội dung | Nội dung | Nội dung |

<!-- page: 2 -->

### Điều 2. Đối tượng áp dụng

Nội dung văn bản...
```

---

## 12. Lỗi OCR thường gặp

### Lỗi xuống dòng sai

Ví dụ lỗi:

```text
Sinh viên phải thực hiện
đúng quy định của Trường.
```

Output mong muốn:

```text
Sinh viên phải thực hiện đúng quy định của Trường.
```

Cách xử lý: gộp dòng nếu dòng trước chưa kết thúc bằng `.`, `:`, `;`, `?`, `!`, nhưng không gộp nếu dòng sau là heading, Điều, Chương, bullet hoặc số thứ tự.

---

### Lỗi thuật ngữ CTU

Ví dụ:

```text
Truờng Đại học Cần Tho
Quy che dao tao
```

Output mong muốn:

```text
Trường Đại học Cần Thơ
Quy chế đào tạo
```

Nên bổ sung từ điển trong `ctu_terms.py`, gồm các cụm như:

- Trường Đại học Cần Thơ.
- Phòng Công tác Sinh viên.
- Phòng Đào tạo.
- Học vụ, học phần, cố vấn học tập.
- Quyết định, quy định, biểu mẫu.

---

### Lỗi heading sai

Không nên chỉ dựa vào từ khóa như “Quy định”, “Quyết định” để tạo heading. Cần xét thêm độ dài dòng, vị trí, kiểu đánh số và ngữ cảnh trước/sau.

---

### Lỗi bảng mất cấu trúc

- PDF text: thử extract table bằng PyMuPDF hoặc thư viện bảng riêng.
- PDF scan/ảnh: thử PP-Structure.
- Bảng phức tạp có thể cần hậu xử lý thủ công hoặc bán tự động.

---

## 13. So sánh nhanh phương pháp

| Phương pháp | Dùng cho | Ưu điểm | Nhược điểm |
|---|---|---|---|
| PyMuPDF | PDF copy text | Nhanh, chính xác, nhẹ | Không OCR ảnh, có thể lỗi xuống dòng |
| EasyOCR | Ảnh/PDF scan | Dễ cài, tiếng Việt ổn | Chậm, bảng yếu |
| PaddleOCR | Ảnh/PDF scan | OCR mạnh, mở rộng tốt | Cài phức tạp hơn |
| PP-Structure | Bảng/layout | Hỗ trợ table/layout | Cần hậu xử lý, dễ lỗi version |
| Hybrid | Tài liệu hỗn hợp | Linh hoạt nhất | Code phức tạp hơn |

---

## 14. Gợi ý chọn phương pháp

| Trường hợp | Nên dùng |
|---|---|
| PDF bôi đen/copy text được | PyMuPDF |
| PDF scan toàn bộ | EasyOCR hoặc PaddleOCR |
| Ảnh chụp văn bản | EasyOCR hoặc PaddleOCR |
| File có bảng | PP-Structure + hậu xử lý |
| Test nhanh | PyMuPDF hoặc giới hạn trang |
| Pipeline ổn định dễ debug | Hybrid PyMuPDF + EasyOCR |
| Phát triển nâng cao | Hybrid PyMuPDF + PaddleOCR + PP-Structure |

---

## 15. Một số lệnh kiểm tra nhanh

```powershell
python -c "import fitz; print('PyMuPDF OK')"
python -c "import easyocr; print('EasyOCR OK')"
python -c "from paddleocr import PaddleOCR; print('PaddleOCR OK')"
python -c "from paddleocr import PPStructure; print('PP-Structure OK')"
python -c "import cv2; print('OpenCV OK')"
```

---

## 16. Lỗi thường gặp khi chạy

### Không tìm thấy file

Kiểm tra lại đường dẫn. Nếu đường dẫn có khoảng trắng, đặt trong dấu ngoặc kép:

```powershell
python OCR_PadViet_main/main.py "D:\Code\CTU_Student_Service\input\PDF_text\qt_xep_TKB.pdf"
```

### Lỗi import PaddleOCR/PaddlePaddle

```powershell
pip show paddlepaddle
pip show paddleocr
```

Nếu vẫn lỗi, nên tạo lại venv Python 3.11 rồi cài lại.

### OCR chạy nhưng không ra text

Nguyên nhân có thể là ảnh mờ, DPI thấp, sai cấu hình ngôn ngữ, ảnh convert bị trắng hoặc model chưa tải đúng.

Cách xử lý:

- Kiểm tra ảnh trong `temp_images`.
- Tăng DPI lên 200 hoặc 300.
- Test trước 1 ảnh đơn.
- Test EasyOCR trước, PaddleOCR sau.

### Markdown output rỗng hoặc quá ít ký tự

```powershell
Get-Item .\output\ten_file_structured.md | Select-Object Name, Length
```

Nếu `Length` quá nhỏ, kiểm tra lại OCR, bước ghi file và phần hậu xử lý.

---

## 17. Quy trình test đề xuất

Khi sửa OCR code, nên test theo thứ tự:

1. Ảnh đơn.
2. PDF scan 1 trang.
3. PDF scan 2 trang.
4. PDF text copy được.
5. File có bảng.
6. File dài nhiều trang.
7. So sánh Markdown output với PDF gốc.

Ví dụ:

```powershell
python OCR_PadViet_main/main.py "input/PDF_scan/QD3266.pdf" --page-start 1 --page-end 2
Get-Item .\output\QD3266_structured.md | Select-Object Name, Length
```

---

## 18. Tiêu chí đánh giá output OCR

| Tiêu chí | Ý nghĩa |
|---|---|
| Độ chính xác tiếng Việt | Có sai dấu, sai chữ, mất chữ không |
| Giữ cấu trúc | Có giữ Chương/Điều/Khoản/Điểm không |
| Giữ bảng | Bảng có chuyển sang Markdown không |
| Lỗi xuống dòng | Có bị gãy dòng bất thường không |
| Page marker | Có đánh dấu trang để citation không |
| Tốc độ | Chạy có quá lâu không |
| Cache | Có chạy lại nhanh, không convert lại không |
| Dễ debug | Có log rõ ràng không |

---

## 19. Kết luận

Trong project **CTU Student Service**, nên dùng pipeline hybrid thay vì chỉ dùng một OCR engine:

- **PyMuPDF** cho PDF copy text được.
- **EasyOCR** cho ảnh/PDF scan cần ổn định, dễ cài.
- **PaddleOCR** cho hướng OCR nâng cao.
- **PP-Structure** cho tài liệu có bảng/layout.
- **Post-processing riêng** để sửa lỗi xuống dòng, thuật ngữ CTU, heading, danh sách, bảng và page marker.

Mục tiêu cuối cùng là tạo Markdown sạch, ổn định và dễ đưa vào chunking/RAG, không nhất thiết giữ y nguyên giao diện PDF.
