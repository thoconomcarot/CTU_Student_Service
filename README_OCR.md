# README OCR – CTU Student Service

Tài liệu này mô tả phần OCR/Parser trong project **CTU Student Service**. Mục tiêu của module OCR là chuyển các tài liệu như PDF, ảnh scan, văn bản quy định, quyết định, biểu mẫu của CTU thành file Markdown có cấu trúc để phục vụ bước xử lý dữ liệu và RAG.

---

## 1. Giới thiệu

Trong project này, OCR không chỉ dùng để nhận diện chữ từ ảnh mà còn dùng để chuẩn hóa tài liệu thành Markdown dễ truy xuất.

Module OCR cần xử lý các loại tài liệu sau:

- PDF có thể copy text.
- PDF scan không copy được text.
- Ảnh văn bản, ví dụ `.jpg`, `.png`.
- Văn bản có bảng, danh sách, chương, điều, khoản, điểm.
- Văn bản hành chính như quy định, quyết định, biểu mẫu, hướng dẫn thủ tục.

Output mong muốn là file Markdown có cấu trúc, ví dụ:

```text
output/<ten_file>_structured.md
```

Nội dung cần giữ lại:

- Tiêu đề chính.
- Heading / mục lớn / mục nhỏ.
- Chương, Điều, Khoản, Điểm.
- Danh sách.
- Bảng nếu nhận diện được.
- Page marker để phục vụ citation, ví dụ:

```markdown
<!-- page: 1 -->
```

Không cần giữ lại:

- Font chữ.
- Căn lề.
- Header/footer lặp lại.
- Dấu trang trí.
- Khoảng trắng thừa.

---

## 2. Các phương pháp OCR/Parser đang dùng

Project hiện có nhiều hướng xử lý khác nhau tùy loại file đầu vào.

### 2.1. PyMuPDF – dùng cho PDF có thể copy text

Dùng khi file PDF có text thật, có thể bôi đen và copy được.

Ưu điểm:

- Chạy nhanh.
- Không cần OCR từng ảnh.
- Độ chính xác chữ gần như cao nhất nếu PDF có text chuẩn.
- Phù hợp cho PDF text, công văn, quy định dạng số hóa.

Nhược điểm:

- Không đọc được chữ nằm trong ảnh scan.
- Có thể bị lỗi xuống dòng do layout PDF.
- Bảng có thể bị vỡ cấu trúc nếu PDF không có table layout rõ ràng.

File liên quan:

```text
OCR/extract_pdf_text.py
OCR/OCR_EasyPymu_main.py
OCR_PadViet_main/main.py
```

Cách chạy ví dụ:

```powershell
python OCR/extract_pdf_text.py "input/PDF_text/ten_file.pdf"
```

Hoặc chạy bằng pipeline chính:

```powershell
python OCR_PadViet_main/main.py "input/PDF_text/ten_file.pdf"
```

Khi nào nên dùng:

- File PDF copy text được.
- Cần tốc độ nhanh.
- Không cần nhận diện chữ từ ảnh.

---

### 2.2. EasyOCR – dùng cho ảnh hoặc PDF scan

EasyOCR dùng để nhận diện chữ từ ảnh hoặc từ các trang PDF đã convert thành ảnh.

Ưu điểm:

- Cài đặt tương đối đơn giản.
- Nhận diện tiếng Việt khá ổn.
- Phù hợp với máy không quá mạnh.
- Dễ kết hợp với PyMuPDF để tạo pipeline hybrid.

Nhược điểm:

- Chạy chậm hơn PyMuPDF.
- Không giữ bảng tốt nếu không có xử lý layout riêng.
- Có thể sai dấu tiếng Việt, dính chữ, gãy dòng.
- Với PDF nhiều trang, cần convert từng trang thành ảnh nên mất thời gian.

File liên quan:

```text
OCR/hybrid_pymupdf_easyocr.py
OCR/OCR_EasyPymu_main.py
OCR_PadViet_main/ocr_engine.py
OCR_PadViet_main/image_preprocess.py
OCR_PadViet_main/markdown_layout.py
```

Cách chạy ví dụ:

```powershell
python OCR/hybrid_pymupdf_easyocr.py "input/PDF_scan/ten_file.pdf"
```

Hoặc dùng pipeline chính:

```powershell
python OCR_PadViet_main/main.py "input/PDF_scan/ten_file.pdf"
```

Chạy với ảnh:

```powershell
python OCR_PadViet_main/main.py "input/images/ten_anh.jpg"
```

Khi nào nên dùng:

- PDF scan không copy text được.
- File ảnh `.jpg`, `.png`, `.jpeg`.
- Cần nhận diện chữ tiếng Việt từ ảnh.

---

### 2.3. PaddleOCR – dùng cho OCR tiếng Việt và xử lý nâng cao

PaddleOCR là OCR engine mạnh, có thể dùng cho ảnh hoặc PDF scan sau khi convert trang thành ảnh.

Ưu điểm:

- OCR tốt với nhiều loại ảnh.
- Có thể kết hợp thêm PP-Structure để nhận diện layout và bảng.
- Phù hợp khi muốn phát triển pipeline chuyên nghiệp hơn.

Nhược điểm:

- Cài đặt phức tạp hơn EasyOCR.
- Có thể lỗi tương thích Python, PaddlePaddle, PaddleOCR.
- Nếu cấu hình sai model/lang có thể chạy nhưng không ra text.
- Chạy CPU có thể chậm.

File liên quan:

```text
OCR_PadViet_main/main.py
OCR_PadViet_main/ocr_engine.py
OCR_PadViet_main/image_preprocess.py
OCR_PadViet_main/markdown_layout.py
```

Cách chạy ví dụ:

```powershell
python OCR_PadViet_main/main.py "input/PDF_scan/ten_file.pdf"
```

Nếu muốn giới hạn số trang để test nhanh:

```powershell
python OCR_PadViet_main/main.py "input/PDF_scan/ten_file.pdf" --page-start 1 --page-end 2
```

Khi nào nên dùng:

- Muốn test OCR nâng cao hơn EasyOCR.
- Muốn thử nhận diện layout/bảng bằng PP-Structure.
- Chấp nhận cài đặt phức tạp hơn để có khả năng mở rộng tốt hơn.

---

### 2.4. PP-Structure – dùng để nhận diện bảng/layout

PP-Structure là phần mở rộng của PaddleOCR, dùng để nhận diện cấu trúc tài liệu như bảng, tiêu đề, đoạn văn, hình ảnh.

Ưu điểm:

- Có khả năng xử lý bảng tốt hơn OCR thường.
- Phù hợp với tài liệu hành chính có biểu mẫu hoặc bảng.
- Có thể hỗ trợ xuất lại bảng Markdown.

Nhược điểm:

- Cài đặt và cấu hình khó hơn.
- Không phải file nào cũng nhận diện bảng tốt.
- Có thể cần tiền xử lý ảnh để tăng độ chính xác.

Khi nào nên dùng:

- PDF/ảnh có bảng.
- Biểu mẫu hành chính.
- Tài liệu cần giữ layout tương đối rõ.

---

## 3. Pipeline xử lý được khuyến nghị

Pipeline tốt nhất cho project hiện tại nên đi theo hướng hybrid:

```text
Input file
    |
    |-- Nếu là PDF copy text được
    |       -> Dùng PyMuPDF extract text
    |       -> Gộp dòng / sửa lỗi xuống dòng
    |       -> Chuẩn hóa Markdown
    |
    |-- Nếu là PDF scan
    |       -> Convert từng trang sang ảnh
    |       -> OCR bằng EasyOCR hoặc PaddleOCR
    |       -> Nếu có bảng thì thử PP-Structure
    |       -> Chuẩn hóa Markdown
    |
    |-- Nếu là ảnh
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
│   └── <ten_file>_structured.md
│
└── temp_images/
    └── <ten_file>/
```

---

## 5. Vai trò các file chính

| File | Chức năng |
|---|---|
| `main.py` | File chạy chính, nhận đường dẫn input và điều phối pipeline. |
| `config.py` | Lưu cấu hình chung như DPI, thư mục input/output, engine OCR. |
| `common_fix.py` | Sửa lỗi thường gặp sau OCR: lỗi xuống dòng, khoảng trắng, dấu câu, ký tự sai. |
| `ctu_terms.py` | Từ điển thuật ngữ CTU, hỗ trợ sửa các cụm từ hay gặp trong văn bản sinh viên. |
| `image_preprocess.py` | Tiền xử lý ảnh trước OCR: chuyển xám, tăng tương phản, resize, khử nhiễu. |
| `ocr_engine.py` | Chứa logic gọi EasyOCR/PaddleOCR. |
| `markdown_layout.py` | Chuyển text OCR thành Markdown có heading, danh sách, bảng, page marker. |
| `extract_pdf_text.py` | Extract text trực tiếp từ PDF copy được bằng PyMuPDF. |
| `hybrid_pymupdf_easyocr.py` | Kết hợp PyMuPDF và EasyOCR để xử lý cả PDF text và PDF scan. |

---

## 6. Hướng dẫn cài đặt môi trường

### 6.1. Tạo virtual environment

Khuyến nghị dùng Python 3.11 để giảm lỗi tương thích.

```powershell
cd D:\Code\CTU_Student_Service
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip setuptools wheel
```

Kiểm tra Python trong môi trường ảo:

```powershell
python --version
pip --version
```

Thoát môi trường ảo:

```powershell
deactivate
```

---

## 7. Cài đặt PyMuPDF

Dùng cho PDF có thể copy text và convert PDF sang ảnh.

```powershell
pip install pymupdf
```

Kiểm tra:

```powershell
python -c "import fitz; print('PyMuPDF OK')"
```

Nếu chạy thành công sẽ hiện:

```text
PyMuPDF OK
```

---

## 8. Cài đặt EasyOCR

EasyOCR dùng PyTorch phía sau. Trên máy CPU, chỉ cần cài bản mặc định.

```powershell
pip install easyocr
```

Kiểm tra:

```powershell
python -c "import easyocr; print('EasyOCR OK')"
```

Ví dụ gọi EasyOCR trong code:

```python
import easyocr

reader = easyocr.Reader(['vi', 'en'], gpu=False)
result = reader.readtext('input/images/test.jpg', detail=0)
print(result)
```

Ghi chú:

- `['vi', 'en']`: nhận diện tiếng Việt và tiếng Anh.
- `gpu=False`: dùng CPU, phù hợp máy không có GPU NVIDIA.
- Lần chạy đầu có thể lâu vì EasyOCR cần tải model.

---

## 9. Cài đặt PaddleOCR

### 9.1. Cài PaddlePaddle CPU

```powershell
pip install paddlepaddle
```

Kiểm tra:

```powershell
python -c "import paddle; print('PaddlePaddle OK')"
```

### 9.2. Cài PaddleOCR

```powershell
pip install paddleocr
```

Kiểm tra:

```powershell
python -c "from paddleocr import PaddleOCR; print('PaddleOCR OK')"
```

Ví dụ gọi PaddleOCR:

```python
from paddleocr import PaddleOCR

ocr = PaddleOCR(use_angle_cls=True, lang='vi')
result = ocr.ocr('input/images/test.jpg', cls=True)
print(result)
```

Ghi chú:

- `lang='vi'`: model tiếng Việt.
- `use_angle_cls=True`: hỗ trợ nhận diện chữ bị xoay.
- Nếu không nhận được text, cần kiểm tra lại ảnh đầu vào, DPI, model và version thư viện.

---

## 10. Cài đặt PP-Structure

PP-Structure nằm trong PaddleOCR, thường dùng chung sau khi đã cài `paddleocr`.

Kiểm tra import:

```powershell
python -c "from paddleocr import PPStructure; print('PP-Structure OK')"
```

Ví dụ gọi PP-Structure:

```python
from paddleocr import PPStructure

engine = PPStructure(lang='en', show_log=True)
result = engine('input/images/page_001.png')
print(result)
```

Ghi chú:

- PP-Structure thường dùng `lang='en'` cho phần layout/table.
- OCR text có thể dùng `lang='vi'`, còn structure có thể dùng `lang='en'`.
- Với bảng phức tạp, kết quả vẫn cần hậu xử lý để xuất Markdown đẹp.

---

## 11. Cài các thư viện hỗ trợ

```powershell
pip install pillow opencv-python numpy pandas tqdm python-dotenv
```

Ý nghĩa:

| Thư viện | Công dụng |
|---|---|
| `pillow` | Đọc/ghi ảnh. |
| `opencv-python` | Tiền xử lý ảnh. |
| `numpy` | Xử lý ma trận ảnh. |
| `pandas` | Hỗ trợ xử lý bảng nếu cần. |
| `tqdm` | Hiển thị tiến trình xử lý. |
| `python-dotenv` | Đọc cấu hình từ file `.env` nếu có. |

---

## 12. File requirements gợi ý

Có thể tạo file `requirements.txt` như sau:

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

Cài toàn bộ bằng lệnh:

```powershell
pip install -r requirements.txt
```

Nếu PaddleOCR bị lỗi khi cài chung, nên cài riêng theo thứ tự:

```powershell
pip install pymupdf pillow opencv-python numpy pandas tqdm python-dotenv
pip install easyocr
pip install paddlepaddle
pip install paddleocr
```

---

## 13. Hướng dẫn chạy theo từng loại file

### 13.1. Chạy PDF có thể copy text

```powershell
python OCR_PadViet_main/main.py "input/PDF_text/qt_xep_TKB.pdf"
```

Kết quả:

```text
output/qt_xep_TKB_structured.md
```

### 13.2. Chạy PDF scan

```powershell
python OCR_PadViet_main/main.py "input/PDF_scan/QD3266.pdf"
```

Kết quả:

```text
output/QD3266_structured.md
```

### 13.3. Chạy một số trang để test nhanh

```powershell
python OCR_PadViet_main/main.py "input/PDF_scan/QD3266.pdf" --page-start 1 --page-end 2
```

Cách này dùng để kiểm tra nhanh 1-2 trang trước khi OCR toàn bộ file.

### 13.4. Chạy ảnh đơn

```powershell
python OCR_PadViet_main/main.py "input/images/dongioithieu.jpg"
```

---

## 14. Cơ chế cache ảnh trang PDF

Với PDF scan, chương trình thường phải convert từng trang thành ảnh trước khi OCR. Việc này tốn thời gian, đặc biệt với file nhiều trang.

Cơ chế cache nên hoạt động như sau:

```text
PDF gốc
    -> temp_images/<ten_file>/page_001.png
    -> temp_images/<ten_file>/page_002.png
    -> ...
```

Nếu ảnh trang đã tồn tại thì không convert lại, chỉ dùng lại ảnh cũ để OCR.

Lợi ích:

- Tiết kiệm thời gian khi chạy lại.
- Không tạo nhiều thư mục temp trùng nhau.
- Dễ debug từng trang OCR.

Ví dụ:

```text
[SKIP] page_001.png already exists
[SKIP] page_002.png already exists
[OCR] page_001.png
[OCR] page_002.png
```

---

## 15. Cấu trúc Markdown output mong muốn

Ví dụ:

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

## 16. Các lỗi OCR thường gặp và cách xử lý

### 16.1. Lỗi xuống dòng sai

Ví dụ lỗi:

```text
Sinh viên phải thực hiện
đúng quy định của Trường.
```

Output mong muốn:

```text
Sinh viên phải thực hiện đúng quy định của Trường.
```

Cách xử lý:

- Nếu dòng trước không kết thúc bằng dấu `.`, `:`, `;`, `?`, `!` thì có thể gộp với dòng sau.
- Không gộp nếu dòng sau là heading, Điều, Chương, bullet, số thứ tự.

File xử lý:

```text
OCR_PadViet_main/common_fix.py
OCR_PadViet_main/markdown_layout.py
```

---

### 16.2. Lỗi nhận diện sai thuật ngữ CTU

Ví dụ:

```text
Truờng Đại học Cần Tho
Phòng Công tác Sinh viên
Quy che dao tao
```

Output mong muốn:

```text
Trường Đại học Cần Thơ
Phòng Công tác Sinh viên
Quy chế đào tạo
```

File xử lý:

```text
OCR_PadViet_main/ctu_terms.py
```

Nên bổ sung các cụm từ thường gặp:

- Trường Đại học Cần Thơ.
- Phòng Công tác Sinh viên.
- Phòng Đào tạo.
- Học vụ.
- Học phần.
- Cố vấn học tập.
- Quyết định.
- Quy định.
- Biểu mẫu.

---

### 16.3. Lỗi tự phóng to heading sai

Một số pipeline có thể hiểu nhầm chữ in đậm hoặc cụm từ “Quy định”, “Quyết định” là tiêu đề lớn.

Cách xử lý:

- Không chỉ dựa vào từ khóa để xác định heading.
- Cần xét thêm vị trí dòng, độ dài dòng, kiểu đánh số, ngữ cảnh trước/sau.
- Chỉ đưa lên heading lớn nếu dòng thật sự là tiêu đề văn bản hoặc mục lớn.

---

### 16.4. Lỗi bảng bị mất cấu trúc

OCR thường đọc bảng thành nhiều dòng rời rạc.

Cách xử lý:

- Với PDF text: thử extract table bằng PyMuPDF hoặc thư viện xử lý bảng riêng.
- Với PDF scan/ảnh: thử PP-Structure.
- Nếu bảng phức tạp, có thể cần hậu xử lý thủ công hoặc bán tự động.

---

## 17. So sánh nhanh các phương pháp

| Phương pháp | Dùng cho | Ưu điểm | Nhược điểm |
|---|---|---|---|
| PyMuPDF | PDF copy text | Nhanh, chính xác, nhẹ | Không OCR ảnh, có thể lỗi xuống dòng |
| EasyOCR | Ảnh/PDF scan | Dễ cài, tiếng Việt ổn | Chậm, bảng yếu |
| PaddleOCR | Ảnh/PDF scan | OCR mạnh, mở rộng tốt | Cài phức tạp hơn |
| PP-Structure | Bảng/layout | Hỗ trợ table/layout | Cần hậu xử lý, có thể lỗi version |
| Hybrid PyMuPDF + OCR | Tài liệu hỗn hợp | Linh hoạt nhất | Code phức tạp hơn |

---

## 18. Gợi ý chọn phương pháp

| Trường hợp | Nên dùng |
|---|---|
| PDF bôi đen/copy text được | PyMuPDF |
| PDF scan toàn bộ | EasyOCR hoặc PaddleOCR |
| Ảnh chụp văn bản | EasyOCR hoặc PaddleOCR |
| File có bảng | PP-Structure kết hợp hậu xử lý |
| Muốn chạy nhanh để test | PyMuPDF hoặc giới hạn `--page-start`, `--page-end` |
| Muốn pipeline ổn định dễ debug | Hybrid PyMuPDF + EasyOCR |
| Muốn phát triển nâng cao | Hybrid PyMuPDF + PaddleOCR + PP-Structure |

---

## 19. Một số lệnh kiểm tra nhanh

Kiểm tra PyMuPDF:

```powershell
python -c "import fitz; print('PyMuPDF OK')"
```

Kiểm tra EasyOCR:

```powershell
python -c "import easyocr; print('EasyOCR OK')"
```

Kiểm tra PaddleOCR:

```powershell
python -c "from paddleocr import PaddleOCR; print('PaddleOCR OK')"
```

Kiểm tra PP-Structure:

```powershell
python -c "from paddleocr import PPStructure; print('PP-Structure OK')"
```

Kiểm tra OpenCV:

```powershell
python -c "import cv2; print('OpenCV OK')"
```

---

## 20. Một số lỗi thường gặp khi chạy

### Lỗi không tìm thấy file

Ví dụ:

```text
[ERROR] Không tìm thấy file: ten_file.pdf
```

Cách sửa:

- Kiểm tra lại đường dẫn file.
- Nếu đường dẫn có khoảng trắng, đặt trong dấu ngoặc kép.

Ví dụ:

```powershell
python OCR_PadViet_main/main.py "D:\Code\CTU_Student_Service\input\PDF_text\qt_xep_TKB.pdf"
```

---

### Lỗi import PaddleOCR hoặc PaddlePaddle

Cách kiểm tra:

```powershell
pip show paddlepaddle
pip show paddleocr
```

Nếu lỗi nặng, nên tạo lại venv Python 3.11 rồi cài lại.

---

### OCR chạy nhưng không ra text

Nguyên nhân có thể:

- Ảnh quá mờ.
- DPI thấp.
- Sai cấu hình ngôn ngữ OCR.
- Trang PDF convert ra ảnh trắng hoặc lỗi.
- Model OCR chưa tải đúng.

Cách xử lý:

- Kiểm tra ảnh trong thư mục `temp_images`.
- Tăng DPI lên 200 hoặc 300.
- Test trước 1 ảnh đơn.
- Test từng engine riêng: EasyOCR trước, PaddleOCR sau.

---

### File Markdown output rỗng hoặc quá ít ký tự

Cách kiểm tra:

```powershell
Get-Item .\output\ten_file_structured.md | Select-Object Name, Length
```

Nếu `Length` quá nhỏ:

- Kiểm tra OCR có ra text không.
- Kiểm tra bước ghi file output.
- Kiểm tra có bị lọc text quá mạnh trong hậu xử lý không.

---

## 21. Quy trình test đề xuất

Khi thêm hoặc sửa OCR code, nên test theo thứ tự:

1. Test ảnh đơn.
2. Test PDF scan 1 trang.
3. Test PDF scan 2 trang.
4. Test PDF text copy được.
5. Test file có bảng.
6. Test file dài nhiều trang.
7. So sánh output Markdown với PDF gốc.

Ví dụ:

```powershell
python OCR_PadViet_main/main.py "input/PDF_scan/QD3266.pdf" --page-start 1 --page-end 2
```

Sau đó kiểm tra:

```powershell
Get-Item .\output\QD3266_structured.md | Select-Object Name, Length
```

---

## 22. Tiêu chí đánh giá output OCR

Nên đánh giá theo các tiêu chí sau:

| Tiêu chí | Ý nghĩa |
|---|---|
| Độ chính xác tiếng Việt | Có sai dấu, sai chữ, mất chữ không |
| Giữ cấu trúc | Có giữ Chương/Điều/Khoản/Điểm không |
| Giữ bảng | Bảng có chuyển được sang Markdown không |
| Lỗi xuống dòng | Có bị gãy dòng bất thường không |
| Page marker | Có đánh dấu trang để citation không |
| Tốc độ | Chạy có quá lâu không |
| Khả năng chạy lại | Có cache ảnh, không convert lại không |
| Dễ debug | Có log rõ ràng không |

---

## 23. Kết luận

Trong project CTU Student Service, không nên chỉ dùng một phương pháp OCR duy nhất. Cách tốt nhất là dùng pipeline hybrid:

- **PyMuPDF** cho PDF copy text được.
- **EasyOCR** cho ảnh/PDF scan cần sự ổn định và dễ cài.
- **PaddleOCR** cho hướng OCR nâng cao.
- **PP-Structure** cho tài liệu có bảng/layout.
- **Post-processing riêng** để sửa lỗi xuống dòng, thuật ngữ CTU, heading, danh sách, bảng và page marker.

Pipeline cuối cùng nên ưu tiên tạo ra Markdown sạch, ổn định, dễ đưa vào bước chunking và RAG hơn là cố giữ y nguyên giao diện PDF.
