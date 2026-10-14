# HỆ THỐNG QUẢN LÝ & KIỂM TRA HỒ SƠ ĐIỆN TỬ (NCKH)
## GIAI ĐOẠN 2: UPLOAD TÀI LIỆU & BÓC TÁCH VĂN BẢN (DOCUMENT PARSER)

> **Đề tài NCKH:** Xây dựng hệ thống tự động kiểm tra tính đầy đủ, hợp lệ và nhất quán của hồ sơ hợp đồng cung ứng lao động Việt Nam đi làm việc ở nước ngoài.  
> **Giai đoạn 1:** Khung ứng dụng Web FastAPI, CSDL quan hệ SQLAlchemy 2.x, SQLite, Alembic, CRUD và Giao diện quản lý Modern Tech Minimalist.  
> **Giai đoạn 2:** Upload tệp tin vật lý, bảo vệ an toàn tệp, bộ phân tích văn bản (PyMuPDF cho PDF, python-docx cho DOCX, đánh dấu needs_ocr cho JPG/PNG), lưu trữ văn bản theo trang (`document_pages`), giao diện Drag-and-Drop và Document Viewer 2 cột.

---

## 📌 Lưu ý Quan trọng về Tiền tố API
> [!NOTE]
> Trong tài liệu định hướng tổng thể đề tài (`Ke_hoach_phat_trien_he_thong_kiem_tra_ho_so_NCKH.md`), các endpoint được viết mẫu dưới dạng `/api/...` (không có `v1`).  
> Trong triển khai kỹ thuật chuẩn hóa của hệ thống, backend sử dụng tiền tố phiên bản **`/api/v1/...`** (ví dụ: `/api/v1/regulations`, `/api/v1/dossiers`, `/api/v1/documents`) nhằm đảm bảo tính tương thích ngược và mở rộng trong tương lai.

---

## ⚠️ Hạn chế Kỹ thuật Cần Lưu ý (Technical Limitations)
> [!WARNING]
> 1. **Thư viện python-docx:** Trích xuất văn bản từ thân tài liệu chính (`doc.element.body`), duyệt tuần tự theo thứ tự xuất hiện của các đoạn văn (`p`) và bảng biểu (`tbl`). Thư viện bỏ qua nội dung trong Header, Footer và các Hộp văn bản trôi nổi (Floating Text Box). Với DOCX, hệ thống chỉ báo lỗi `failed` khi toàn bộ văn bản sau khi strip rỗng hoàn toàn.
> 2. **Ngưỡng ký tự tối thiểu của PDF:** Đối với tệp tin PDF, nếu xuất hiện **bất kỳ một trang nào** có độ dài văn bản trích xuất dưới ngưỡng `PARSER_MIN_CHARS_PER_PAGE` (mặc định 20 ký tự, cấu hình qua `.env`) hoặc là trang scan hình ảnh, hệ thống sẽ tự động gắn cờ tài liệu là **`needs_ocr`** (Cần nhận dạng chữ) để sẵn sàng chuyển giao xử lý OCR ở Giai đoạn 3.

---

## 🏗️ Cấu trúc Thư mục Dự án

```
doc_checker_app/
│
├── .env.example                     # File mẫu biến môi trường (DATABASE_URL, STORAGE_DIR, MAX_UPLOAD_MB, ...)
├── .env                             # Cấu hình môi trường thực tế (không commit Git)
├── .gitignore                       # Bỏ qua file nhạy cảm, cache, venv, db, storage/*.bin
├── requirements.txt                 # Danh sách thư viện Python (FastAPI, PyMuPDF, python-docx, lxml, ...)
├── pytest.ini                       # Cấu hình test runner pytest
├── README.md                        # Hướng dẫn chi tiết này
│
├── storage/                         # Thư mục lưu trữ tệp tin vật lý gốc trên máy chủ
│   └── .gitkeep
│
├── backend/
│   ├── alembic.ini                  # Cấu hình Alembic migration
│   ├── alembic/
│   │   ├── env.py                   # Tự động trỏ DB tuyệt đối và render_as_batch=True cho SQLite
│   │   ├── script.py.mako           # Template migration
│   │   └── versions/                # Các phiên bản migration
│   │       ├── db115732abac_initial_schema.py             # Revision 001: regulations, dossiers, documents
│   │       └── cc825363f654_add_document_pages_and_parse_status.py # Revision 002: document_pages, parse_status
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # Khởi tạo FastAPI, CORS, phục vụ Static frontend tại "/"
│   │   ├── database.py              # Engine, PRAGMA foreign_keys=ON, UTCDateTime xử lý naive/aware
│   │   ├── models.py                # ORM Models: Regulation, Dossier, Document, DocumentPage
│   │   ├── schemas.py               # Pydantic v2 Schemas: DocumentOut (thêm parse_status, page_count), DocumentPageOut
│   │   ├── seed.py                  # Script nạp dữ liệu mẫu ban đầu (Idempotent)
│   │   ├── services/                # Tầng nghiệp vụ (Business Logic)
│   │   │   ├── document_parser.py   # Magic bytes detection, PyMuPDF parser, python-docx parser
│   │   │   ├── document_service.py  # Upload chunk stream, rollback an toàn, reparse giữ edited_text
│   │   │   ├── dossier_service.py   # Cascade soft delete & restore documents cùng đợt
│   │   │   └── regulation_service.py # Unique constraint, date validation, soft delete
│   │   └── routers/                 # Tầng API HTTP Controller (/api/v1)
│   │       ├── health.py            # GET /api/v1/health
│   │       ├── regulations.py       # CRUD & restore văn bản quy định
│   │       ├── dossiers.py          # CRUD, restore hồ sơ & POST /{id}/documents (Upload file)
│   │       └── documents.py         # GET /{id}/file, GET /{id}/pages, POST /{id}/parse, CRUD metadata
│   │
│   └── tests/                       # Bộ kiểm thử tự động pytest (28 test cases)
│       ├── conftest.py              # Fixture SQLite in-memory với StaticPool
│       ├── test_health.py           # Test health check
│       ├── test_regulations.py      # Test CRUD, unique, date validation, restore
│       ├── test_dossiers.py         # Test CRUD, cascade soft delete, cascade restore
│       ├── test_documents.py        # Test CRUD, ràng buộc dossier cha
│       └── test_upload_and_parser.py # Test upload PDF/DOCX/Ảnh, magic bytes, limit 413, 0-page, pass, reparse
│
└── frontend/                        # Giao diện Modern Tech Minimalist (FastAPI phục vụ tại "/")
    ├── index.html                   # Giao diện chính (Upload zone, 2-column Document Viewer modal)
    ├── css/
    │   └── style.css                # CSS tinh chỉnh phông chữ Plus Jakarta Sans, scrollbar
    └── js/
        ├── api.js                   # Client gọi API fetch tập trung & api.upload multipart/form-data
        ├── toast.js                 # Thông báo Toast đẹp mắt
        ├── regulations.js           # Xử lý giao diện Văn bản quy định
        ├── dossiers.js              # Quản lý Hồ sơ, Drag-and-Drop upload, Document Viewer 2 cột, Reparse
        └── app.js                   # Điều hướng chuyển tab & kiểm tra health
```

---

## ⚡ Hướng dẫn Cài đặt & Chạy trên Windows (PowerShell)

> [!IMPORTANT]
> **Quy tắc thư mục làm việc:**  
> Mở PowerShell và di chuyển vào duy nhất một thư mục gốc dự án:  
> `cd d:\doc_checker_app`  
> MỌI lệnh bên dưới đều được thực hiện từ thư mục gốc này!

### Bước 1: Kích hoạt môi trường ảo (.venv)
```powershell
.\.venv\Scripts\Activate.ps1
```

### Bước 2: Cài đặt các thư viện mới nhất
```powershell
.\.venv\Scripts\pip install -r requirements.txt
```

### Bước 3: Cấu hình biến môi trường (.env)
Đảm bảo file `.env` đã có các biến môi trường của Giai đoạn 2:
```env
DATABASE_URL=sqlite:///./app.db
CORS_ORIGINS=http://localhost:8000
STORAGE_DIR=storage
MAX_UPLOAD_MB=20
PARSER_MIN_CHARS_PER_PAGE=20
```

### Bước 4: Chạy Alembic Migration (Nâng cấp schema)
```powershell
.\.venv\Scripts\alembic upgrade head
```

### Bước 5: Chạy Server FastAPI & Mở Giao diện
```powershell
.\.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Truy cập trình duyệt:
- 🖥️ **Giao diện Web:** [http://localhost:8000](http://localhost:8000)
- 📖 **Swagger API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- 🩺 **Health Check:** [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

---

## 📡 Danh sách Endpoints API Giai đoạn 2

| Method | Endpoint | Mô tả |
|---|---|---|
| `POST` | `/api/v1/dossiers/{id}/documents` | **Upload tệp tin**: Nhận `multipart/form-data`, kiểm tra magic bytes, lưu file vật lý vào `storage/` theo tên UUID hex, tự động bóc tách text và lưu `document_pages`. |
| `GET` | `/api/v1/documents/{id}/file` | **Tải / xem file gốc**: Phục vụ xem trước (preview) hoặc tải về, tiêu đề RFC 5987 hỗ trợ tên tiếng Việt UTF-8, header `X-Content-Type-Options: nosniff`. |
| `GET` | `/api/v1/documents/{id}/pages` | **Danh sách trang & text**: Trả về các trang đã bóc tách (`page_number`, `raw_text`, `edited_text`, `parser_type`, `engine_version`). |
| `POST` | `/api/v1/documents/{id}/parse` | **Phân tích lại (Reparse)**: Bóc tách lại từ file gốc, thay thế trang cũ bằng trang mới trong cùng 1 transaction, **bảo lưu `edited_text`** nếu trùng `page_number`. |

---

## 🧪 Chạy Toàn bộ Kiểm thử Tự động (Pytest)

Chạy 28 bài kiểm thử tự động (14 bài Giai đoạn 1 + 14 bài Giai đoạn 2):
```powershell
.\.venv\Scripts\pytest -v
```

Kết quả: **28 passed in < 2s**.

### Danh sách kịch bản kiểm thử Giai đoạn 2:
1. `test_upload_valid_pdf`: Upload PDF 2 trang chuẩn, bóc tách text từng trang, SHA-256, kích thước, tải file qua endpoint `/file`.
2. `test_upload_pdf_short_or_scanned_marks_needs_ocr`: PDF có trang < 20 ký tự được gắn cờ `needs_ocr`, vẫn lưu trang để xem trước.
3. `test_upload_pdf_password_protected`: PDF có mật khẩu -> `parse_status='failed'`, thông báo "PDF được bảo vệ bằng mật khẩu".
4. `test_upload_pdf_zero_pages`: PDF 0 trang -> `parse_status='failed'`, thông báo "PDF không có trang nào hoặc bị hỏng".
5. `test_upload_valid_docx`: Upload DOCX chứa văn bản và bảng biểu, bóc tách thành 1 trang với `python-docx`.
6. `test_upload_empty_docx_fails`: DOCX không có chữ -> `parse_status='failed'`, thông báo "DOCX không có nội dung văn bản".
7. `test_upload_image_marks_needs_ocr`: Upload ảnh JPG/PNG -> gắn cờ `needs_ocr`, không tạo trang text ở Giai đoạn 2.
8. `test_upload_legacy_doc_rejected_415`: File Word cũ `.doc` (OLE binary) bị từ chối với HTTP 415.
9. `test_upload_fake_pdf_magic_bytes_rejected_415`: File văn bản đổi đuôi `.pdf` bị từ chối bằng kiểm tra Magic Bytes (HTTP 415).
10. `test_upload_file_size_exceeded_413`: File vượt quá `MAX_UPLOAD_MB=1` bị ngắt stream ngay và trả về HTTP 413.
11. `test_upload_to_nonexistent_or_deleted_dossier`: Chặn upload vào hồ sơ không tồn tại (404) hoặc hồ sơ đã xóa mềm (400).
12. `test_reparse_preserves_edited_text`: Gọi reparse thay thế trang cũ bằng trang mới nhưng bảo lưu chính xác `edited_text`.
13. `test_reparse_document_without_file_returns_400`: Reparse tài liệu chỉ có metadata (chưa có file vật lý) trả về HTTP 400.
14. `test_soft_delete_retains_physical_file`: Xóa mềm tài liệu không xóa file vật lý trên đĩa; khôi phục thì xem lại được bình thường.
