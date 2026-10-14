TÀI LIỆU ĐỊNH HƯỚNG TRIỂN KHAI

KẾ HOẠCH PHÁT TRIỂNHỆ THỐNG KIỂM TRAHỒ SƠ HỢP ĐỒNG CUNG ỨNG

Web Application  •  OCR  •  LLM  •  Rule-based Validation

ĐỊNH HƯỚNG SẢN PHẨM

Một ứng dụng web hỗ trợ nhập, lưu và xử lý bộ hồ sơ nhiều tài liệu; tự động đọc văn bản bằng Parser/OCR, dùng LLM trích xuất trường dữ liệu, đối chiếu liên văn bản và kiểm tra quy tắc nghiệp vụ có truy vết bằng chứng.

THÔNG TIN

NỘI DUNG

Phạm vi

Hồ sơ hợp đồng cung ứng lao động Việt Nam đi làm việc ở nước ngoài

Môi trường phát triển

Windows; chạy local trên máy thành viên trong giai đoạn đầu

Mục tiêu MVP

Một luồng end-to-end: Upload → OCR/Parsing → LLM → Validation → Report

Thời gian dự kiến

8–10 tuần; điều chỉnh theo nhân lực và mức độ sẵn có của dữ liệu

Phiên bản tài liệu

1.0  |  12/10/2026

Tóm tắt quyết định triển khai

Không triển khai tất cả thành phần AI từ ngày đầu; xây hệ thống quản lý tài liệu, upload và parser trước.

Bắt đầu bằng một backend FastAPI duy nhất, frontend React, SQLite và lưu file trên ổ đĩa; chưa cần Linux, Docker, microservices.

OCR/LLM phục vụ đọc và trích xuất; code/rule engine phục vụ so sánh các điều kiện xác định.

Đánh giá nghiên cứu phải có dataset, baseline, metrics và bằng chứng cho từng kết luận kiểm tra.

1. Mục tiêu, phạm vi và nguyên tắc thiết kế

1.1. Mục tiêu theo hai lớp

LỚP

MỤC TIÊU

ĐẦU RA

Sản phẩm web

FE/BE/DB quản lý văn bản quy định và bộ hồ sơ; upload và xem file; chạy pipeline AI.

Bản demo hoạt động trên Windows.

Nghiên cứu

So sánh các phương pháp trích xuất và kiểm tra; đo lường độ chính xác và lỗi nhận nhầm.

Bộ dữ liệu gán nhãn + báo cáo thực nghiệm.

1.2. Đối tượng dữ liệu cần tách biệt

Văn bản quy định (regulations): thông tin pháp lý, điều khoản, ngày hiệu lực, phiên bản, nguồn ban hành và bộ quy tắc gắn tương ứng.

Bộ hồ sơ (dossiers): một trường hợp cần thẩm định, gồm nhiều tài liệu (documents) và những lần chạy kiểm tra (validation runs).

Kết quả AI (extractions): text, trường đã trích xuất, độ tin cậy/đánh dấu cần kiểm tra, nguồn file, số trang và đoạn chứng cứ.

1.3. Quy mô thực hiện

PHIÊN BẢN

TÀI LIỆU

TRƯỜNG THÔNG TIN

QUY TẮC

MVP đầu tiên

3–4 loại

5–10 trường

3–5 quy tắc minh họa có căn cứ

Mục tiêu nghiên cứu

5–7 loại

20–40 trường

15–30 quy tắc, nếu đủ dữ liệu và thời gian

NGUYÊN TẮC QUAN TRỌNG

Mô hình LLM không có quyền tự kết luận pháp lý cuối cùng chỉ bằng một câu trả lời tự do. Kết quả kiểm tra phải qua các rule được xác minh và có ba trạng thái: PASS / FAIL / NEED REVIEW. Hệ thống là công cụ hỗ trợ thẩm định, không thay thế cán bộ hoặc chuyên gia.

2. Kiến trúc công nghệ đề xuất

LỚP

CÔNG NGHỆ

TRÁCH NHIỆM

Frontend

Tự chọn

CRUD, upload, preview, bảng so sánh và báo cáo.

Backend

Tự chọn (nên dùng NodeJS)

API, điều phối xử lý, quản lý hồ sơ.

Database

SQLite → PostgreSQL/SQL Server?

Lưu metadata, text, thông tin trích xuất, rule, kết quả.

Lưu trữ file

Thư mục storage/ local

Giữ PDF, DOCX, ảnh gốc; chỉ lưu đường dẫn trong DB.

Parser

PyMuPDF, python-docx

Đọc PDF có text và DOCX; giữ số trang/nguồn.

OCR

Tesseract (bắt đầu); thử PaddleOCR, olmOCR

Đọc ảnh và PDF scan tiếng Việt.

LLM

API hoặc Ollama trên Windows, vLLM

Trích xuất các trường theo schema JSON.

Kiểm tra

Pydantic + Python Rule Engine

Chuẩn hóa, so khớp, kiểm tra logic xác định.

Luồng xử lý end-to-end

UPLOAD  →  FILE DETECTION  →  PARSER/OCR  →  LLM EXTRACTION  →  NORMALIZATION  →  CROSS-DOCUMENT CHECK  →  BUSINESS RULES  →  EVIDENCE REPORT

Khuyến nghị: tất cả service đặt trong cùng project Backend trong giai đoạn đầu. Khi pipeline ổn định mới cân nhắc hàng đợi xử lý hoặc tách service.

3. Roadmap triển khai 8–10 tuần

TUẦN

CÔNG VIỆC TRỌNG TÂM

MỐC NGHIỆM THU

1–2

CRUD + Database + API; quản lý quy định, dossier, document.

Tạo/sửa/xóa/lấy lại bộ hồ sơ qua web.

3

Upload và Text Parser (PDF có text, DOCX).

Xem file gốc và text theo trang.

4

Tích hợp OCR cho scan/ảnh; sửa text đọc sai.

OCR lưu text + page + nguồn.

5

LLM trích xuất JSON có cấu trúc; kiểm tra schema.

Trích xuất 5–10 trường từ 2 loại tài liệu.

6

Chuẩn hóa tên, ngày, số, quốc gia; so khớp entity.

Phân biệt tương đương và khác biệt.

7

Đối chiếu thông tin nhiều tài liệu.

Phát hiện lệch số người / doanh nghiệp / quốc gia.

8

Bộ quy tắc nghiệp vụ và liên kết căn cứ pháp lý.

Có PASS / FAIL / REVIEW theo rule.

9

UI báo cáo, liên kết chứng cứ, kiểm thử tổng thể.

Demo end-to-end với một bộ hồ sơ.

10

Gán nhãn, chạy baselines, đo metrics, tổng kết.

Bảng kết quả thực nghiệm và tài liệu NCKH.

Mốc thời gian là dự kiến. Có thể phát triển OCR/LLM độc lập trong script Python song song với Frontend, miễn là giao diện API và schema đã được thống nhất.

4. Chi tiết các giai đoạn và đầu ra

Giai đoạn 1 — CRUD và cơ sở dữ liệu

Mục tiêu: Xây được khung website mà chưa cần AI.

Tạo bảng regulations, dossiers, documents (có liên kết khóa ngoại).

Viết API tạo/lấy/sửa/xóa mềm; kiểm thử bằng FastAPI /docs hoặc Postman.

Thiết kế màn hình danh sách và chi tiết bộ hồ sơ; tách dữ liệu quy định với hồ sơ cần kiểm tra.

Ở văn bản quy định, lưu số hiệu, ngày hiệu lực, nguồn và phiên bản.

Đầu ra: Web quản lý dữ liệu thực với FE–BE–DB liên thông.

Tiêu chí nghiệm thu: Tải lại trang không mất dữ liệu; không nhầm văn bản quy định với tài liệu hồ sơ.

Giai đoạn 2 — Upload và Document Parser

Mục tiêu: Cho phép tải và xử lý file nguồn.

Hỗ trợ bước đầu PDF có text, DOCX, JPG/PNG; giới hạn dung lượng và loại file.

Lưu file gốc vào storage/ bằng tên nội bộ, lưu metadata/đường dẫn trong database.

Đọc PDF có text qua PyMuPDF, DOCX qua python-docx; lưu raw text theo trang và nguồn.

Hiển thị preview file và text đã đọc trên web.

Đầu ra: API upload, API parse; dữ liệu text gắn document_id/page.

Tiêu chí nghiệm thu: Upload PDF có text và DOCX, hiển thị nội dung và không làm mất file gốc.

Giai đoạn 3 — OCR cho PDF scan và ảnh

Mục tiêu: Chuyển trang scan/ảnh thành text để downstream xử lý.

Cài Tesseract Windows và gói ngôn ngữ tiếng Việt (vie); viết ocr_service.py.

Với PDF không có lớp text đáng tin cậy, render từng trang thành ảnh để OCR.

Lưu kết quả OCR theo trang; nếu có, giữ bounding box và điểm tin cậy từ OCR engine.

Cho phép xem/sửa text OCR nhưng luôn giữ text gốc để phục vụ đánh giá.

Đầu ra: Đầu ra OCR có document_id, page, text, engine_version.

Tiêu chí nghiệm thu: Một PDF scan được chuyển thành văn bản, có ghi nhận trang và có thể kiểm tra thủ công.

Giai đoạn 4 — LLM Information Extraction

Mục tiêu: Chuyển văn bản phi cấu trúc thành JSON nhất quán.

Chốt schema từng loại tài liệu: contract, license, approval, worker_list.

Gửi text theo trang (và chỉ phần liên quan khi tài liệu dài) cho LLM; yêu cầu JSON có cấu trúc.

Dùng Pydantic xác thực định dạng và kiểu dữ liệu; quản lý trường thiếu/null.

Với mỗi giá trị, lưu đoạn trích dẫn, trang và nguồn; không mặc định coi confidence tự khai của LLM là xác suất đúng.

Đầu ra: JSON trích xuất được lưu DB và truy vết về văn bản.

Tiêu chí nghiệm thu: Trích xuất đúng định dạng các trường thử nghiệm (doanh nghiệp, quốc gia, số lao động, ngày ký…).

Giai đoạn 5 — Schema Normalization và Entity Matching

Mục tiêu: Đưa các biểu diễn khác nhau về cùng một dạng có thể so sánh.

Chuẩn hóa chữ hoa/thường, khoảng trắng, quốc gia, ngày tháng và số.

Ưu tiên mã định danh doanh nghiệp/giấy phép; fuzzy hoặc semantic matching chỉ khi cần.

Lưu cả original_value và normalized_value để có thể giải thích kết quả.

Đầu ra: Hàm normalization độc lập, có unit tests.

Tiêu chí nghiệm thu: "Japan" và "Nhật Bản" được nhận ra là cùng quốc gia; giá trị 118 và 120 không bị đánh đồng.

Giai đoạn 6 — Cross-document Consistency Checking

Mục tiêu: Phát hiện dữ liệu không khớp giữa các tài liệu.

Định nghĩa quan hệ cần so: contract–approval, contract–license, contract–worker_list.

Thực hiện so sánh sau chuẩn hóa; phân biệt MATCH / MISMATCH / MISSING / UNCERTAIN.

Trả từng cặp giá trị kèm document, page và evidence.

Đầu ra: Danh sách inconsistency theo trường và tài liệu.

Tiêu chí nghiệm thu: Phát hiện ví dụ 120 người trong hợp đồng, 118 người trong chấp thuận mà không báo sai hai cách viết đồng nghĩa.

Giai đoạn 7 — Business Rule Engine và căn cứ quy định

Mục tiêu: Áp dụng các điều kiện nghiệp vụ đã được chuyên gia/nhóm xác minh.

Xây danh mục rule_id, mô tả, toán tử, trường sử dụng, loại tài liệu và căn cứ điều khoản.

Code hóa kiểm tra xác định bằng Python; tách rule khỏi prompt LLM.

Gắn từng rule với phiên bản văn bản quy định và mốc thời gian áp dụng.

Nếu thiếu dữ liệu hoặc không chắc chắn, trả NEED REVIEW thay vì ép PASS/FAIL.

Đầu ra: Mỗi rule có trạng thái, lý do, bằng chứng, điều khoản liên quan.

Tiêu chí nghiệm thu: Ít nhất 3–5 rule minh họa được kiểm thử bằng tình huống đúng/sai/thiếu dữ liệu.

Giai đoạn 8 — Báo cáo và đánh giá nghiên cứu

Mục tiêu: Cung cấp giao diện có thể kiểm toán và chứng minh được hiệu quả phương pháp.

Thiết kế dashboard theo bộ hồ sơ: số rule PASS/FAIL/REVIEW và danh sách lỗi.

Nhấn vào lỗi mở tài liệu nguồn đúng trang; cho phép người dùng phản hồi/sửa lỗi trích xuất.

Chuẩn bị ground truth và chạy so sánh ba baseline.

Báo cáo Accuracy, Precision/Recall/F1, False PASS và thời gian xử lý.

Đầu ra: MVP chạy end-to-end + bảng kết quả thực nghiệm.

Tiêu chí nghiệm thu: Một bộ hồ sơ thử nghiệm đi từ upload đến report, tất cả kết luận đều có thể truy lại nguồn.

5. Thiết kế dữ liệu và giao diện API cơ bản

5.1. Những bảng dữ liệu tối thiểu

BẢNG

THÔNG TIN LƯU

regulations

id, title, identifier, effective_from/to, version, source_url, file_path

dossiers

id, name, status, created_at, updated_at

documents

id, dossier_id, document_type, original_name, storage_path, mime_type, uploaded_at

document_pages

id, document_id, page_number, parser_type, raw_text, edited_text

extracted_fields

id, document_id, field_name, value_raw, value_normalized, page, evidence, review_status

rules

id, name, description, legal_basis_id, valid_from/to, rule_version

validation_results

id, dossier_id, rule_id, status, reason, evidence_json, run_id

Các trường trên là định hướng logic; cần chốt naming và quan hệ khóa ngoại trước khi bắt đầu code. Nên lưu lịch sử lần kiểm tra (run_id) để so sánh kết quả theo thời gian.

5.2. Danh sách API triển khai theo thứ tự

PHƯƠNG THỨC / ENDPOINT

MỤC ĐÍCH

GET /api/regulations

Liệt kê văn bản quy định

POST /api/regulations

Thêm văn bản quy định

POST /api/dossiers

Tạo bộ hồ sơ

GET /api/dossiers/{id}

Lấy chi tiết hồ sơ

POST /api/dossiers/{id}/documents

Upload tài liệu

POST /api/documents/{id}/parse

Parser hoặc OCR

POST /api/documents/{id}/extract

Trích xuất LLM theo schema

POST /api/dossiers/{id}/validate

Đối chiếu và chạy rule

GET /api/dossiers/{id}/report

Lấy báo cáo đầy đủ

6. Cấu trúc thư mục và thiết lập Windows

6.1. Cấu trúc project đề xuất

document-validation-system/

  frontend/src/{pages,components,services}/

  backend/app/main.py

  backend/app/{routers,models,schemas}/

  backend/app/services/

    document_parser.py  |  ocr_service.py

    llm_service.py      |  normalizer.py

    validation_engine.py  |  report_service.py

  storage/       # File gốc, không đưa lên Git

  tests/         # Unit/integration tests

  research_data/ # Dataset thử nghiệm, lưu an toàn

6.2. Những lệnh khởi tạo tối thiểu trên PowerShell

Backend (cài Python 3.11 trước):

py -3.11 -m venv .venv

.\.venv\Scripts\Activate.ps1

python -m pip install fastapi uvicorn sqlalchemy python-multipart pymupdf python-docx pydantic

uvicorn app.main:app --reload

Frontend (cài Node.js LTS trước):

npm create vite@latest frontend -- --template react

cd frontend

npm install

npm run dev

Đến giai đoạn OCR mới cài Tesseract executable (bao gồm vie.traineddata) và pip install pytesseract pillow. Giai đoạn đầu dùng FastAPI /docs để kiểm tra API; chưa cần Docker hay WSL.

7. Phân công nhóm và Sprint 1

7.1. Nhóm vai trò tham khảo (4–5 người)

VAI TRÒ

PHẠM VI

Frontend

Màn hình CRUD, upload, preview, dashboard/report.

Backend / DB

Cơ sở dữ liệu, API, upload, job orchestration, bảo vệ dữ liệu.

Document AI

Parser, OCR, prompt/schema trích xuất, kết nối LLM.

Validation

Chuẩn hóa, đối chiếu liên văn bản, triển khai rule.

Research / QA

Xây dataset và nhãn chuẩn, quy trình đánh giá, kiểm thử, báo cáo NCKH.

7.2. Sprint 1 – việc cần giao ngay

XONG

CÔNG VIỆC

TIÊU CHÍ NGHIỆM THU

☐

CRUD văn bản quy định

Có danh sách/tạo/sửa/xóa mềm; DB bền vững.

☐

Quản lý bộ hồ sơ

Một dossier có nhiều document; CRUD ổn định.

☐

Upload PDF/DOCX/ảnh

Giữ file gốc, lưu loại/đường dẫn/metadata.

☐

Document Parser

PDF có text và DOCX trả nội dung theo trang.

☐

Document Preview

Xem file gốc + text trích xuất trong web.

☐

Bộ hồ sơ demo

Ít nhất 1 bộ có 3–4 loại tài liệu phục vụ thử nghiệm.

QUY TẮC NGHIỆM THU SPRINT 1

Nhóm chỉ chuyển sang tích hợp OCR/LLM khi có thể tạo dossier trên web → upload tài liệu → đọc text PDF/DOCX → lưu kết quả → mở lại và xem. Tránh tạo giao diện giả lập không có backend/database thật.

8. Đánh giá khoa học và kiểm soát rủi ro

8.1. Thiết kế thực nghiệm song song với sản phẩm

PHƯƠNG ÁN

PIPELINE

Baseline A — truyền thống

OCR → Regex/NER → Rule Engine

Baseline B — LLM thuần

OCR → LLM Extraction → LLM Validation

Đề xuất — hybrid

OCR/Parser → Structured Extraction → Normalization → Cross-document Matching → Deterministic Rules → Evidence Report

Dữ liệu gán nhãn theo các mức: loại tài liệu, giá trị trường, trang/đoạn chứng cứ, quan hệ liên văn bản và nhãn rule PASS/FAIL/REVIEW. Phải chia train/validation/test theo bộ hồ sơ để tránh rò rỉ dữ liệu giữa các trang của cùng một hồ sơ.

8.2. Metrics nên theo dõi

MÔ-ĐUN

THƯỚC ĐO

OCR

Character Error Rate (CER), Word Error Rate (WER).

Extraction

Exact Match, Precision, Recall, F1 theo từng trường.

Matching

Precision/Recall/F1 phát hiện mâu thuẫn liên văn bản.

Rule/End-to-end

Rule-level accuracy/F1; dossier-level accuracy/F1; False PASS, False FAIL/False Rejection.

Vận hành

Thời gian xử lý / hồ sơ, tỷ lệ NEED REVIEW, lỗi kỹ thuật.

8.3. Rủi ro cần tránh

Pháp lý: không coi rule ví dụ là yêu cầu luật thực tế nếu chưa xác minh điều khoản, phiên bản và thời điểm hiệu lực.

Dữ liệu: chỉ sử dụng hồ sơ có quyền xử lý; ẩn danh dữ liệu cá nhân, không đẩy hồ sơ nhạy cảm lên API ngoài khi chưa được phép.

OCR: PDF scan mờ làm sai text, kéo theo LLM sai; luôn giữ bản gốc và đường dẫn tới trang chứng cứ.

LLM: cần kiểm tra schema, chống suy đoán giá trị không có trong nguồn; thiếu dữ liệu thì NEED REVIEW.

Hệ thống: giới hạn MIME/kích thước file, kiểm tra upload, không tin tên file đầu vào; giữ cấu hình và khóa API trong .env (không commit Git).

Phạm vi: ký tên/con dấu chỉ là module mở rộng; chưa nghiên cứu xác thực chữ ký, chống giả mạo hay tự sinh quy định tự động.

9. Sản phẩm bàn giao và điều kiện hoàn thành MVP

HẠNG MỤC

CẦN CÓ KHI DEMO

Mã nguồn

Repository chứa FE, BE, services, README và cách chạy trên Windows.

Cơ sở dữ liệu

Bộ hồ sơ/tài liệu/quy định; extraction và validation có lịch sử.

Luồng thao tác

Tạo hồ sơ → upload → đọc text/OCR → LLM → đối chiếu → báo cáo.

Bằng chứng

Mỗi lỗi chỉ ra giá trị, tài liệu, trang, câu trích và rule/căn cứ tương ứng.

Nghiên cứu

Dataset gán nhãn + baseline + bảng chỉ số, phân tích các trường hợp lỗi.

MỐC TIẾP THEO SAU CRUD

Công việc tiếp theo nên giao ngay là File Upload + Document Parser + Preview. Sau khi hoàn thành bước này, đội AI mới nối OCR và LLM vào cùng một luồng web. Ưu tiên chứng minh một hồ sơ có thể đi hết pipeline trước khi mở rộng số tài liệu, trường dữ liệu hoặc rule.

Tài liệu được biên soạn từ Research Problem do nhóm cung cấp và lộ trình triển khai đã trao đổi; các quy tắc pháp lý nêu làm ví dụ chỉ dùng để định hướng kỹ thuật, cần xác minh trước khi áp dụng.