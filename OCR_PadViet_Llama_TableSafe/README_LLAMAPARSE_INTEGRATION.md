# Tích hợp LlamaParse vào pipeline PaddleOCR + VietOCR

Bộ file này thêm nhánh **LlamaParse cloud** vào source OCR cũ:

- `llamaparse_engine.py`: gọi LlamaParse v2, xuất Markdown có `<!-- page: n -->`.
- `hybrid_router.py`: tự chọn local OCR hoặc LlamaParse.
- `main_hybrid_llama.py`: CLI chạy hybrid.
- `requirements_llamaparse.txt`: thư viện cần cài thêm.

## 1. Cài đặt

Trong venv hiện tại:

```powershell
python -m pip install -r requirements_llamaparse.txt
```

Thiết lập API key:

```powershell
setx LLAMA_CLOUD_API_KEY "llx-API_KEY_CUA_BAN"
```

Đóng PowerShell/VS Code terminal rồi mở lại để biến môi trường có hiệu lực.

## 2. Copy file vào source cũ

Copy 3 file này vào cùng thư mục với `main.py`, `ocr_engine.py`, `markdown_layout.py` cũ:

```text
llamaparse_engine.py
hybrid_router.py
main_hybrid_llama.py
```

Nếu source cũ của bạn không có hàm `ocr_engine.process_file(...)`, mở `hybrid_router.py` và sửa hàm:

```python
def run_local_paddle_vietocr(...):
    from ocr_engine import process_file
```

thành đúng tên hàm local OCR hiện tại của bạn.

## 3. Cách chạy

### Auto: file scan/bảng khó dùng LlamaParse, PDF text thường dùng local

```powershell
python main_hybrid_llama.py "D:\Code\CTU_Student_Service\Dataset\file.pdf" --engine auto
```

### Ép dùng LlamaParse Agentic

```powershell
python main_hybrid_llama.py "D:\Code\CTU_Student_Service\Dataset\file.pdf" --engine llamaparse --llama-tier agentic
```

### Bảng/form cực khó

```powershell
python main_hybrid_llama.py "D:\Code\CTU_Student_Service\Dataset\file.pdf" --engine llamaparse --llama-tier agentic_plus --spatial --xlsx
```

### Chỉ parse vài trang để test credits

```powershell
python main_hybrid_llama.py "D:\Code\CTU_Student_Service\Dataset\file.pdf" --engine llamaparse --page-start 1 --page-end 2
```

### Ép dùng local Paddle + VietOCR

```powershell
python main_hybrid_llama.py "D:\Code\CTU_Student_Service\Dataset\file.pdf" --engine local
```

## 4. Khi nào dùng engine nào?

| Loại file | Engine nên dùng |
|---|---|
| PDF text copy được, ít bảng | `local` hoặc `auto` |
| PDF scan | `llamaparse --llama-tier agentic` |
| Bảng/phụ lục/biểu mẫu nhiều ô | `llamaparse --llama-tier agentic` |
| Bảng scan mờ, ô gộp, layout phức tạp | `llamaparse --llama-tier agentic_plus --spatial --xlsx` |
| Chạy nhiều file, tiết kiệm credits | `auto` |

## 5. Lưu ý bảo mật dữ liệu

LlamaParse là cloud service, nghĩa là file được upload lên LlamaCloud để xử lý. Với tài liệu CTU công khai thì ổn. Với tài liệu chứa thông tin cá nhân sinh viên, nên ẩn danh hoặc dùng pipeline local trước.

## Cập nhật SAFE cho lỗi bảng giả

Bản này đã đổi mặc định `aggressive_table_extraction=False` để hạn chế LlamaParse biến đoạn văn bản thường thành Markdown table.

### Khi trang là văn bản bình thường

Dùng local hoặc auto:

```powershell
python main_hybrid_llama.py "D:\Code\CTU_Student_Service\Dataset\02_Attachments\PDFs\CTSV\QuyTrinh4-Congtacsinhvien.pdf" --engine auto --page-start 1 --page-end 2
```

hoặc:

```powershell
python main_hybrid_llama.py "D:\Code\CTU_Student_Service\Dataset\02_Attachments\PDFs\CTSV\QuyTrinh4-Congtacsinhvien.pdf" --engine local --page-start 1 --page-end 2
```

### Khi trang thật sự có lưu đồ/bảng

Dùng LlamaParse, nhưng vẫn để chế độ safe trước:

```powershell
python main_hybrid_llama.py "D:\Code\CTU_Student_Service\Dataset\02_Attachments\PDFs\CTSV\QuyTrinh4-Congtacsinhvien.pdf" --engine llamaparse --llama-tier agentic --page-start 4 --page-end 4 --disable-cache
```

Nếu bảng/lưu đồ bị thiếu cột hoặc thiếu cell thì mới bật aggressive:

```powershell
python main_hybrid_llama.py "D:\Code\CTU_Student_Service\Dataset\02_Attachments\PDFs\CTSV\QuyTrinh4-Congtacsinhvien.pdf" --engine llamaparse --llama-tier agentic --page-start 4 --page-end 4 --aggressive-tables --disable-cache
```

### Lưu ý

Không nên ép `--engine llamaparse` cho toàn bộ PDF text copy được. Với dạng tài liệu như `QuyTrinh4-Congtacsinhvien.pdf`, các trang 1,2,3,5,7,9... là văn bản thường nên dùng local/PyMuPDF; các trang 4,6,8,10,12,13... có bảng/lưu đồ thì mới cân nhắc LlamaParse.
