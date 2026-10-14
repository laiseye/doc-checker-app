"""
Bộ kiểm thử tự động Giai đoạn 2: Upload tài liệu & Document Parser
------------------------------------------------------------------
Kiểm tra toàn diện:
1. Upload PDF hợp lệ nhiều trang (status='done', bóc tách text theo trang, sha256, file_size).
2. Upload PDF có trang dưới ngưỡng tối thiểu (status='needs_ocr').
3. Upload PDF có mật khẩu (status='failed', thông báo đúng).
4. Upload PDF 0 trang (status='failed', thông báo đúng).
5. Upload DOCX hợp lệ chứa cả đoạn văn và bảng biểu (status='done', page_count=1).
6. Upload DOCX rỗng không có chữ (status='failed', thông báo đúng).
7. Upload hình ảnh JPG/PNG (status='needs_ocr', không bóc tách text ở GĐ2).
8. Từ chối file Word định dạng cũ .doc (HTTP 415).
9. Từ chối file giả mạo định dạng không khớp Magic Bytes (HTTP 415).
10. Từ chối file vượt quá dung lượng tối đa MAX_UPLOAD_MB=1 (HTTP 413).
11. Kiểm tra ràng buộc dossier cha (404 nếu không tồn tại, 400 nếu bị xóa mềm).
12. Reparse tài liệu và bảo lưu edited_text của các trang cũ cùng số trang.
13. Reparse tài liệu không có file vật lý trả về HTTP 400.
14. Xóa mềm tài liệu không xóa file vật lý trên đĩa; khôi phục thì xem lại được file.
"""

import io
import os
from pathlib import Path
import pytest
import pymupdf
import docx
from sqlalchemy import select

from app.models import Dossier, Document, DocumentPage, DocumentType


# ==============================================================================
# FIXTURES & HELPERS
# ==============================================================================
@pytest.fixture(autouse=True)
def setup_test_storage(tmp_path, monkeypatch):
    """Ghi đè thư mục lưu trữ file sang thư mục tạm thời của pytest"""
    test_storage = tmp_path / "test_storage"
    test_storage.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("STORAGE_DIR", str(test_storage))
    monkeypatch.setenv("MAX_UPLOAD_MB", "20")
    monkeypatch.setenv("PARSER_MIN_CHARS_PER_PAGE", "20")
    yield test_storage


@pytest.fixture
def create_test_dossier(client):
    """Fixture tạo nhanh một bộ hồ sơ để kiểm thử"""
    res = client.post(
        "/api/v1/dossiers",
        json={
            "name": "Hồ sơ Thử nghiệm GĐ2",
            "status": "DRAFT",
            "description": "Hồ sơ kiểm thử Upload & Parse",
        },
    )
    assert res.status_code == 201
    return res.json()["id"]


def make_pdf_bytes(pages_text: list[str], password: str = None) -> bytes:
    """Tạo file PDF trong bộ nhớ với danh sách nội dung từng trang"""
    doc = pymupdf.open()
    for text in pages_text:
        page = doc.new_page()
        page.insert_text((50, 72), text)
    if password:
        pdf_bytes = doc.tobytes(
            encryption=pymupdf.PDF_ENCRYPT_AES_256,
            user_pw=password,
            owner_pw=password,
        )
    else:
        pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def make_zero_page_pdf_bytes() -> bytes:
    """Tạo byte stream PDF hợp lệ chuẩn 1.4 nhưng có 0 trang (Count 0, Kids [])"""
    pdf_0 = (
        b"%PDF-1.4\n"
        b"1 0 obj\n"
        b"<< /Type /Catalog /Pages 2 0 R >>\n"
        b"endobj\n"
        b"2 0 obj\n"
        b"<< /Type /Pages /Kids [] /Count 0 >>\n"
        b"endobj\n"
        b"xref\n"
        b"0 3\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"trailer\n"
        b"<< /Size 3 /Root 1 0 R >>\n"
        b"startxref\n"
        b"115\n"
        b"%%EOF\n"
    )
    return pdf_0


def make_docx_bytes(paragraphs: list[str], table_rows: list[list[str]] = None) -> bytes:
    """Tạo file DOCX trong bộ nhớ với các đoạn văn và bảng biểu"""
    doc = docx.Document()
    for p in paragraphs:
        doc.add_paragraph(p)
    if table_rows:
        table = doc.add_table(rows=len(table_rows), cols=len(table_rows[0]))
        for r_idx, row in enumerate(table_rows):
            for c_idx, cell_value in enumerate(row):
                table.cell(r_idx, c_idx).text = cell_value
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()


# 1x1 pixel PNG image bytes
MINIMAL_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00"
    b"\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


# ==============================================================================
# CÁC TEST CASES
# ==============================================================================

def test_upload_valid_pdf(client, create_test_dossier):
    """1. Upload file PDF hợp lệ có text nhiều trang"""
    dossier_id = create_test_dossier
    page1 = "Cong hoa Xa hoi Chu nghia Viet Nam. Doc lap - Tu do - Hanh phuc. Ban thuyet minh de tai NCKH."
    page2 = "Noi dung nghien cuu chi tiet giai doan 2: Thiet ke he thong boc tach van ban ho so dien tu."
    pdf_bytes = make_pdf_bytes([page1, page2])

    res = client.post(
        f"/api/v1/dossiers/{dossier_id}/documents",
        files={"file": ("thuyet_minh.pdf", pdf_bytes, "application/pdf")},
        data={"document_type": DocumentType.CONTRACT.value},
    )
    assert res.status_code == 201
    doc_data = res.json()
    doc_id = doc_data["id"]

    assert doc_data["original_name"] == "thuyet_minh.pdf"
    assert doc_data["document_type"] == DocumentType.CONTRACT.value
    assert doc_data["parse_status"] == "done"
    assert doc_data["parse_error"] is None
    assert doc_data["file_size"] == len(pdf_bytes)
    assert len(doc_data["sha256"]) == 64
    assert doc_data["page_count"] == 2

    # Kiểm tra endpoint GET /documents/{id}/pages
    pages_res = client.get(f"/api/v1/documents/{doc_id}/pages")
    assert pages_res.status_code == 200
    pages = pages_res.json()
    assert len(pages) == 2
    assert pages[0]["page_number"] == 1
    assert "Cong hoa Xa hoi" in pages[0]["raw_text"]
    assert pages[0]["parser_type"] == "pymupdf"
    assert pages[1]["page_number"] == 2
    assert "Noi dung nghien cuu chi tiet" in pages[1]["raw_text"]

    # Kiểm tra endpoint GET /documents/{id}/file
    file_res = client.get(f"/api/v1/documents/{doc_id}/file")
    assert file_res.status_code == 200
    assert file_res.headers["content-type"] == "application/pdf"
    assert "inline;" in file_res.headers["content-disposition"]
    assert "nosniff" in file_res.headers.get("x-content-type-options", "")
    assert file_res.content == pdf_bytes


def test_upload_pdf_short_or_scanned_marks_needs_ocr(client, create_test_dossier):
    """2. PDF có trang dưới ngưỡng ký tự tối thiểu (<20 chars) -> đánh dấu needs_ocr"""
    dossier_id = create_test_dossier
    page1 = "Trang 1 có đầy đủ nội dung văn bản dài hơn 20 ký tự để kiểm tra."
    page2 = "Ngắn"  # Chỉ có 4 ký tự -> dưới ngưỡng 20
    pdf_bytes = make_pdf_bytes([page1, page2])

    res = client.post(
        f"/api/v1/dossiers/{dossier_id}/documents",
        files={"file": ("scanned_page.pdf", pdf_bytes, "application/pdf")},
    )
    assert res.status_code == 201
    doc_data = res.json()
    assert doc_data["parse_status"] == "needs_ocr"
    assert "OCR" in doc_data["parse_error"]
    assert doc_data["page_count"] == 2

    # Các trang vẫn được lưu vào document_pages để xem trước
    pages_res = client.get(f"/api/v1/documents/{doc_data['id']}/pages")
    assert pages_res.status_code == 200
    assert len(pages_res.json()) == 2


def test_upload_pdf_password_protected(client, create_test_dossier):
    """3. PDF có mật khẩu bảo vệ -> parse_status='failed', parse_error rõ ràng"""
    dossier_id = create_test_dossier
    pdf_bytes = make_pdf_bytes(
        ["Nội dung tuyệt mật không được đọc nếu không có mật khẩu."],
        password="MySecretPassword123",
    )

    res = client.post(
        f"/api/v1/dossiers/{dossier_id}/documents",
        files={"file": ("protected.pdf", pdf_bytes, "application/pdf")},
    )
    assert res.status_code == 201
    doc_data = res.json()
    assert doc_data["parse_status"] == "failed"
    assert "PDF được bảo vệ bằng mật khẩu" in doc_data["parse_error"]
    assert doc_data["page_count"] == 0

    pages_res = client.get(f"/api/v1/documents/{doc_data['id']}/pages")
    assert pages_res.status_code == 200
    assert len(pages_res.json()) == 0


def test_upload_pdf_zero_pages(client, create_test_dossier):
    """4. PDF 0 trang -> parse_status='failed', không bao giờ trả 'done'"""
    dossier_id = create_test_dossier
    pdf_bytes = make_zero_page_pdf_bytes()

    res = client.post(
        f"/api/v1/dossiers/{dossier_id}/documents",
        files={"file": ("empty.pdf", pdf_bytes, "application/pdf")},
    )
    assert res.status_code == 201
    doc_data = res.json()
    assert doc_data["parse_status"] == "failed"
    assert "PDF không có trang nào hoặc bị hỏng" in doc_data["parse_error"]
    assert doc_data["page_count"] == 0


def test_upload_valid_docx(client, create_test_dossier):
    """5. Upload file DOCX hợp lệ chứa văn bản và bảng biểu theo thứ tự"""
    dossier_id = create_test_dossier
    paragraphs = [
        "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
        "Đề tài: Ứng dụng AI trong thẩm định hồ sơ",
    ]
    table_data = [
        ["STT", "Họ và tên", "Vai trò"],
        ["1", "Nguyễn Văn A", "Chủ nhiệm đề tài"],
        ["2", "Trần Thị B", "Thư ký khoa học"],
    ]
    docx_bytes = make_docx_bytes(paragraphs, table_data)

    res = client.post(
        f"/api/v1/dossiers/{dossier_id}/documents",
        files={"file": ("bao_cao.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert res.status_code == 201
    doc_data = res.json()
    doc_id = doc_data["id"]

    assert doc_data["parse_status"] == "done"
    assert doc_data["page_count"] == 1
    assert doc_data["parse_error"] is None

    pages_res = client.get(f"/api/v1/documents/{doc_id}/pages")
    assert pages_res.status_code == 200
    pages = pages_res.json()
    assert len(pages) == 1
    text = pages[0]["raw_text"]
    assert "CỘNG HÒA XÃ HỘI" in text
    assert "Chủ nhiệm đề tài" in text
    assert pages[0]["parser_type"] == "python-docx"


def test_upload_empty_docx_fails(client, create_test_dossier):
    """6. DOCX rỗng không có chữ -> parse_status='failed', không dùng 'needs_ocr'"""
    dossier_id = create_test_dossier
    docx_bytes = make_docx_bytes([])  # Tài liệu trắng hoàn toàn

    res = client.post(
        f"/api/v1/dossiers/{dossier_id}/documents",
        files={"file": ("blank.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert res.status_code == 201
    doc_data = res.json()
    assert doc_data["parse_status"] == "failed"
    assert "DOCX không có nội dung văn bản" in doc_data["parse_error"]
    assert doc_data["page_count"] == 0


def test_upload_image_marks_needs_ocr(client, create_test_dossier):
    """7. Upload ảnh PNG/JPG -> parse_status='needs_ocr', chưa bóc tách text"""
    dossier_id = create_test_dossier

    res = client.post(
        f"/api/v1/dossiers/{dossier_id}/documents",
        files={"file": ("scan_cccd.png", MINIMAL_PNG, "image/png")},
    )
    assert res.status_code == 201
    doc_data = res.json()
    assert doc_data["parse_status"] == "needs_ocr"
    assert doc_data["page_count"] == 0
    assert "OCR" in doc_data["parse_error"]


def test_upload_legacy_doc_rejected_415(client, create_test_dossier):
    """8. File Word cổ .doc (OLE header) bị từ chối với HTTP 415"""
    dossier_id = create_test_dossier
    ole_header = b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1" + b"\x00" * 100

    res = client.post(
        f"/api/v1/dossiers/{dossier_id}/documents",
        files={"file": ("old_word.doc", ole_header, "application/msword")},
    )
    assert res.status_code == 415
    assert ".docx" in res.json()["detail"]


def test_upload_fake_pdf_magic_bytes_rejected_415(client, create_test_dossier):
    """9. File text nhưng đổi đuôi thành .pdf bị từ chối do không đúng magic bytes (HTTP 415)"""
    dossier_id = create_test_dossier
    fake_content = b"This is plain text pretending to be a PDF file."

    res = client.post(
        f"/api/v1/dossiers/{dossier_id}/documents",
        files={"file": ("fake.pdf", fake_content, "application/pdf")},
    )
    assert res.status_code == 415
    assert "không được hỗ trợ" in res.json()["detail"]


def test_upload_file_size_exceeded_413(client, create_test_dossier, monkeypatch):
    """10. Upload file vượt quá MAX_UPLOAD_MB bị từ chối ngay với HTTP 413"""
    dossier_id = create_test_dossier
    monkeypatch.setenv("MAX_UPLOAD_MB", "1")  # Đặt ngưỡng 1MB để test nhanh

    # Tạo dữ liệu 1.2 MB với header PDF hợp lệ để kiểm tra stream limit
    large_pdf = b"%PDF-1.4\n" + (b"A" * (1200 * 1024))

    res = client.post(
        f"/api/v1/dossiers/{dossier_id}/documents",
        files={"file": ("large.pdf", large_pdf, "application/pdf")},
    )
    assert res.status_code == 413
    assert "vượt quá giới hạn tối đa cho phép" in res.json()["detail"]


def test_upload_to_nonexistent_or_deleted_dossier(client, create_test_dossier):
    """11. Upload vào hồ sơ không tồn tại (404) hoặc hồ sơ đã xóa mềm (400)"""
    pdf_bytes = make_pdf_bytes(["Test validation"])

    # 1. Dossier không tồn tại
    res404 = client.post(
        "/api/v1/dossiers/99999/documents",
        files={"file": ("test.pdf", pdf_bytes, "application/pdf")},
    )
    assert res404.status_code == 404

    # 2. Dossier bị xóa mềm
    dossier_id = create_test_dossier
    client.delete(f"/api/v1/dossiers/{dossier_id}")

    res400 = client.post(
        f"/api/v1/dossiers/{dossier_id}/documents",
        files={"file": ("test.pdf", pdf_bytes, "application/pdf")},
    )
    assert res400.status_code == 400
    assert "xóa mềm" in res400.json()["detail"]


def test_reparse_preserves_edited_text(client, db_session, create_test_dossier):
    """12. POST /documents/{id}/parse thay trang cũ bằng trang mới nhưng BẢO LƯU edited_text"""
    dossier_id = create_test_dossier
    pdf_bytes = make_pdf_bytes([
        "Noi dung goc trang 1 dai hon 20 ky tu de kiem tra reparse.",
        "Noi dung goc trang 2 dai hon 20 ky tu de kiem tra reparse.",
    ])

    res = client.post(
        f"/api/v1/dossiers/{dossier_id}/documents",
        files={"file": ("reparse_test.pdf", pdf_bytes, "application/pdf")},
    )
    assert res.status_code == 201
    doc_id = res.json()["id"]

    # Giả lập người dùng đã sửa tay trang 1 bằng cách update trực tiếp vào DB
    page1 = db_session.scalar(
        select(DocumentPage).where(
            DocumentPage.document_id == doc_id,
            DocumentPage.page_number == 1,
        )
    )
    assert page1 is not None
    edited_content = "ĐÂY LÀ VĂN BẢN NGƯỜI DÙNG ĐÃ CHỈNH SỬA TAY VÀ CẦN ĐƯỢC BẢO LƯU."
    page1.edited_text = edited_content
    db_session.commit()

    # Thực hiện gọi API reparse
    reparse_res = client.post(f"/api/v1/documents/{doc_id}/parse")
    assert reparse_res.status_code == 200
    reparsed_doc = reparse_res.json()
    assert reparsed_doc["parse_status"] == "done"

    # Kiểm tra danh sách trang sau khi reparse
    pages_res = client.get(f"/api/v1/documents/{doc_id}/pages")
    assert pages_res.status_code == 200
    new_pages = pages_res.json()
    assert len(new_pages) == 2

    # Trang 1: edited_text phải được bảo lưu chính xác
    assert new_pages[0]["page_number"] == 1
    assert new_pages[0]["edited_text"] == edited_content
    assert "Noi dung goc trang 1" in new_pages[0]["raw_text"]

    # Trang 2: edited_text là None
    assert new_pages[1]["page_number"] == 2
    assert new_pages[1]["edited_text"] is None


def test_reparse_document_without_file_returns_400(client, create_test_dossier):
    """13. Reparse tài liệu chưa có file vật lý trả về HTTP 400"""
    dossier_id = create_test_dossier
    # Tạo tài liệu qua API Giai đoạn 1 (chưa có file)
    create_res = client.post(
        "/api/v1/documents",
        json={"dossier_id": dossier_id, "original_name": "metadata_only.pdf"},
    )
    assert create_res.status_code == 201
    doc_id = create_res.json()["id"]

    reparse_res = client.post(f"/api/v1/documents/{doc_id}/parse")
    assert reparse_res.status_code == 400
    assert "chưa có tệp tin vật lý" in reparse_res.json()["detail"]


def test_soft_delete_retains_physical_file(client, create_test_dossier, setup_test_storage):
    """14. Xóa mềm tài liệu KHÔNG xóa file trên đĩa; khôi phục thì truy cập lại được"""
    dossier_id = create_test_dossier
    pdf_bytes = make_pdf_bytes(["Nội dung tài liệu kiểm tra tính toàn vẹn file vật lý."])

    res = client.post(
        f"/api/v1/dossiers/{dossier_id}/documents",
        files={"file": ("keep_file.pdf", pdf_bytes, "application/pdf")},
    )
    assert res.status_code == 201
    doc_data = res.json()
    doc_id = doc_data["id"]
    storage_path = doc_data["storage_path"]

    # Kiểm tra file vật lý tồn tại trên đĩa
    physical_file = setup_test_storage / storage_path
    assert physical_file.exists()
    assert physical_file.is_file()

    # Xóa mềm tài liệu
    del_res = client.delete(f"/api/v1/documents/{doc_id}")
    assert del_res.status_code == 200

    # File vật lý VẪN PHẢI TỒN TẠI trên đĩa
    assert physical_file.exists()

    # Thử tải file khi đã xóa mềm -> 404
    assert client.get(f"/api/v1/documents/{doc_id}/file").status_code == 404

    # Khôi phục tài liệu -> xem lại được file bình thường
    restore_res = client.post(f"/api/v1/documents/{doc_id}/restore")
    assert restore_res.status_code == 200
    file_res = client.get(f"/api/v1/documents/{doc_id}/file")
    assert file_res.status_code == 200
    assert file_res.content == pdf_bytes
