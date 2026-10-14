"""
Module phân tích văn bản từ tài liệu (Document Parser Service)
--------------------------------------------------------------
Chịu trách nhiệm:
1. Nhận diện loại tệp tin theo chữ ký nhị phân (Magic Bytes), chống giả mạo đuôi file.
2. Trích xuất text từ tệp PDF (PyMuPDF):
   - Kiểm tra PDF có mật khẩu (doc.needs_pass) -> failed.
   - Kiểm tra số trang rỗng (doc.page_count == 0) -> failed.
   - Trích xuất từng trang, tạo bản ghi cho từng trang kể cả trang rỗng.
   - Nếu có trang dưới ngưỡng PARSER_MIN_CHARS_PER_PAGE (mặc định 20 ký tự) -> needs_ocr.
3. Trích xuất text từ tệp DOCX (python-docx):
   - Duyệt tuần tự đoạn văn và bảng biểu theo thứ tự xuất hiện.
   - Lưu thành 1 trang duy nhất (page_number=1).
   - Nếu hoàn toàn không có text -> failed với lỗi "DOCX không có nội dung văn bản".
4. Tệp hình ảnh JPG/PNG: Đánh dấu needs_ocr (chờ Giai đoạn 3).
"""

import os
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple
import pymupdf
import docx

def get_min_chars_per_page() -> int:
    """Đọc ngưỡng ký tự tối thiểu của một trang PDF từ biến môi trường (mặc định 20)"""
    try:
        return int(os.getenv("PARSER_MIN_CHARS_PER_PAGE", "20"))
    except ValueError:
        return 20


@dataclass
class ParsedPageData:
    """Dữ liệu một trang văn bản đã trích xuất"""
    page_number: int
    raw_text: str
    parser_type: str
    engine_version: Optional[str] = None


@dataclass
class ParseResult:
    """Kết quả phân tích toàn bộ tài liệu"""
    status: str  # 'done' | 'needs_ocr' | 'failed'
    error_message: Optional[str] = None
    pages: List[ParsedPageData] = field(default_factory=list)


# ==============================================================================
# 1. NHẬN DIỆN VÀ KIỂM TRA CHỮ KÝ FILE (MAGIC BYTES)
# ==============================================================================
def detect_file_type(file_path: Path) -> Tuple[str, str, str]:
    """
    Xác định loại file dựa trên chữ ký nhị phân (Magic Bytes) đầu tệp.
    Trả về Tuple: (file_type, mime_type, extension)
    Ví dụ: ("PDF", "application/pdf", ".pdf")

    Ném ngoại lệ ValueError nếu định dạng không được hỗ trợ hoặc giả mạo đuôi.
    """
    if not file_path.exists() or file_path.stat().st_size == 0:
        raise ValueError("Tệp tin rỗng hoặc không tồn tại trên hệ thống")

    with open(file_path, "rb") as f:
        header = f.read(16)

    # 1. Kiểm tra PDF: bắt đầu bằng %PDF
    if header.startswith(b"%PDF"):
        return "PDF", "application/pdf", ".pdf"

    # 2. Kiểm tra PNG: \x89PNG\r\n\x1a\n
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG", "image/png", ".png"

    # 3. Kiểm tra JPEG: \xFF\xD8\xFF
    if header.startswith(b"\xFF\xD8\xFF"):
        return "JPEG", "image/jpeg", ".jpg"

    # 4. Kiểm tra DOC cũ (Binary OLE: \xD0\xCF\x11\xE0): Từ chối
    if header.startswith(b"\xD0\xCF\x11\xE0"):
        raise ValueError("Định dạng file Word .doc cũ không được hỗ trợ. Vui lòng chuyển đổi sang định dạng .docx hiện đại.")

    # 5. Kiểm tra DOCX: ZIP archive bắt đầu bằng PK\x03\x04 và chứa word/document.xml
    if header.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                names = zf.namelist()
                if "word/document.xml" in names:
                    return (
                        "DOCX",
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        ".docx",
                    )
        except Exception:
            pass
        raise ValueError("Tệp ZIP không phải là định dạng tài liệu Word .docx hợp lệ")

    raise ValueError("Định dạng tệp tin không được hỗ trợ. Hệ thống chỉ chấp nhận PDF, DOCX, JPG/JPEG và PNG.")


# ==============================================================================
# 2. BỘ PHÂN TÍCH TỆP PDF (PyMuPDF)
# ==============================================================================
def parse_pdf(file_path: Path) -> ParseResult:
    """
    Phân tích tệp PDF bằng PyMuPDF (fitz):
    - Kiểm tra bảo vệ mật khẩu (doc.needs_pass).
    - Kiểm tra số lượng trang (doc.page_count == 0).
    - Trích xuất text từng trang và đánh giá độ tin cậy.
    """
    try:
        doc = pymupdf.open(file_path)
    except Exception as e:
        return ParseResult(
            status="failed",
            error_message=f"Không thể mở tệp PDF (file có thể bị hỏng): {str(e)}",
        )

    try:
        # Kiểm tra PDF có mật khẩu
        if doc.needs_pass:
            return ParseResult(
                status="failed",
                error_message="PDF được bảo vệ bằng mật khẩu",
            )

        # Kiểm tra file không có trang nào
        if doc.page_count == 0:
            return ParseResult(
                status="failed",
                error_message="PDF không có trang nào hoặc bị hỏng",
            )

        pages: List[ParsedPageData] = []
        has_low_text_page = False
        engine_ver = f"pymupdf {pymupdf.__version__}"

        min_chars = get_min_chars_per_page()
        for i in range(doc.page_count):
            page_num = i + 1
            try:
                page = doc.load_page(i)
                text = page.get_text("text") or ""
            except Exception as page_err:
                text = ""
                has_low_text_page = True

            # Kiểm tra ngưỡng ký tự (sau khi strip)
            stripped = text.strip()
            if len(stripped) < min_chars:
                has_low_text_page = True

            pages.append(
                ParsedPageData(
                    page_number=page_num,
                    raw_text=text,
                    parser_type="pymupdf",
                    engine_version=engine_ver,
                )
            )

        status_result = "needs_ocr" if has_low_text_page else "done"
        err_msg = (
            f"Có trang chứa ít hơn {min_chars} ký tự hoặc là trang scan hình ảnh, cần xử lý OCR ở Giai đoạn 3"
            if has_low_text_page
            else None
        )
        return ParseResult(status=status_result, error_message=err_msg, pages=pages)

    except Exception as e:
        return ParseResult(
            status="failed",
            error_message=f"Lỗi trong quá trình đọc nội dung PDF: {str(e)}",
        )
    finally:
        doc.close()


# ==============================================================================
# 3. BỘ PHÂN TÍCH TỆP DOCX (python-docx)
# ==============================================================================
def parse_docx(file_path: Path) -> ParseResult:
    """
    Phân tích tệp Word (.docx) bằng python-docx:
    - Đọc tuần tự cả đoạn văn (Paragraphs) và bảng biểu (Tables) theo đúng thứ tự xuất hiện.
    - Lưu toàn bộ văn bản vào 1 trang duy nhất (page_number=1).
    - Ngưỡng PARSER_MIN_CHARS_PER_PAGE không áp dụng cho DOCX.
    - Chỉ báo lỗi 'failed' khi tổng text rỗng hoàn toàn sau khi strip.
    """
    try:
        doc = docx.Document(file_path)
    except Exception as e:
        return ParseResult(
            status="failed",
            error_message=f"Không thể đọc tệp Word DOCX (file có thể bị hỏng): {str(e)}",
        )

    try:
        content_parts: List[str] = []

        # Duyệt tuần tự các phần tử con trực tiếp của thân tài liệu (body)
        for child in doc.element.body:
            # 1. Đoạn văn (Paragraph)
            if child.tag.endswith("p"):
                p = docx.text.paragraph.Paragraph(child, doc)
                p_text = p.text.strip()
                if p_text:
                    content_parts.append(p_text)
            # 2. Bảng biểu (Table)
            elif child.tag.endswith("tbl"):
                table = docx.table.Table(child, doc)
                for row in table.rows:
                    row_texts = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if row_texts:
                        content_parts.append(" | ".join(row_texts))

        full_text = "\n\n".join(content_parts).strip()

        # Nếu hoàn toàn không có nội dung text sau khi strip -> failed
        if not full_text:
            return ParseResult(
                status="failed",
                error_message="DOCX không có nội dung văn bản",
            )

        engine_ver = f"python-docx {docx.__version__}"
        page_data = ParsedPageData(
            page_number=1,
            raw_text=full_text,
            parser_type="python-docx",
            engine_version=engine_ver,
        )

        return ParseResult(status="done", pages=[page_data])

    except Exception as e:
        return ParseResult(
            status="failed",
            error_message=f"Lỗi khi trích xuất nội dung DOCX: {str(e)}",
        )


# ==============================================================================
# 4. HÀM PHÂN TÍCH ĐIỀU PHỐI CHÍNH (PARSE_DOCUMENT)
# ==============================================================================
def parse_document(file_path: Path, mime_type: str) -> ParseResult:
    """
    Hàm điều phối phân tích văn bản dựa trên MIME type:
    - PDF -> Gọi parse_pdf
    - DOCX -> Gọi parse_docx
    - Image (JPEG, PNG) -> Đặt needs_ocr, không tạo page
    """
    if not file_path.exists():
        return ParseResult(status="failed", error_message="Tệp tin không tồn tại trên ổ đĩa")

    # Xử lý PDF
    if mime_type == "application/pdf":
        return parse_pdf(file_path)

    # Xử lý DOCX
    if mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return parse_docx(file_path)

    # Xử lý ảnh JPG/PNG (chờ Giai đoạn 3 OCR)
    if mime_type in ["image/jpeg", "image/png"]:
        return ParseResult(
            status="needs_ocr",
            error_message="Tài liệu hình ảnh cần xử lý nhận dạng chữ OCR ở Giai đoạn 3",
            pages=[],
        )

    return ParseResult(
        status="failed",
        error_message=f"Loại MIME '{mime_type}' chưa được hỗ trợ phân tích",
    )
