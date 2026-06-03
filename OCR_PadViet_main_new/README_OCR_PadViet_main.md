# OCR_PadViet_main

Source OCR dành cho tài liệu CTU/RAG, dùng để chuyển PDF/ảnh sang Markdown có cấu trúc.

Bản này dùng luồng xử lý chính:

- PDF có thể copy text: dùng **PyMuPDF** để lấy text và bảng.
- PDF scan hoặc ảnh: render trang thành ảnh, dùng **PaddleOCR** để phát hiện vùng chữ, dùng **VietOCR** để nhận dạng tiếng Việt, và fallback PaddleOCR khi cần.
- Sau khi lấy text: chạy 3 lớp hậu xử lý gồm lỗi chung, thuật ngữ CTU và lỗi riêng/ít gặp.
- Output cuối cùng là file Markdown `*_structured.md` kèm báo cáo review nếu còn dòng nghi ngờ.

File chạy chính là:

```text
main.py
```

---

## 1. Cấu trúc file

| File | Chức năng |
| --- | --- |
| `main.py` | File chạy chính, đọc tham số dòng lệnh, điều phối xử lý PDF/ảnh và ghi output. |
| `config.py` | Cấu hình chung: thư mục output, DPI, page range, OCR engine, cache, debug, hậu xử lý. |
| `ocr_engine.py` | Khởi tạo PaddleOCR/VietOCR, detect box, crop vùng chữ, nhận dạng text, fallback ký tự đặc biệt. |
| `image_preprocess.py` | Đọc/ghi ảnh Unicode, xóa con dấu đỏ, tạo ảnh biến thể, crop box chữ. |
| `markdown_layout.py` | Gộp dòng bị vỡ, nhận diện heading Chương/Điều/Mục, bullet/list và header/footer lặp. |
| `common_fix.py` | Lớp 1: sửa lỗi OCR phổ biến trong văn bản hành chính, quy định, quyết định, biểu mẫu. |
| `ctu_terms.py` | Lớp 2: sửa và bảo vệ thuật ngữ thường gặp của CTU Student Service. |
| `rare_fix.py` | Lớp 3: lỗi riêng/ít gặp, tạo báo cáo review hoặc nhận rule sửa từ file JSON ngoài source. |
| `README.md` | Hướng dẫn cài đặt và chạy chương trình. |

---

## 2. Công nghệ sử dụng

| Công nghệ | Vai trò |
| --- | --- |
| Python | Ngôn ngữ chạy toàn bộ pipeline. |
| PyMuPDF / `fitz` | Đọc PDF text, render PDF scan thành ảnh, trích bảng nếu PDF có bảng. |
| PaddleOCR | Phát hiện vùng chữ và fallback nhận dạng text. |
| VietOCR | Nhận dạng tiếng Việt từ crop chữ do PaddleOCR phát hiện. |
| OpenCV | Tiền xử lý ảnh, xóa dấu đỏ, crop box, tăng tương phản. |
| Pillow | Chuyển ảnh OpenCV sang định dạng PIL cho VietOCR. |
| Markdown | Định dạng output phục vụ RAG/citation sau này. |

---

## 3. Chuẩn bị trước khi cài

Nên dùng:

- Windows 10/11.
- Visual Studio Code.
- PowerShell.
- Python 3.10 hoặc 3.11. Khuyến nghị **Python 3.11**.
- Chạy CPU là đủ. GPU không bắt buộc.

Kiểm tra Python:

```powershell
python --version
```

Hoặc nếu máy có nhiều bản Python:

```powershell
py --version
py -3.11 --version
```

Nếu chưa có Python, cài Python trước và nhớ chọn:

```text
Add python.exe to PATH
```

Nên tránh Python quá mới như 3.13 vì một số thư viện OCR/deep learning có thể chưa hỗ trợ ổn định. Nên cài 3.11

---

## 4. Giải nén source

Giải nén file zip vào thư mục project, ví dụ:

```text
D:\Code\CTU_Student_Service\OCR_PadViet_main
```

Cấu trúc nên có dạng:

```text
CTU_Student_Service
├── OCR_PadViet_main
│   ├── main.py
│   ├── config.py
│   ├── ocr_engine.py
│   ├── image_preprocess.py
│   ├── markdown_layout.py
│   ├── common_fix.py
│   ├── ctu_terms.py
│   ├── rare_fix.py
│   └── README.md
├── input
└── output
```

Khuyến nghị chạy lệnh từ thư mục project gốc:

```powershell
cd D:\Code\CTU_Student_Service
```

Lý do: trong source, đường dẫn mặc định `input` và `output` được hiểu theo thư mục terminal hiện tại.

---

## 5. Tạo môi trường ảo `.venv`

Tạo venv:

```powershell
python -m venv .venv
```

Nếu máy có nhiều Python, dùng rõ Python 3.11:

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

## 6. Nâng cấp pip

Sau khi đã vào venv, chạy:

```powershell
python -m pip install --upgrade pip setuptools wheel
```

Kiểm tra pip đang nằm trong venv:

```powershell
python -m pip --version
```

Đường dẫn hiển thị nên có `.venv`.

---

## 7. Cài thư viện cần thiết

### 7.1. Cài PyTorch CPU cho VietOCR

VietOCR cần `torch` và `torchvision`. Với máy không dùng GPU, cài bản CPU:

```powershell
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

### 7.2. Cài PaddlePaddle + PaddleOCR

Bản source này đang dùng API kiểu PaddleOCR 2.x, nên khuyến nghị cài bản ổn định theo source:

```powershell
python -m pip install paddlepaddle==3.3.1
python -m pip install paddleocr==2.9.1
```

Nếu lệnh trên lỗi do phiên bản Python, hãy đổi sang Python 3.11 rồi tạo lại `.venv`.

### 7.3. Cài các thư viện còn lại

```powershell
python -m pip install vietocr pymupdf opencv-python pillow "numpy<2"
```

Trong đó:

- `vietocr`: nhận dạng tiếng Việt.
- `pymupdf`: import bằng tên `fitz`, dùng đọc/render PDF.
- `opencv-python`: import bằng tên `cv2`, dùng tiền xử lý ảnh.
- `pillow`: dùng chuyển ảnh sang PIL cho VietOCR.
- `numpy<2`: giúp tránh một số lỗi tương thích với OpenCV/PaddleOCR trên Windows.

---

## 8. Kiểm tra thư viện đã cài thành công

Chạy lệnh kiểm tra import:

```powershell
python -c "import fitz, cv2, paddle; from paddleocr import PaddleOCR; from vietocr.tool.config import Cfg; print('PyMuPDF + OpenCV + PaddleOCR + VietOCR OK')"
```

Nếu hiện:

```text
PyMuPDF + OpenCV + PaddleOCR + VietOCR OK
```

là cài thành công.

Lưu ý: lần đầu chạy PaddleOCR/VietOCR có thể tự tải model nên sẽ lâu hơn các lần sau.

---

## 9. Cách chạy OCR

### 9.1. Xem các tham số hỗ trợ

```powershell
python OCR_PadViet_main\main.py --help
```

---

### 9.2. Chạy toàn bộ folder input

```powershell
python OCR_PadViet_main\main.py "input"
```

Lệnh này sẽ quét tất cả file PDF/ảnh trong thư mục `input`.

Các định dạng hỗ trợ:

```text
.pdf, .png, .jpg, .jpeg, .bmp, .tif, .tiff, .webp
```

---

### 9.3. Chạy một file PDF cụ thể

```powershell
python OCR_PadViet_main\main.py "input\PDF_scan\Cong_van_282.pdf"
```

Nếu đường dẫn có khoảng trắng, phải đặt trong dấu nháy kép:

```powershell
python OCR_PadViet_main\main.py "input\PDF_scan\Noi quy KTX nam 2016.pdf"
```

---

### 9.4. Chạy một file ảnh cụ thể

```powershell
python OCR_PadViet_main\main.py "input\images\mau_don.png"
```

---

### 9.5. Chạy một số trang PDF

Ví dụ chỉ chạy trang 1 đến trang 2:

```powershell
python OCR_PadViet_main\main.py "input\PDF_scan\Cong_van_282.pdf" --page-start 1 --page-end 2
```

<span style="color: rgb(232, 149, 74);">Nếu file dài hoặc máy yếu, nên test vài trang trước bằng cách này.</span>

---

### 9.6. Chạy lại khi output đã tồn tại

Mặc định nếu output đã có, chương trình sẽ bỏ qua để tránh OCR lại.

Muốn xử lý lại, thêm `--force`:

```powershell
python OCR_PadViet_main\main.py "input\PDF_scan\Cong_van_282.pdf" --force
```

---

### 0.7. Đổi thư mục output

Mặc định output nằm ở:

```text
output
```

Nếu muốn lưu sang thư mục khác:

```powershell
python OCR_PadViet_main\main.py "input\PDF_scan\Cong_van_282.pdf" --output "output_padviet"
```

---

## 10. Các lệnh chạy thường dùng

### Chạy PDF scan chất lượng cao

```powershell
python OCR_PadViet_main\main.py "input\PDF_scan\ten_file.pdf" --dpi 300 --force
```

### Chạy PDF scan nhẹ hơn cho máy yếu

```powershell
python OCR_PadViet_main\main.py "input\PDF_scan\ten_file.pdf" --dpi 200 --page-start 1 --page-end 2
```

### Chạy bằng PaddleOCR thuần, không dùng VietOCR

```powershell
python OCR_PadViet_main\main.py "input\PDF_scan\ten_file.pdf" --no-vietocr
```

### Không xóa con dấu đỏ

```powershell
python OCR_PadViet_main\main.py "input\PDF_scan\ten_file.pdf" --no-red-stamp-clean
```

### Tắt fallback ký tự đặc biệt

```powershell
python OCR_PadViet_main\main.py "input\PDF_scan\ten_file.pdf" --no-symbol-fallback
```

### Dùng chế độ gộp dòng mạnh hơn

```powershell
python OCR_PadViet_main\main.py "input\PDF_text\ten_file.pdf" --layout-merge-mode aggressive --force
```

### Lưu crop VietOCR để debug

```powershell
python OCR_PadViet_main\main.py "input\PDF_scan\ten_file.pdf" --save-crops --force
```

Crop sẽ được lưu ở:

```text
output\vietocr_crops
```

### Chỉ dùng ảnh cache đã render trước đó

```powershell
python OCR_PadViet_main\main.py "input\PDF_scan\ten_file.pdf" --existing-images-only --force
```

Lưu ý: lệnh này chỉ chạy được nếu ảnh trang đã có trong:

```text
output\temp_images
```

---

## 11. Output nằm ở đâu?

Markdown sau xử lý được lưu tại:

```text
output\<ten_file>_structured.md
```

Ví dụ:

```text
output\Cong_van_282_structured.md
```

Ảnh tạm render từ PDF scan nằm tại:

```text
output\temp_images
```

Báo cáo review lỗi nghi ngờ nằm tại:

```text
output\review_reports\<ten_file>_review.txt
```

Nếu bật `--save-crops`, crop chữ để debug nằm tại:

```text
output\vietocr_crops
```

---

## 12. Cách chương trình tự chọn PDF text hay OCR

Với mỗi trang PDF, chương trình dùng PyMuPDF lấy text trước.

Nếu trang có đủ text, output sẽ có marker:

```text
<!-- extraction: pymupdf_text -->
```

Nghĩa là trang đó là PDF có thể copy text, không cần OCR ảnh.

Nếu trang có quá ít text, chương trình render trang thành ảnh rồi OCR. Output sẽ có marker:

```text
<!-- extraction: ocr_pdf_scan -->
```

Với file ảnh, output sẽ có:

```text
<!-- extraction: paddle_detect_vietocr_recognize -->
```

hoặc fallback:

```text
<!-- extraction: paddleocr_plain -->
```

---

## 13. Luồng xử lý chính

```text
main.py
↓
Nhận path file/folder từ dòng lệnh
↓
PDF text?
├── Có  → PyMuPDF extract text + PyMuPDF table
└── Không → Render trang PDF thành ảnh
              ↓
           image_preprocess.py
              ↓
           PaddleOCR detect box
              ↓
           Crop từng dòng chữ
              ↓
           VietOCR nhận dạng tiếng Việt
              ↓
           Fallback PaddleOCR nếu nghi lỗi @, URL, ký tự đặc biệt
↓
common_fix.py   → sửa lỗi OCR chung
ctu_terms.py    → sửa thuật ngữ CTU
rare_fix.py     → sửa/cảnh báo lỗi riêng ít gặp
↓
markdown_layout.py → gộp dòng, heading, bullet, page marker
↓
output/<ten_file>_structured.md
output/review_reports/<ten_file>_review.txt
```

---

## 14. Ý nghĩa các module hậu xử lý

### 14.1. `common_fix.py` - lỗi chung

Dùng cho lỗi phổ biến, không phụ thuộc một file cụ thể:

- Chuẩn hóa khoảng trắng.
- Chuẩn hóa bullet/gạch đầu dòng.
- Sửa email/link bị OCR sai ký tự `@`.
- Sửa số điện thoại bị tách khoảng trắng.
- Sửa một số lỗi tiếng Việt phổ biến.
- Sửa ký tự đặc biệt như `?` bị OCR nhầm thành gạch ngang trong vài ngữ cảnh.

Không nên đưa lỗi riêng theo tên một PDF vào đây.

---

### 14.2. `ctu_terms.py` - thuật ngữ CTU

Dùng cho các thuật ngữ thường gặp trong đề tài CTU Student Service:

- Trường Đại học Cần Thơ.
- Phòng Đào tạo.
- Phòng Công tác Sinh viên.
- Học vụ.
- Học phần.
- Điểm rèn luyện.
- Giấy xác nhận sinh viên.
- Tạm hoãn nghĩa vụ quân sự.
- Vay vốn sinh viên.

Nếu lỗi thuật ngữ lặp lại ở nhiều tài liệu CTU, thêm vào file này.

---

### 14.3. `rare_fix.py` - lỗi riêng/ít gặp

Dùng cho lỗi chưa đủ chắc để tự sửa hàng loạt.

Mặc định module này ưu tiên tạo file review:

```text
output\review_reports\<ten_file>_review.txt
```

Nếu muốn tự động sửa lỗi riêng mà không sửa source, tạo file JSON rồi truyền bằng `--loi-rieng-json`.

Ví dụ file `rules_loi_rieng.json`:

```json
{
  "replace": {
    "chuỗi OCR sai": "chuỗi đúng"
  },
  "regex_replace": [
    {
      "pattern": "Số:\\s*ABC",
      "replacement": "Số: XYZ",
      "flags": "i"
    }
  ]
}
```

Chạy:

```powershell
python OCR_PadViet_main\main.py "input\PDF_scan\ten_file.pdf" --loi-rieng-json "rules_loi_rieng.json" --force
```

---

### 14.4. `markdown_layout.py` - bố cục Markdown

Dùng để:

- Gộp dòng bị xuống dòng sai.
- Giữ riêng các dòng `Chương`, `Mục`, `Điều`.
- Không tự phóng to dòng có chữ `Quy định` nếu nó chỉ nằm trong câu bình thường.
- Khôi phục bullet/list trong văn bản hành chính.
- Xóa header/footer lặp giữa nhiều trang.
- Thêm page marker dạng:

```text
<!-- page: 1 -->
```

Page marker này quan trọng để sau này làm citation trong RAG.

---

## 15. Bảng tham số dòng lệnh quan trọng

| Tham số | Ý nghĩa |
| --- | --- |
| `path` | Đường dẫn file PDF/ảnh hoặc folder. Mặc định là `input`. |
| `--output` | Thư mục lưu output. Mặc định là `output`. |
| `--force` | Chạy lại dù file output đã tồn tại. |
| `--dpi` | DPI render PDF scan. Mặc định 300. Máy yếu có thể dùng 200. |
| `--page-start` | Trang bắt đầu, đánh số từ 1. |
| `--page-end` | Trang kết thúc, đánh số từ 1. |
| `--lang` | Ngôn ngữ PaddleOCR: `vi`, `latin`, `en`. Mặc định `vi`. |
| `--gpu` | Bật GPU nếu đã cài đúng Paddle/Torch GPU. Bình thường không dùng. |
| `--no-vietocr` | Tắt VietOCR, dùng PaddleOCR thuần. |
| `--vietocr-model` | Chọn model VietOCR: `vgg_transformer` hoặc `vgg_seq2seq`. |
| `--vietocr-weights` | Đường dẫn weights VietOCR custom nếu có. |
| `--crop-padding` | Padding quanh crop OCR. Mặc định 8. |
| `--save-crops` | Lưu crop chữ để debug VietOCR. |
| `--no-image-cache` | Không dùng cache ảnh render/ảnh tiền xử lý. |
| `--existing-images-only` | Chỉ dùng ảnh cache đã có, không render trang mới. |
| `--no-red-stamp-clean` | Không xóa vùng con dấu đỏ. |
| `--no-symbol-fallback` | Không fallback PaddleOCR cho dòng nghi lỗi ký tự đặc biệt. |
| `--layout-merge-mode` | Chế độ gộp dòng: `conservative` hoặc `aggressive`. |
| `--loi-rieng-json` | File JSON chứa rule sửa lỗi riêng ngoài source. |
| `--no-loi-chung` | Tắt lớp sửa lỗi chung. |
| `--no-tu-dien-ctu` | Tắt từ điển CTU. |
| `--no-loi-rieng` | Tắt lớp lỗi riêng/review. |
| `--no-debug-images` | Không giữ ảnh biến thể debug. |

---

## 16. Khi nào dùng tham số nào?

### PDF text copy được nhưng xuống dòng xấu

```powershell
python OCR_PadViet_main\main.py "input\PDF_text\ten_file.pdf" --layout-merge-mode aggressive --force
```

Nếu aggressive làm gộp sai, đổi về mặc định:

```powershell
python OCR_PadViet_main\main.py "input\PDF_text\ten_file.pdf" --layout-merge-mode conservative --force
```

### PDF scan có chữ nhỏ, ký tự đặc biệt, email

```powershell
python OCR_PadViet_main\main.py "input\PDF_scan\ten_file.pdf" --dpi 300 --crop-padding 10 --force
```

### Máy yếu, chỉ muốn test nhanh

```powershell
python OCR_PadViet_main\main.py "input\PDF_scan\ten_file.pdf" --dpi 200 --page-start 1 --page-end 1
```

### VietOCR lỗi hoặc chạy quá chậm

```powershell
python OCR_PadViet_main\main.py "input\PDF_scan\ten_file.pdf" --no-vietocr --force
```

### Con dấu đỏ bị xóa làm mất chữ

```powershell
python OCR_PadViet_main\main.py "input\PDF_scan\ten_file.pdf" --no-red-stamp-clean --force
```

---

## 17. Một số lỗi thường gặp và cách xử lý

### 17.1. Không tìm thấy file input

Thông báo có thể là:

```text
[WARN] Không tìm thấy file PDF/ảnh trong: input
```

Cách xử lý:

- Kiểm tra đang đứng đúng thư mục project chưa.
- Kiểm tra đã tạo folder `input` chưa.
- Kiểm tra file có thật trong folder chưa.
- Nếu đường dẫn có dấu cách, đặt trong dấu nháy kép.

Ví dụ đúng:

```powershell
python OCR_PadViet_main\main.py "input\PDF_scan\Noi quy KTX nam 2016.pdf"
```

---

### 17.2. Output đã tồn tại nên không OCR lại

Thông báo:

```text
[SKIP] Output đã tồn tại
```

Cách xử lý:

```powershell
python OCR_PadViet_main\main.py "input\PDF_scan\ten_file.pdf" --force
```

---

### 17.3. Lỗi `ModuleNotFoundError: No module named 'fitz'`

Không cài package tên `fitz` riêng. Package đúng là `pymupdf`.

```powershell
python -m pip install --upgrade pymupdf
```

---

### 17.4. Lỗi `ModuleNotFoundError: No module named 'paddleocr'`

Cài lại PaddleOCR:

```powershell
python -m pip install paddleocr==2.9.1
```

---

### 17.5. Lỗi `ModuleNotFoundError: No module named 'paddle'`

Cài PaddlePaddle CPU:

```powershell
python -m pip install paddlepaddle==3.3.1
```

---

### 17.6. VietOCR import lỗi hoặc Torch lỗi

Cài lại PyTorch CPU và VietOCR:

```powershell
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
python -m pip install vietocr
```

Nếu vẫn lỗi, tạo lại venv bằng Python 3.11.

---

### 17.7. PaddleOCR/VietOCR tự tải model rất lâu

Lần đầu chạy có thể tải model nên lâu. Cần có internet ổn định. Các lần sau model đã có cache nên nhanh hơn.

---

### 17.8. OCR PDF scan chạy quá chậm

Cách giảm tải:

- Chạy từng trang bằng `--page-start` và `--page-end`.
- Giảm DPI từ 300 xuống 200.
- Tắt VietOCR bằng `--no-vietocr` nếu chỉ cần test nhanh.
- Không dùng `--force` nếu output đã có.
- Giữ lại `output\temp_images` để lần sau không cần render lại.

Ví dụ:

```powershell
python OCR_PadViet_main\main.py "input\PDF_scan\ten_file.pdf" --dpi 200 --page-start 1 --page-end 2 --no-vietocr
```

---

### 17.9. Markdown không hiển thị nội dung dù file có dung lượng

Kiểm tra file output:

```powershell
Get-Item .\output\ten_file_structured.md | Select-Object Name, Length
```

Mở file bằng VS Code:

```powershell
code .\output\ten_file_structured.md
```

Nếu Markdown preview không hiện, mở trực tiếp file `.md` ở chế độ text để kiểm tra nội dung trước.

---

## 18. Thoát môi trường ảo

Khi không dùng nữa:

```powershell
deactivate
```

---

## 19. Lệnh chạy nhanh nên nhớ

Kiểm tra thư viện:

```powershell
python -c "import fitz, cv2, paddle; from paddleocr import PaddleOCR; from vietocr.tool.config import Cfg; print('OK')"
```

Chạy toàn bộ input:

```powershell
python OCR_PadViet_main\main.py "input"
```

Chạy một PDF scan:

```powershell
python OCR_PadViet_main\main.py "input\PDF_scan\ten_file.pdf" --dpi 300 --force
```

Chạy một PDF text:

```powershell
python OCR_PadViet_main\main.py "input\PDF_text\ten_file.pdf" --force
```

Chạy một ảnh:

```powershell
python OCR_PadViet_main\main.py "input\images\ten_file.png" --force
```

Chỉ chạy trang 1 đến 2:

```powershell
python OCR_PadViet_main\main.py "input\PDF_scan\ten_file.pdf" --page-start 1 --page-end 2 --force
```

---

## 20. Nguyên tắc bảo trì source

Không nên nhét toàn bộ lỗi OCR vào `main.py`.

Nên chia như sau:

| Loại lỗi | File nên sửa |
| --- | --- |
| Lỗi khoảng trắng, dấu câu, email, link, số điện thoại | `common_fix.py` |
| Lỗi thuật ngữ CTU lặp lại nhiều tài liệu | `ctu_terms.py` |
| Lỗi riêng ít gặp, chưa chắc chắn | `rare_fix.py` hoặc file JSON ngoài source |
| Lỗi xuống dòng, heading, bullet, page marker | `markdown_layout.py` |
| Lỗi ảnh scan, dấu đỏ, crop, ảnh mờ | `image_preprocess.py` |
| Lỗi detect/recognize OCR | `ocr_engine.py` |

Nguyên tắc quan trọng:

- Chỉ thêm rule tự động nếu lỗi có tính lặp lại và đủ an toàn.
- Không sửa đoán nội dung pháp lý nếu không chắc.
- Lỗi riêng từng file nên đưa vào JSON qua `--loi-rieng-json`, không hard-code vào source.
- Sau mỗi lần sửa rule, test lại bằng `--page-start` và `--page-end` trước khi chạy toàn bộ file.

---

## 21. Gợi ý quy trình test một tài liệu mới

Bước 1: Chạy 1-2 trang đầu để kiểm tra:

```powershell
python OCR_PadViet_main\main.py "input\PDF_scan\ten_file.pdf" --page-start 1 --page-end 2 --force
```

Bước 2: Mở file Markdown output:

```powershell
code .\output\ten_file_structured.md
```

Bước 3: Mở báo cáo review nếu có:

```powershell
code .\output\review_reports\ten_file_review.txt
```

Bước 4: Nếu ổn thì chạy toàn bộ file:

```powershell
python OCR_PadViet_main\main.py "input\PDF_scan\ten_file.pdf" --force
```

Bước 5: Nếu có lỗi lặp lại nhiều tài liệu, thêm rule vào module tương ứng thay vì sửa thủ công file Markdown.