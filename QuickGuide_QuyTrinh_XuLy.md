# Quick Guide - Quy trình xử lý tài liệu từng bước cho NLCS RAG

File này dùng để xem nhanh trong quá trình **formatter, OCR, chuẩn hóa Markdown, kiểm tra metadata, review, publish và đưa tài liệu vào RAG**.

---

## 0. Nguyên tắc cốt lõi

```text
PDF/DOCX/Image gốc = nguồn đối chiếu/audit
Markdown trong 01_Dataset = nguồn chính để chunk + embedding
Backend = validate metadata + chunking + embedding + index Qdrant
Qdrant = lưu vector chunks đã được publish
```

Không đưa tài liệu vào RAG nếu chưa đủ điều kiện:

```yaml
ocr_status: "done"
review_status: "approved"
validity_status: "valid"
rag_status: "published"
confidentiality: "public"
```

Nếu tài liệu **chưa xác định hiệu lực**:

```yaml
validity_status: "unchecked"
rag_status: "not_indexed"
```

Nếu tài liệu **đã bị thay thế**:

```yaml
validity_status: "replaced"
rag_status: "deactivated"
is_latest: false
```

---

## 1. Luồng tổng quát

```text
1. Thu thập tài liệu gốc
   ↓
2. Lưu file gốc vào 02_Attachments
   ↓
3. OCR / Parser tài liệu ra Markdown
   ↓
4. Lưu bản OCR tạm vào 06_Processing/OCR_Output
   ↓
5. Làm sạch Markdown
   ↓
6. Tạo file Markdown chính trong 01_Dataset
   ↓
7. Điền YAML metadata
   ↓
8. Kiểm tra version và hiệu lực
   ↓
9. Review nội dung
   ↓
10. Đánh dấu approved + valid
   ↓
11. Publish cho RAG
   ↓
12. Backend validate metadata
   ↓
13. Chunking từ Markdown
   ↓
14. Embedding
   ↓
15. Index vào Qdrant
   ↓
16. Active Knowledge Base
```

---

## 2. Bước 1 - Thu thập tài liệu gốc

### Mục tiêu

Thu thập file gốc từ website trường, phòng ban, biểu mẫu hoặc tài liệu nội bộ.

### File đầu vào

```text
PDF
DOCX
Image scan
Form
HTML / webpage
```

### Việc cần làm

- Kiểm tra nguồn lấy tài liệu.
- Ghi lại ngày truy cập.
- Không đổi nội dung file gốc.
- Không xóa file cũ nếu có tài liệu mới hơn.

### Metadata cần ghi

```yaml
source_url: ""
source_file: ""
accessed_date: ""
collection_status: "collected"
```

---

## 3. Bước 2 - Lưu file gốc vào `02_Attachments`

### Vị trí lưu

```text
02_Attachments/PDFs/<Đơn vị>/
02_Attachments/DOCX/
02_Attachments/Forms/
02_Attachments/Images/
```

### Ví dụ

```text
02_Attachments/PDFs/PDT/QD1813_QD_ban_hanh_Quy_dinh_cong_tac_hoc_vu_2021.pdf
```

### Checklist

- [ ] File mở được.
- [ ] Tên file dễ nhận biết.
- [ ] Đặt đúng đơn vị/lĩnh vực.
- [ ] Không lưu file gốc trong `01_Dataset`.

---

## 4. Bước 3 - OCR / Parser ra Markdown

### Mục tiêu

Chuyển tài liệu gốc thành Markdown có cấu trúc.

### Output tạm

```text
06_Processing/OCR_Output/<ten_file>_ocr.md
```

### Cần giữ lại

- Heading.
- Chương / Điều / Khoản / Điểm.
- Bảng.
- Danh sách.
- Số trang.
- Biểu mẫu / link nếu có.

### Không cần giữ

- Font chữ.
- Căn lề.
- Header/footer lặp lại.
- Dấu trang trí.
- Khoảng trắng thừa.

### Page marker

Dùng để citation:

```markdown
<!-- page: 1 -->

Nội dung trang 1...

<!-- page: 2 -->

Nội dung trang 2...
```

---

## 5. Bước 4 - Làm sạch Markdown

### Mục tiêu

Biến bản OCR tạm thành Markdown chuẩn để quản lý và chunking.

### Cần kiểm tra

- [ ] Không mất dấu tiếng Việt.
- [ ] Heading đúng cấp.
- [ ] Bảng không bị vỡ.
- [ ] Danh sách không bị dính dòng.
- [ ] Nội dung không bị lặp header/footer.
- [ ] Page marker đúng vị trí.
- [ ] Không tự ý diễn giải lại văn bản gốc.

### Lưu ý quan trọng

Formatter chỉ được **chuẩn hóa hình thức**, không được tự sửa nội dung nghiệp vụ nếu không có căn cứ.

Sai:

```text
Tự đổi Phòng Công tác Sinh viên thành Phòng Đào tạo.
```

Đúng:

```text
Giữ nguyên tên đơn vị theo tài liệu gốc.
```

---

## 6. Bước 5 - Tạo file Markdown chính trong `01_Dataset`

### Vị trí lưu

```text
01_Dataset/<Đơn vị hoặc Lĩnh vực>/<ten_tai_lieu>.md
```

### Ví dụ

```text
01_Dataset/PDT/QD1813_QuyDinhCongTacHocVu_2021.md
```

### File này là gì?

Đây là **canonical Markdown**:

```text
File chính dùng để review, chunk, embedding và đưa vào RAG.
```

Không dùng raw OCR text làm nguồn chính cho RAG nếu Markdown đã được chuẩn hóa tốt hơn.

---

## 7. Bước 6 - Điền YAML metadata

### Template tối thiểu

```yaml
---
document_id: ""
version_id: ""
title: ""

document_type: ""
domain: ""
department: ""
audience:
  - "student"

code: ""
issued_date:
effective_date:
expiry_date:
version: ""

is_latest: false
validity_status: "unchecked"
replaces:
replaced_by:
supersession_note:

collection_status: "collected"
ocr_status: "done"
review_status: "not_reviewed"
rag_status: "not_indexed"

source_url: ""
source_file: ""
file_type: "pdf"
accessed_date:

language: "vi"
confidentiality: "public"
priority: "medium"
citation_type: "page"
chunking_strategy: "heading_based"

created_at:
updated_at:
checksum:
parser:
parser_version:
ocr_engine:
ocr_confidence:
notes:

tags:
  - ctu
---
```

---

## 8. Bước 7 - Kiểm tra `document_id` và `version_id`

### Quy tắc

```text
document_id = ID chung của cùng một nhóm tài liệu
version_id = ID riêng của từng phiên bản cụ thể
```

### Ví dụ

Bản năm 2021:

```yaml
document_id: "ctu-quy-dinh-hoc-vu"
version_id: "ctu-qd1813-2021"
version: "2021"
```

Bản năm 2024:

```yaml
document_id: "ctu-quy-dinh-hoc-vu"
version_id: "ctu-qdxxxx-2024"
version: "2024"
```

### Checklist

- [ ] `document_id` đúng nhóm tài liệu.
- [ ] `version_id` không trùng bản khác.
- [ ] Không overwrite file version cũ.
- [ ] Nếu có bản mới, tạo file Markdown mới.

---

## 9. Bước 8 - Kiểm tra hiệu lực tài liệu

### Trường hợp chưa kiểm tra được

```yaml
validity_status: "unchecked"
is_latest: false
rag_status: "not_indexed"
```

Không publish.

### Trường hợp còn hiệu lực

```yaml
validity_status: "valid"
is_latest: true
```

Có thể xét publish nếu đã review.

### Trường hợp hết hạn

```yaml
validity_status: "expired"
is_latest: false
rag_status: "deactivated"
```

Không dùng cho chatbot mặc định.

### Trường hợp bị thay thế

```yaml
validity_status: "replaced"
is_latest: false
replaced_by: "<version_id_moi>"
rag_status: "deactivated"
```

---

## 10. Bước 9 - Review nội dung

### Khi đang review

```yaml
review_status: "reviewing"
```

### Nếu cần sửa

```yaml
review_status: "need_fix"
```

### Nếu đã duyệt

```yaml
review_status: "approved"
```

### Checklist review

- [ ] Tiêu đề đúng.
- [ ] Số hiệu đúng.
- [ ] Ngày ban hành đúng.
- [ ] Đơn vị phụ trách đúng.
- [ ] Nội dung OCR đủ.
- [ ] Heading đúng cấp.
- [ ] Bảng đúng cột/dòng.
- [ ] Có page marker.
- [ ] Đã kiểm tra hiệu lực.
- [ ] Không có thông tin nhạy cảm ngoài phạm vi công khai.

---

## 11. Bước 10 - Quyết định publish vào RAG

### Chỉ publish khi

```yaml
ocr_status: "done"
review_status: "approved"
validity_status: "valid"
rag_status: "published"
confidentiality: "public"
```

Nếu dùng rule nghiêm ngặt:

```yaml
is_latest: true
```

### Không publish khi

```text
validity_status = unchecked
validity_status = unknown
validity_status = expired
validity_status = replaced
review_status != approved
ocr_status != done
confidentiality != public
```

---

## 12. Bước 11 - Copy sang `04_RAG/Published` nếu dùng MVP workflow

Có 2 cách vận hành.

### Cách A - Backend đọc trực tiếp từ `01_Dataset`

Backend scan file có metadata hợp lệ.

### Cách B - Copy file đã duyệt sang `04_RAG/Published`

```text
04_RAG/Published/<ten_file>.md
```

Khuyến nghị MVP: dùng Cách B để dễ kiểm soát và demo.

---

## 13. Bước 12 - Backend validate metadata

Backend cần kiểm tra:

```text
document_id
version_id
title
document_type
domain
department
audience
ocr_status
review_status
rag_status
validity_status
confidentiality
source_file/source_url
```

### Rule backend

```text
IF review_status = approved
AND ocr_status = done
AND rag_status = published
AND validity_status = valid
AND confidentiality = public
AND effective_date <= today
AND (expiry_date is empty OR expiry_date >= today)
THEN ingest
ELSE skip
```

Nếu yêu cầu chỉ lấy bản mới nhất:

```text
AND is_latest = true
```

---

## 14. Bước 13 - Chunking từ Markdown

### Nguyên tắc

Chunk theo heading, không cắt ngẫu nhiên.

Ưu tiên:

```text
# Tài liệu
## Chương
### Điều
#### Khoản
```

### Mỗi chunk cần metadata

```json
{
  "document_id": "",
  "version_id": "",
  "title": "",
  "heading_path": "",
  "page_start": 1,
  "page_end": 1,
  "document_type": "",
  "department": "",
  "domain": "",
  "validity_status": "valid",
  "rag_status": "published"
}
```

---

## 15. Bước 14 - Embedding

### Input embedding

Nên embed:

```text
Title
Heading path
Metadata context ngắn
Chunk content
```

Ví dụ:

```text
Tài liệu: Quy định công tác học vụ
Đơn vị: Phòng Đào tạo
Mục: Chương II > Điều 5

<Nội dung chunk>
```

### Không embed

- File chưa review.
- File chưa valid.
- File bị replaced.
- File deactivated.
- File private/restricted nếu chưa có quyền truy cập.

---

## 16. Bước 15 - Qdrant indexing

### Payload cần có

```json
{
  "chunk_id": "",
  "document_id": "",
  "version_id": "",
  "title": "",
  "document_type": "",
  "domain": "",
  "department": "",
  "audience": ["student"],
  "version": "",
  "is_latest": true,
  "validity_status": "valid",
  "rag_status": "published",
  "confidentiality": "public",
  "page_start": 1,
  "page_end": 1,
  "source_url": "",
  "source_file": ""
}
```

### Retriever mặc định chỉ lấy

```text
rag_status = published
validity_status = valid
confidentiality = public
```

Nếu cần nghiêm ngặt:

```text
is_latest = true
```

---

## 17. Bước 16 - Khi tài liệu bị thay thế

### File cũ

```yaml
is_latest: false
validity_status: "replaced"
replaced_by: "<version_id_moi>"
rag_status: "deactivated"
```

### File mới

```yaml
is_latest: true
validity_status: "valid"
replaces: "<version_id_cu>"
review_status: "approved"
rag_status: "published"
```

### Qdrant vector cũ

Không cần xóa ngay. Cập nhật payload:

```json
{
  "rag_status": "deactivated",
  "validity_status": "replaced",
  "is_latest": false,
  "replaced_by": "<version_id_moi>"
}
```

---

## 18. Bảng quyết định nhanh

| Tình huống | Metadata cần đặt | Có đưa vào RAG không? |
|---|---|---|
| Mới thu thập | `ocr_status: "not_started"` | Không |
| Đã OCR, chưa review | `review_status: "not_reviewed"` | Không |
| Đang sửa lỗi OCR | `review_status: "need_fix"` | Không |
| Chưa kiểm tra hiệu lực | `validity_status: "unchecked"` | Không |
| Không xác định hiệu lực | `validity_status: "unknown"` | Không |
| Đã duyệt, còn hiệu lực | `review_status: "approved"`, `validity_status: "valid"` | Có thể |
| Đã publish | `rag_status: "published"` | Có |
| Bị thay thế | `validity_status: "replaced"`, `rag_status: "deactivated"` | Không |
| Hết hạn | `validity_status: "expired"`, `rag_status: "deactivated"` | Không |
| Tài liệu nội bộ | `confidentiality: "internal"` | Không public chatbot |
| Tài liệu hạn chế | `confidentiality: "restricted"` | Không public chatbot |

---

## 19. Checklist cuối trước khi active

- [ ] File gốc nằm trong `02_Attachments`.
- [ ] File Markdown chính nằm trong `01_Dataset`.
- [ ] Có `document_id`.
- [ ] Có `version_id`.
- [ ] YAML đầy đủ.
- [ ] OCR hoàn tất.
- [ ] Review đã approved.
- [ ] Hiệu lực là valid.
- [ ] Nếu có bản mới/cũ, đã điền `replaces` hoặc `replaced_by`.
- [ ] Không phải tài liệu replaced/expired.
- [ ] Không phải tài liệu restricted.
- [ ] Có page marker nếu citation theo trang.
- [ ] Đã chunk preview nếu cần.
- [ ] Đã publish cho RAG.
- [ ] Backend validate pass.
- [ ] Đã index Qdrant.
- [ ] Test truy vấn thử có citation đúng.

---

## 20. Công thức nhớ nhanh

```text
Unchecked thì không publish.
Replaced thì deactivated.
Approved + Valid mới được publish.
Markdown trong 01_Dataset là nguồn chính.
PDF trong 02_Attachments là nguồn đối chiếu.
Qdrant chỉ nhận chunk từ Markdown đã duyệt.
```

---

## 21. Lỗi thường gặp

### Lỗi 1: Dùng `status` chung chung

Sai:

```yaml
status: "Đã thu thập"
```

Đúng:

```yaml
collection_status: "collected"
ocr_status: "done"
review_status: "approved"
rag_status: "published"
validity_status: "valid"
```

### Lỗi 2: Đưa file `unchecked` vào RAG

Sai:

```yaml
validity_status: "unchecked"
rag_status: "published"
```

Đúng:

```yaml
validity_status: "unchecked"
rag_status: "not_indexed"
```

### Lỗi 3: Tài liệu bị thay thế nhưng vẫn published

Sai:

```yaml
validity_status: "replaced"
rag_status: "published"
```

Đúng:

```yaml
validity_status: "replaced"
rag_status: "deactivated"
```

### Lỗi 4: Ghi đè tài liệu cũ bằng bản mới

Sai:

```text
QD1813_QuyDinhHocVu_2021.md
```

rồi sửa thành nội dung năm 2024.

Đúng:

```text
QD1813_QuyDinhHocVu_2021.md
QDxxxx_QuyDinhHocVu_2024.md
```

---

## 22. Dataview kiểm tra nhanh

### Tài liệu chưa kiểm tra hiệu lực

```dataview
TABLE document_id, version_id, title, validity_status, rag_status
FROM "01_Dataset"
WHERE validity_status = "unchecked" OR validity_status = "unknown"
SORT updated_at DESC
```

### Tài liệu bị thay thế nhưng chưa deactivate

```dataview
TABLE document_id, version_id, title, validity_status, rag_status, replaced_by
FROM "01_Dataset"
WHERE validity_status = "replaced" AND rag_status != "deactivated"
SORT updated_at DESC
```

### Tài liệu đủ điều kiện publish

```dataview
TABLE document_id, version_id, title, review_status, ocr_status, validity_status, rag_status
FROM "01_Dataset"
WHERE review_status = "approved"
AND ocr_status = "done"
AND validity_status = "valid"
AND confidentiality = "public"
SORT updated_at DESC
```

### Tài liệu đã publish

```dataview
TABLE document_id, version_id, title, is_latest, validity_status, rag_status
FROM "01_Dataset"
WHERE rag_status = "published"
SORT updated_at DESC
```

---

## 23. Kết luận

Quy trình đúng:

```text
File gốc
  ↓
OCR/Parser
  ↓
Markdown chuẩn
  ↓
Metadata + Version validation
  ↓
Review
  ↓
Approved + Valid
  ↓
Published
  ↓
Chunking
  ↓
Embedding
  ↓
Qdrant
  ↓
Active Knowledge Base
```

Không đưa tài liệu chưa rõ hiệu lực, chưa review hoặc đã bị thay thế vào chatbot mặc định.
