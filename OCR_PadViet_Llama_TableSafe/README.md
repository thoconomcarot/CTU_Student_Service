# OCR PadViet Llama TableSafe

Bản tối ưu mới để tránh lỗi tạo bảng giả:

- `main.py`: pipeline local, **không còn trích bảng bằng PyMuPDF**.
- `main_table_safe.py`: pipeline khuyến nghị, tự route trang bảng/lưu đồ sang LlamaParse.
- `README_TABLESAFE.md`: hướng dẫn chi tiết.

Chạy nhanh:

```powershell
python -m pip install -r requirements_llamaparse.txt
python main_table_safe.py "D:\Code\CTU_Student_Service\Dataset\02_Attachments\PDFs\CTSV\QuyTrinh4-Congtacsinhvien.pdf" --engine auto-page --page-start 1 --page-end 4
```

Không dùng LlamaParse, không cần API key:

```powershell
python main_table_safe.py "file.pdf" --engine local --page-start 1 --page-end 4
```

Chỉ định trang bảng/lưu đồ thủ công:

```powershell
python main_table_safe.py "file.pdf" --engine auto-page --table-pages 4,6,8-10
```
