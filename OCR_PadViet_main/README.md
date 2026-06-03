# OCR_CTU_clean_v1

Source OCR cho tài liệu CTU/RAG, đặt tên file tiếng Anh ngắn gọn dễ hiểu.

## Cấu trúc file

| File | Chức năng |
|---|---|
| `config.py` | Cấu hình chung, hàm tiện ích về text/file/checksum |
| `common_fix.py` | Lớp 1: sửa lỗi OCR phổ biến trong công văn, quy định, quyết định, biểu mẫu |
| `ctu_terms.py` | Lớp 2: từ điển/thuật ngữ thường gặp trong đề tài CTU Student Service |
| `rare_fix.py` | Lớp 3: lỗi riêng/ít gặp, ưu tiên cảnh báo review hoặc sửa bằng JSON ngoài source |
| `image_preprocess.py` | Tiền xử lý ảnh, xóa con dấu đỏ, tạo ảnh biến thể, crop vùng chữ |
| `ocr_engine.py` | PaddleOCR + VietOCR, fallback PaddleOCR cho dòng nghi lỗi ký tự đặc biệt |
| `markdown_layout.py` | Gộp dòng, nhận diện heading/bullet, tạo Markdown có page marker |
| `run_ocr.py` | File chạy chính |

## Lệnh chạy mẫu

```powershell
python OCR_CTU_clean_v1\run_ocr.py "input\PDF_scan\Cong_van_282_-_Hoc_bong_SCIC_nam_2026.pdf" --dpi 300 --crop-padding 8 --layout-merge-mode conservative --force
```

Nếu muốn tắt xóa con dấu đỏ:

```powershell
python OCR_CTU_clean_v1\run_ocr.py "input\PDF_scan\Cong_van_282_-_Hoc_bong_SCIC_nam_2026.pdf" --no-red-stamp-clean
```

Nếu muốn tắt fallback ký tự đặc biệt:

```powershell
python OCR_CTU_clean_v1\run_ocr.py "input\PDF_scan\Cong_van_282_-_Hoc_bong_SCIC_nam_2026.pdf" --no-symbol-fallback
```

## Ghi chú cho PDF scan có text layer lỗi

Một số PDF scan vẫn có text layer ẩn do OCR cũ tạo ra. Nếu text layer này bị lỗi kiểu `BQ GIAO Dl)C`, `TRUONGD~IHQccANTHa`, `DQc l~p`, chương trình sẽ tự bỏ text layer và OCR lại từ ảnh scan.

Chạy ép OCR lại từ ảnh:

```powershell
python OCR_PadViet_main/main.py "duong_dan_file.pdf" --force --force-ocr
```

`--force` dùng để ghi đè output cũ, còn `--force-ocr` dùng để bỏ qua text layer PDF.

## Ghi chú về PDF scan có text layer hỏng

Một số PDF scan nhìn bằng mắt vẫn rõ chữ nhưng bên trong có sẵn text layer OCR cũ bị sai. Bản này không bắt lỗi theo từng file cụ thể nữa, mà đánh giá text layer bằng điểm chất lượng tổng quát:

- tỷ lệ ký tự lạ trong chữ;
- token có số/ký hiệu chen giữa chữ;
- dấu hiệu mojibake/encoding hỏng;
- tỷ lệ dấu tiếng Việt quá thấp trong văn bản có ngữ cảnh tiếng Việt;
- trang có ảnh phủ gần toàn bộ trang nhưng text layer yếu.

Nếu text layer không đáng tin, chương trình tự bỏ text layer và OCR lại từ ảnh render. Muốn ép OCR toàn bộ PDF, dùng:

```powershell
python OCR_PadViet_main/main.py "duong_dan_file.pdf" --force --force-ocr
```
