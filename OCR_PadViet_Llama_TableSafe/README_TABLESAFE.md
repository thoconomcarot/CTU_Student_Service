# OCR PadViet + LlamaParse TableSafe

Bản này sửa lỗi chính đã gặp với file `QuyTrinh4-Congtacsinhvien.pdf`:

1. **Không còn dùng PyMuPDF để tạo bảng Markdown.**  
   PyMuPDF `find_tables()` dễ nhận nhầm các đoạn văn bản thường thành bảng giả, đặc biệt ở văn bản hành chính có nhiều dòng căn lề đều.

2. **Nếu cần tạo bảng thì dùng LlamaParse.**  
   Trang văn bản thường dùng local text/OCR. Trang có bảng/lưu đồ thật mới route sang LlamaParse.

3. **Có detector layout trước khi gọi LlamaParse.**  
   File `document_page_analyzer.py` kiểm tra keyword bảng/lưu đồ, đường kẻ vector và đường kẻ raster. Detector chỉ quyết định trang nào có bảng, không trích bảng.

4. **Sửa thêm lỗi dính chữ và heading a/b/c.**  
   Ví dụ: `số16` -> `số 16`, `phiếu“` -> `phiếu “`, `CTSVtập` -> `CTSV tập`, `ĐRLcấp` -> `ĐRL cấp`. Các dòng `a. Mục đích: ...` không còn bị nâng cả câu dài thành heading.

## File chính

| File | Chức năng |
|---|---|
| `main_table_safe.py` | CLI khuyến nghị để chạy pipeline TableSafe |
| `hybrid_page_router.py` | Ghép kết quả local và LlamaParse theo từng trang |
| `document_page_analyzer.py` | Nhận diện trang có bảng/lưu đồ thật, không tạo bảng |
| `main.py` | Pipeline local TableSafe, PyMuPDF text-only + Paddle/VietOCR khi cần OCR |
| `llamaparse_engine.py` | Gọi LlamaParse cho trang bảng/lưu đồ |
| `markdown_layout.py` | Gộp dòng, nhận diện heading/list an toàn hơn |
| `common_fix.py` | Sửa lỗi OCR/PDF text phổ biến |
| `text_layer_quality.py` | Kiểm tra text layer PDF có bị lỗi không, không phụ thuộc PaddleOCR |

## Cài thêm thư viện

```powershell
python -m pip install -r requirements_llamaparse.txt
```

Nếu chưa cài OCR local cũ thì cài thêm theo README cũ của PadViet.

## API key LlamaParse

Chỉ cần API key khi dùng `--engine auto-page` có trang bảng/lưu đồ, hoặc `--engine llamaparse`.

```powershell
setx LLAMA_CLOUD_API_KEY "llx-API_KEY_CUA_BAN"
```

Đóng terminal VS Code rồi mở lại. Kiểm tra:

```powershell
echo $env:LLAMA_CLOUD_API_KEY
```

## Cách chạy khuyến nghị

### 1. Chạy tự động theo từng trang

```powershell
python main_table_safe.py "D:\Code\CTU_Student_Service\Dataset\02_Attachments\PDFs\CTSV\QuyTrinh4-Congtacsinhvien.pdf" --engine auto-page --page-start 1 --page-end 4
```

Với file mẫu này, detector sẽ để trang 1,2,3 dùng local và route trang 4 sang LlamaParse.

### 2. Chạy local toàn bộ, tuyệt đối không tạo bảng

```powershell
python main_table_safe.py "D:\Code\CTU_Student_Service\Dataset\02_Attachments\PDFs\CTSV\QuyTrinh4-Congtacsinhvien.pdf" --engine local --page-start 1 --page-end 4
```

Lệnh này không cần API key. Trang 4 sẽ chỉ là text thô, không có bảng Markdown.

### 3. Chỉ định thủ công trang có bảng/lưu đồ

```powershell
python main_table_safe.py "D:\Code\CTU_Student_Service\Dataset\02_Attachments\PDFs\CTSV\QuyTrinh4-Congtacsinhvien.pdf" --engine auto-page --page-start 1 --page-end 4 --table-pages 4
```

Cách này ổn định nhất nếu bạn đã biết trang nào có bảng.

### 4. Bảng/lưu đồ khó

```powershell
python main_table_safe.py "D:\Code\CTU_Student_Service\Dataset\02_Attachments\PDFs\CTSV\QuyTrinh4-Congtacsinhvien.pdf" --engine auto-page --table-pages 4 --llama-tier agentic_plus --spatial
```

Chỉ bật `--aggressive-tables` khi trang chắc chắn là bảng/lưu đồ phức tạp:

```powershell
python main_table_safe.py "file.pdf" --engine auto-page --table-pages 4 --aggressive-tables
```

## Nguyên tắc dùng

- Trang văn bản thường: **local**.
- Trang bảng/lưu đồ/form: **LlamaParse**.
- Không dùng PyMuPDF để tạo bảng.
- Khi nghi ngờ detector sai, dùng `--table-pages` để chỉ định thủ công.
