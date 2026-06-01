# OCR_EasyPymu_modular

Bản này được tách từ `OCR_EasyPymu_main.py` thành nhiều file theo chức năng, giữ luồng xử lý chính:

- PDF có thể copy text: dùng **PyMuPDF** để trích xuất text và bảng.
- PDF scan / ảnh: dùng **EasyOCR** để OCR tiếng Việt + tiếng Anh.
- Sau khi lấy text: xử lý lỗi xuống dòng, lỗi chính tả thường gặp của CTU, lỗi hiếm và xuất ra Markdown.

Hàm chính để chạy là:

```text
main.py
```

---

## 1. Cấu trúc file

| File | Chức năng |
|---|---|
| `main.py` | Hàm chính để chạy chương trình, đọc tham số dòng lệnh. |
| `config.py` | Cấu hình đường dẫn, định dạng hỗ trợ, ngôn ngữ OCR, DPI, ngưỡng text. |
| `file_processor.py` | Điều phối xử lý PDF/ảnh, ghi file Markdown output. |
| `ocr_engine.py` | Khởi tạo EasyOCR và OCR ảnh dạng plain/detail. |
| `table_utils.py` | Tách bảng bằng PyMuPDF và dựng bảng từ bbox EasyOCR. |
| `markdown_layout.py` | Chuyển text thành Markdown, nhận diện heading/list. |
| `line_fix.py` | Xử lý lỗi xuống dòng chung do PDF/OCR. |
| `common_fix.py` | Sửa lỗi chung: khoảng trắng, dấu câu, bullet, ký tự lạ. |
| `ctu_terms.py` | Từ điển sửa thuật ngữ thường gặp của CTU. |
| `rare_fix.py` | Nhóm lỗi ít gặp, có thể mở rộng dần. |
| `requirements.txt` | Danh sách thư viện cần cài. |
| `MODULE_MAP.txt` | Ghi chú mapping từ file 2000 dòng cũ sang từng module mới. |

---

## 2. Chuẩn bị trước khi cài

Nên dùng:

- Windows 10/11.
- Visual Studio Code.
- Python 3.10 hoặc 3.11. Khuyến nghị dùng Python 3.11.
- Chạy bằng CPU, không cần GPU.

Kiểm tra Python đã cài chưa:

```powershell
python --version
```

Hoặc:

```powershell
py --version
```

Nếu máy có nhiều bản Python, nên dùng rõ Python 3.11:

```powershell
py -3.11 --version
```

Nếu chưa có Python, hãy cài Python trước, nhớ chọn:

```text
Add python.exe to PATH
```

---

## 3. Giải nén source

Sau khi tải file zip, giải nén ra thư mục project, ví dụ:

```text
D:\Code\CTU_Student_Service\OCR_EasyPymu_modular
```

Cấu trúc nên có dạng:

```text
CTU_Student_Service
└── OCR_EasyPymu_modular
    ├── main.py
    ├── config.py
    ├── file_processor.py
    ├── ocr_engine.py
    ├── table_utils.py
    ├── markdown_layout.py
    ├── line_fix.py
    ├── common_fix.py
    ├── ctu_terms.py
    ├── rare_fix.py
    ├── requirements.txt
    └── README.md
```

Mở terminal tại thư mục project hoặc mở trực tiếp trong VS Code.

Ví dụ:

```powershell
cd D:\Code\CTU_Student_Service
```

---

## 4. Tạo môi trường ảo `.venv`

Tạo venv bằng Python:

```powershell
python -m venv .venv
```

Nếu máy có nhiều Python, dùng:

```powershell
py -3.11 -m venv .venv
```

Kích hoạt venv trên PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Khi kích hoạt thành công, terminal sẽ có dạng:

```text
(.venv) PS D:\Code\CTU_Student_Service>
```

Nếu PowerShell báo lỗi không cho chạy script, chạy lệnh này một lần:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Sau đó kích hoạt lại:

```powershell
.\.venv\Scripts\Activate.ps1
```

---

## 5. Nâng cấp pip

Sau khi đã vào venv, chạy:

```powershell
python -m pip install --upgrade pip
```

Kiểm tra pip đang nằm trong venv:

```powershell
python -m pip --version
```

Đường dẫn hiển thị nên có `.venv`.

---

## 6. Cài thư viện cần thiết

Cài theo file `requirements.txt`:

```powershell
python -m pip install -r OCR_EasyPymu_modular\requirements.txt
```

File `requirements.txt` hiện gồm:

```text
pymupdf
easyocr
opencv-python
```

Trong đó:

- `pymupdf`: đọc PDF text, render PDF scan thành ảnh.
- `easyocr`: OCR ảnh/PDF scan.
- `opencv-python`: hỗ trợ xử lý ảnh/bbox khi dựng bảng.

Nếu cài `easyocr` bị lỗi liên quan `torch` hoặc `torchvision`, cài PyTorch CPU trước:

```powershell
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

Sau đó cài lại:

```powershell
python -m pip install easyocr
```

Nếu gặp lỗi liên quan `numpy`, có thể thử:

```powershell
python -m pip install "numpy<2"
python -m pip install easyocr
```

---

## 7. Kiểm tra thư viện đã cài thành công

Chạy lệnh kiểm tra import:

```powershell
python -c "import fitz, easyocr, cv2; print('PyMuPDF + EasyOCR + OpenCV OK')"
```

Nếu hiện:

```text
PyMuPDF + EasyOCR + OpenCV OK
```

là cài thành công.

Lưu ý: lần đầu chạy EasyOCR có thể tự tải model tiếng Việt/tiếng Anh nên sẽ hơi lâu. Các lần sau sẽ nhanh hơn.

---

## 8. Tạo thư mục input/output

Do source này lấy đường dẫn theo vị trí của `main.py`, nên thư mục mặc định nên nằm trong folder `OCR_EasyPymu_modular`.

Tạo các thư mục sau:

```powershell
mkdir OCR_EasyPymu_modular\input
mkdir OCR_EasyPymu_modular\output
```

Cấu trúc sau khi tạo:

```text
OCR_EasyPymu_modular
├── input
├── output
├── main.py
└── ...
```

Bỏ file PDF hoặc ảnh cần OCR vào:

```text
OCR_EasyPymu_modular\input
```

Ví dụ:

```text
OCR_EasyPymu_modular\input\QD3266.pdf
OCR_EasyPymu_modular\input\Noi_quy_KTX.png
```

---

## 9. Cách chạy OCR

### 9.1. Chạy toàn bộ file trong folder input mặc định

```powershell
python OCR_EasyPymu_modular\main.py
```

Lệnh này sẽ quét toàn bộ file hỗ trợ trong:

```text
OCR_EasyPymu_modular\input
```

Các định dạng hỗ trợ:

```text
.pdf, .png, .jpg, .jpeg, .bmp, .tif, .tiff, .webp
```

---

### 9.2. Chạy một file PDF cụ thể

Ví dụ file nằm trong folder input:

```powershell
python OCR_EasyPymu_modular\main.py "OCR_EasyPymu_modular\input\QD3266.pdf"
```

Nếu đường dẫn có khoảng trắng, phải đặt trong dấu nháy kép:

```powershell
python OCR_EasyPymu_modular\main.py "OCR_EasyPymu_modular\input\Noi quy KTX nam 2016.pdf"
```

---

### 9.3. Chạy một file ảnh cụ thể

```powershell
python OCR_EasyPymu_modular\main.py "OCR_EasyPymu_modular\input\anh_scan.png"
```

---

### 9.4. Chạy một folder khác

```powershell
python OCR_EasyPymu_modular\main.py "D:\Code\CTU_Student_Service\input"
```

---

### 9.5. Ép xử lý lại khi output đã tồn tại

Mặc định nếu file output đã tồn tại, chương trình sẽ bỏ qua để tránh OCR lại.

Nếu muốn xử lý lại, thêm `--force`:

```powershell
python OCR_EasyPymu_modular\main.py "OCR_EasyPymu_modular\input\QD3266.pdf" --force
```

Hoặc chạy lại toàn bộ folder input:

```powershell
python OCR_EasyPymu_modular\main.py --force
```

---

## 10. Kết quả output nằm ở đâu?

File Markdown sau khi xử lý sẽ được lưu tại:

```text
OCR_EasyPymu_modular\output\<ten_file>_structured.md
```

Ví dụ:

```text
OCR_EasyPymu_modular\output\QD3266_structured.md
```

Ảnh tạm render từ PDF scan được lưu tại:

```text
OCR_EasyPymu_modular\output\temp_images
```

Nếu chạy lại cùng file PDF scan, chương trình sẽ dùng lại ảnh đã render nếu ảnh còn tồn tại.

---

## 11. Cách chương trình tự chọn PyMuPDF hay OCR

Với mỗi trang PDF, chương trình kiểm tra lượng text lấy được bằng PyMuPDF.

Nếu trang có đủ text:

```text
extraction: pymupdf
```

Nghĩa là PDF có thể copy text, chương trình dùng PyMuPDF để lấy text.

Nếu trang có quá ít text:

```text
extraction: easyocr_pdf_scan
```

Nghĩa là trang đó có khả năng là PDF scan, chương trình render trang thành ảnh rồi OCR bằng EasyOCR.

Với file ảnh:

```text
extraction: easyocr_image
```

---

## 12. Luồng xử lý chính

```text
main.py
↓
file_processor.py
↓
PDF text  → PyMuPDF → table_utils.py → markdown_layout.py
PDF scan  → render ảnh → EasyOCR → table_utils.py → markdown_layout.py
Ảnh       → EasyOCR → table_utils.py → markdown_layout.py
↓
common_fix.py
ctu_terms.py
rare_fix.py
line_fix.py
↓
output/<ten_file>_structured.md
```

---

## 13. Các nhóm lỗi đã được tách riêng

Không nên sửa lỗi trực tiếp trong `main.py`.

### 13.1. Lỗi xuống dòng chung

Sửa trong:

```text
line_fix.py
```

Dùng cho các lỗi kiểu:

```text
Trường Đại học
Cần Thơ
```

thành:

```text
Trường Đại học Cần Thơ
```

Hoặc:

```text
1.
Cơ sở thực hiện
```

thành:

```text
1. Cơ sở thực hiện
```

---

### 13.2. Lỗi chung OCR / Markdown

Sửa trong:

```text
common_fix.py
```

Dùng cho các lỗi như:

- Thừa khoảng trắng.
- Sai dấu gạch đầu dòng.
- Sai bullet.
- Dính ký tự lạ.
- Sai khoảng trắng trước/sau dấu câu.
- Nhiều dòng trống liên tiếp.

---

### 13.3. Lỗi chính tả theo thuật ngữ CTU

Sửa trong:

```text
ctu_terms.py
```

Dùng cho các thuật ngữ thường gặp:

- Trường Đại học Cần Thơ.
- Phòng Công tác Sinh viên.
- Phòng Đào tạo.
- học phần.
- sinh viên.
- cố vấn học tập.
- học vụ.
- ký túc xá.

Khi có lỗi thuật ngữ lặp lại ở nhiều tài liệu CTU, thêm vào file này.

---

### 13.4. Lỗi ít gặp riêng

Sửa trong:

```text
rare_fix.py
```

Dùng cho lỗi hiếm nhưng có thể lặp lại ở vài tài liệu.

Không nên thêm lỗi quá riêng theo đúng tên một file PDF, vì như vậy source sẽ dài và khó bảo trì.

---

## 14. Cách thêm rule sửa lỗi mới

Ví dụ muốn sửa lỗi OCR thường nhận:

```text
Dai hoc Can Tho
```

thành:

```text
Đại học Cần Thơ
```

thì thêm rule vào `ctu_terms.py`.

Ví dụ dạng regex:

```python
CTU_TERM_FIXES = [
    (r"\bDai hoc Can Tho\b", "Đại học Cần Thơ"),
]
```

Nếu là lỗi chung không thuộc CTU, thêm vào `common_fix.py`.

Nếu là lỗi xuống dòng, thêm vào `line_fix.py`.

Nếu là lỗi rất hiếm, thêm vào `rare_fix.py`.

---

## 15. Một số lỗi thường gặp và cách xử lý

### 15.1. Lỗi không tìm thấy file

Ví dụ:

```text
[ERROR] Không tìm thấy file
```

Cách xử lý:

- Kiểm tra lại đường dẫn.
- Nếu đường dẫn có dấu cách, đặt trong dấu nháy kép.
- Kiểm tra file có thật trong folder `input` không.

Ví dụ đúng:

```powershell
python OCR_EasyPymu_modular\main.py "OCR_EasyPymu_modular\input\Noi quy KTX nam 2016.pdf"
```

---

### 15.2. Output đã tồn tại nên không OCR lại

Thông báo:

```text
[SKIP] Output đã tồn tại, không OCR lại
```

Cách xử lý:

```powershell
python OCR_EasyPymu_modular\main.py "OCR_EasyPymu_modular\input\ten_file.pdf" --force
```

---

### 15.3. EasyOCR chạy lâu ở lần đầu

Lần đầu EasyOCR có thể tải model nên chậm. Hãy đợi đến khi tải xong. Các lần sau model đã có cache nên nhanh hơn.

---

### 15.4. Máy yếu, OCR PDF scan chạy chậm

Cách giảm tải:

- Chỉ chạy một file mỗi lần.
- Không dùng `--force` nếu output đã có.
- Giữ lại folder `output\temp_images` để lần sau không cần render lại ảnh.
- Nếu file PDF copy được text, chương trình sẽ tự dùng PyMuPDF nên nhanh hơn OCR scan.

---

### 15.5. Lỗi import `fitz`

Nếu gặp lỗi:

```text
ModuleNotFoundError: No module named 'fitz'
```

Cài lại PyMuPDF:

```powershell
python -m pip install --upgrade pymupdf
```

Không cài package tên `fitz` riêng, vì package cần dùng là `pymupdf`.

---

### 15.6. Lỗi import `easyocr`

Nếu gặp lỗi:

```text
ModuleNotFoundError: No module named 'easyocr'
```

Cài lại:

```powershell
python -m pip install easyocr
```

Nếu vẫn lỗi liên quan `torch`, cài PyTorch CPU trước:

```powershell
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
python -m pip install easyocr
```

---

## 16. Thoát môi trường ảo

Khi không dùng nữa:

```powershell
deactivate
```

---

## 17. Lệnh chạy nhanh thường dùng

Chạy toàn bộ input:

```powershell
python OCR_EasyPymu_modular\main.py
```

Chạy một PDF:

```powershell
python OCR_EasyPymu_modular\main.py "OCR_EasyPymu_modular\input\ten_file.pdf"
```

Chạy lại bắt buộc:

```powershell
python OCR_EasyPymu_modular\main.py "OCR_EasyPymu_modular\input\ten_file.pdf" --force
```

Kiểm tra thư viện:

```powershell
python -c "import fitz, easyocr, cv2; print('OK')"
```

---

## 18. Ghi chú bảo trì source

Nguyên tắc chỉnh source:

- Không nhét toàn bộ rule vào `main.py`.
- Không thêm rule theo từng file PDF cụ thể nếu lỗi đó không có tính lặp lại.
- Lỗi chung đưa vào `common_fix.py`.
- Lỗi xuống dòng đưa vào `line_fix.py`.
- Lỗi thuật ngữ CTU đưa vào `ctu_terms.py`.
- Lỗi ít gặp đưa vào `rare_fix.py`.
- Nếu lỗi cần kiểm tra thủ công, nên để comment rõ để tránh sửa sai hàng loạt.

Cách chia này giúp source không bị quay lại tình trạng một file dài hàng nghìn dòng.
