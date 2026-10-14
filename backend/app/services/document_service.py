"""
Service xử lý nghiệp vụ cho Tài liệu trong hồ sơ (Documents Service)
-------------------------------------------------------------------
Chịu trách nhiệm:
1. Upload tệp tin vật lý (PDF, DOCX, JPG, PNG) vào bộ hồ sơ với giới hạn dung lượng stream.
2. Kiểm tra chữ ký file (Magic bytes) chống giả mạo đuôi file.
3. Lưu trữ an toàn trong thư mục storage/ với tên UUID hex, tính SHA256 và kích thước file.
4. Gọi Document Parser đồng bộ để trích xuất text từng trang và lưu vào document_pages.
5. Cung cấp file nhị phân (phục vụ preview / download) qua RFC 5987 và nosniff.
6. Lấy danh sách trang (GET /pages) và parse lại (POST /parse) bảo lưu edited_text.
7. Đảm bảo tính toán page_count mà TUYỆT ĐỐI không nạp raw_text vào response danh sách.
"""

import os
import uuid
import hashlib
import shutil
from pathlib import Path
from typing import Optional, Tuple, List, Dict
from fastapi import HTTPException, status, UploadFile
from sqlalchemy import select, func, or_, delete
from sqlalchemy.orm import Session

from app.database import ROOT_DIR, get_utc_now
from app.models import Document, Dossier, DocumentPage, DocumentType
from app.schemas import DocumentCreate, DocumentUpdate
from app.services.document_parser import detect_file_type, parse_document, ParseResult


# ==============================================================================
# 1. HÀM TIỆN ÍCH ĐƯỜNG DẪN LƯU TRỮ VÀ DUNG LƯỢNG
# ==============================================================================
def get_storage_dir() -> Path:
    """Trả về đường dẫn tuyệt đối đến thư mục lưu trữ tệp tin trên máy chủ"""
    storage_dirname = os.getenv("STORAGE_DIR", "storage")
    path = (ROOT_DIR / storage_dirname).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_max_upload_bytes() -> int:
    """Trả về giới hạn dung lượng tải lên tối đa theo byte (mặc định 20MB)"""
    max_mb = int(os.getenv("MAX_UPLOAD_MB", "20"))
    return max_mb * 1024 * 1024


# ==============================================================================
# 2. TRUY VẤN VÀ ĐẾM SỐ TRANG (KHÔNG NẠP RAW_TEXT)
# ==============================================================================
def attach_page_counts(db: Session, documents: List[Document]) -> None:
    """
    Tính toán và gắn page_count cho danh sách Document bằng truy vấn COUNT riêng biệt.
    Tuyệt đối không truy cập vào relationship .pages để tránh nạp trường raw_text vào RAM.
    """
    if not documents:
        return
    doc_ids = [d.id for d in documents]
    count_stmt = (
        select(DocumentPage.document_id, func.count(DocumentPage.id))
        .where(DocumentPage.document_id.in_(doc_ids))
        .group_by(DocumentPage.document_id)
    )
    counts_map = dict(db.execute(count_stmt).all())
    for d in documents:
        d.page_count = counts_map.get(d.id, 0)


def get_documents(
    db: Session,
    dossier_id: Optional[int] = None,
    document_type: Optional[DocumentType] = None,
    q: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
    include_deleted: bool = False,
) -> Tuple[List[Document], int]:
    """Lấy danh sách tài liệu có phân trang, lọc theo hồ sơ, loại tài liệu và tìm kiếm"""
    query = select(Document)

    # Lọc theo cờ xóa mềm
    if not include_deleted:
        query = query.where(Document.is_deleted == False)

    # Lọc theo hồ sơ
    if dossier_id is not None:
        query = query.where(Document.dossier_id == dossier_id)

    # Lọc theo loại tài liệu
    if document_type is not None:
        val = document_type.value if hasattr(document_type, "value") else str(document_type)
        query = query.where(Document.document_type == val)

    # Tìm kiếm theo tên file gốc
    if q and q.strip():
        search_term = f"%{q.strip()}%"
        query = query.where(Document.original_name.ilike(search_term))

    # Đếm tổng
    count_stmt = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_stmt) or 0

    # Phân trang
    offset = (page - 1) * page_size
    items_stmt = query.order_by(Document.id.desc()).offset(offset).limit(page_size)
    items = list(db.scalars(items_stmt).all())

    # Gán số lượng trang cho từng document mà không nạp raw_text
    attach_page_counts(db, items)

    return items, total


def get_document_by_id(
    db: Session, document_id: int, include_deleted: bool = False
) -> Document:
    """Lấy chi tiết một tài liệu theo ID và đếm số trang"""
    stmt = select(Document).where(Document.id == document_id)
    if not include_deleted:
        stmt = stmt.where(Document.is_deleted == False)

    document = db.scalar(stmt)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy tài liệu với ID {document_id}",
        )

    # Đếm số trang mà không nạp danh sách raw_text
    page_count = db.scalar(
        select(func.count(DocumentPage.id)).where(DocumentPage.document_id == document.id)
    ) or 0
    document.page_count = page_count

    return document


# ==============================================================================
# 3. UPLOAD TÀI LIỆU VẬT LÝ VÀ PHÂN TÍCH VĂN BẢN
# ==============================================================================
def upload_document_to_dossier(
    db: Session,
    dossier_id: int,
    file: UploadFile,
    document_type: DocumentType = DocumentType.OTHER,
) -> Document:
    """
    Xử lý tải lên file thực tế cho một bộ hồ sơ:
    - Kiểm tra dossier tồn tại và không bị xóa mềm.
    - Đọc stream theo khối, chặn ngay nếu vượt quá MAX_UPLOAD_MB (HTTP 413).
    - Kiểm tra chữ ký magic bytes nhị phân, từ chối file giả mạo hoặc sai định dạng (HTTP 415).
    - Lưu file vào storage/ bằng tên UUID hex, tính SHA-256.
    - Lưu Document vào DB, nếu lỗi thì xóa file vật lý (rollback an toàn).
    - Phân tích văn bản (PDF, DOCX) và lưu document_pages. Nếu parse lỗi, vẫn giữ file gốc.
    """
    # 1. Kiểm tra bộ hồ sơ cha
    dossier_stmt = select(Dossier).where(Dossier.id == dossier_id)
    dossier = db.scalar(dossier_stmt)
    if not dossier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy bộ hồ sơ với ID {dossier_id}",
        )
    if dossier.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể tải tài liệu lên bộ hồ sơ đang bị xóa mềm.",
        )

    # 2. Kiểm tra tên file đầu vào
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Tệp tin tải lên không hợp lệ hoặc thiếu tên tệp.",
        )

    storage_dir = get_storage_dir()
    max_bytes = get_max_upload_bytes()
    max_mb = max_bytes // (1024 * 1024)

    # Tạo tệp tạm thời trên đĩa để nhận luồng stream
    temp_filename = f"upload_tmp_{uuid.uuid4().hex}.bin"
    temp_path = storage_dir / temp_filename

    sha256_hasher = hashlib.sha256()
    total_bytes = 0

    try:
        with open(temp_path, "wb") as out_f:
            while True:
                chunk = file.file.read(64 * 1024)  # Đọc từng khối 64KB
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        detail=f"Dung lượng tệp tin ({total_bytes / (1024*1024):.1f}MB) vượt quá giới hạn tối đa cho phép ({max_mb}MB).",
                    )
                sha256_hasher.update(chunk)
                out_f.write(chunk)

        if total_bytes == 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Tệp tin tải lên có dung lượng rỗng (0 bytes).",
            )

        # 3. Kiểm tra chữ ký nhị phân (Magic Bytes)
        try:
            file_category, detected_mime, detected_ext = detect_file_type(temp_path)
        except ValueError as val_err:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=str(val_err),
            )

        # 4. Đổi tên tệp tạm thành tên chính thức UUID
        final_filename = f"{uuid.uuid4().hex}{detected_ext}"
        final_path = storage_dir / final_filename
        shutil.move(temp_path, final_path)

    except Exception:
        # Dọn dẹp tệp tạm nếu có lỗi trong quá trình đọc hoặc xác thực
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass
        raise
    finally:
        file.file.close()

    # 5. Làm sạch tên file gốc của người dùng
    original_clean_name = Path(file.filename).name[:255]
    sha256_hex = sha256_hasher.hexdigest()
    doc_type_val = document_type.value if hasattr(document_type, "value") else str(document_type)

    # 6. Tạo bản ghi Document trong CSDL
    new_doc = Document(
        dossier_id=dossier_id,
        document_type=doc_type_val,
        original_name=original_clean_name,
        storage_path=final_filename,  # Lưu đường dẫn tương đối so với thư mục storage
        mime_type=detected_mime,
        uploaded_at=get_utc_now(),
        parse_status="processing",
        parse_error=None,
        file_size=total_bytes,
        sha256=sha256_hex,
        is_deleted=False,
        deleted_at=None,
    )
    db.add(new_doc)
    try:
        db.commit()
        db.refresh(new_doc)
    except Exception as db_err:
        db.rollback()
        # Rollback: Xóa file vật lý đã lưu trên đĩa nếu ghi CSDL thất bại
        if final_path.exists():
            try:
                final_path.unlink()
            except Exception:
                pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi lưu thông tin tài liệu vào CSDL: {str(db_err)}",
        )

    # 7. Chạy phân tích văn bản (Document Parser) đồng bộ
    try:
        parse_result: ParseResult = parse_document(final_path, detected_mime)
        new_doc.parse_status = parse_result.status
        new_doc.parse_error = parse_result.error_message

        # Lưu các trang đã trích xuất vào bảng document_pages
        for p in parse_result.pages:
            db_page = DocumentPage(
                document_id=new_doc.id,
                page_number=p.page_number,
                raw_text=p.raw_text,
                edited_text=None,
                parser_type=p.parser_type,
                engine_version=p.engine_version,
                created_at=get_utc_now(),
            )
            db.add(db_page)

        db.commit()
        db.refresh(new_doc)
        new_doc.page_count = len(parse_result.pages)

    except Exception as parse_exc:
        # Nếu parser gặp lỗi không mong muốn, BẢO TOÀN FILE GỐC và ghi nhận failed
        db.rollback()
        new_doc.parse_status = "failed"
        new_doc.parse_error = f"Lỗi không xác định khi đọc tài liệu: {str(parse_exc)}"
        db.commit()
        db.refresh(new_doc)
        new_doc.page_count = 0

    return new_doc


# ==============================================================================
# 4. LẤY FILE GỐC VÀ DANH SÁCH TRANG
# ==============================================================================
def get_document_file_path(
    db: Session, document_id: int, include_deleted: bool = False
) -> Tuple[Document, Path]:
    """
    Lấy thông tin tài liệu và đường dẫn file vật lý trên đĩa:
    - Trả về 404 nếu tài liệu không tồn tại, chưa có file hoặc file bị mất.
    """
    doc = get_document_by_id(db, document_id, include_deleted=include_deleted)
    if not doc.storage_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tài liệu chưa có tệp tin đính kèm.",
        )

    storage_dir = get_storage_dir()
    file_path = storage_dir / doc.storage_path
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tệp tin gốc không tìm thấy trên hệ thống lưu trữ máy chủ.",
        )

    return doc, file_path


def get_document_pages(
    db: Session, document_id: int, include_deleted: bool = False
) -> List[DocumentPage]:
    """Lấy danh sách các trang văn bản đã trích xuất của một tài liệu, sắp xếp theo page_number"""
    # Đảm bảo document tồn tại
    _ = get_document_by_id(db, document_id, include_deleted=include_deleted)

    stmt = (
        select(DocumentPage)
        .where(DocumentPage.document_id == document_id)
        .order_by(DocumentPage.page_number.asc())
    )
    pages = list(db.scalars(stmt).all())
    return pages


# ==============================================================================
# 5. PHÂN TÍCH LẠI TÀI LIỆU (REPARSE DOCUMENT)
# ==============================================================================
def reparse_document(db: Session, document_id: int) -> Document:
    """
    Thực hiện phân tích lại văn bản từ file gốc:
    - Thay thế toàn bộ trang cũ bằng các trang mới trong cùng 1 transaction.
    - ĐIỀU CHỈNH BẮT BUỘC: Nếu trang cũ có edited_text, bảo lưu edited_text và gán sang trang mới có cùng page_number.
    - Trả về 400 nếu tài liệu chưa có file vật lý.
    """
    doc = get_document_by_id(db, document_id, include_deleted=False)
    if not doc.storage_path or doc.parse_status == "no_file":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tài liệu chưa có tệp tin vật lý để thực hiện phân tích lại.",
        )

    storage_dir = get_storage_dir()
    file_path = storage_dir / doc.storage_path
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tệp tin gốc không tồn tại trên hệ thống lưu trữ.",
        )

    # 1. Thu thập edited_text của các trang cũ để bảo lưu theo page_number
    old_pages_stmt = select(DocumentPage).where(DocumentPage.document_id == doc.id)
    old_pages = list(db.scalars(old_pages_stmt).all())
    edited_text_map: Dict[int, Optional[str]] = {
        p.page_number: p.edited_text for p in old_pages if p.edited_text is not None
    }

    # 2. Xóa các trang cũ của tài liệu
    db.execute(delete(DocumentPage).where(DocumentPage.document_id == doc.id))

    # 3. Chạy phân tích văn bản lại từ file gốc
    mime = doc.mime_type or "application/octet-stream"
    parse_result: ParseResult = parse_document(file_path, mime)

    doc.parse_status = parse_result.status
    doc.parse_error = parse_result.error_message
    doc.updated_at = get_utc_now()

    # 4. Ghi các trang mới, bảo lưu edited_text nếu có cùng page_number
    for p in parse_result.pages:
        preserved_edited = edited_text_map.get(p.page_number)
        new_page = DocumentPage(
            document_id=doc.id,
            page_number=p.page_number,
            raw_text=p.raw_text,
            edited_text=preserved_edited,
            parser_type=p.parser_type,
            engine_version=p.engine_version,
            created_at=get_utc_now(),
        )
        db.add(new_page)

    db.commit()
    db.refresh(doc)
    doc.page_count = len(parse_result.pages)
    return doc


# ==============================================================================
# 6. TƯƠNG THÍCH NGƯỢC CRUD GIAI ĐOẠN 1
# ==============================================================================
def create_document(db: Session, payload: DocumentCreate) -> Document:
    """Tạo mới siêu dữ liệu tài liệu (không có file, phục vụ tương thích ngược test GĐ1)"""
    dossier_stmt = select(Dossier).where(Dossier.id == payload.dossier_id)
    dossier = db.scalar(dossier_stmt)
    if not dossier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy bộ hồ sơ cha với ID {payload.dossier_id}",
        )
    if dossier.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể thêm tài liệu vào bộ hồ sơ đang bị xóa mềm.",
        )

    doc_type_val = payload.document_type.value if hasattr(payload.document_type, "value") else str(payload.document_type)
    new_doc = Document(
        dossier_id=payload.dossier_id,
        document_type=doc_type_val,
        original_name=payload.original_name,
        storage_path=payload.storage_path,
        mime_type=payload.mime_type,
        uploaded_at=get_utc_now(),
        parse_status="no_file",
        parse_error=None,
        file_size=None,
        sha256=None,
        is_deleted=False,
        deleted_at=None,
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)
    new_doc.page_count = 0
    return new_doc


def update_document(
    db: Session, document_id: int, payload: DocumentUpdate
) -> Document:
    """Cập nhật thông tin tài liệu"""
    document = get_document_by_id(db, document_id, include_deleted=False)

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == "document_type" and value is not None:
            value = value.value if hasattr(value, "value") else str(value)
        setattr(document, key, value)

    document.updated_at = get_utc_now()
    db.commit()
    db.refresh(document)
    return document


def soft_delete_document(db: Session, document_id: int) -> None:
    """Xóa mềm tài liệu (KHÔNG xóa file vật lý trên đĩa)"""
    document = get_document_by_id(db, document_id, include_deleted=False)
    now_utc = get_utc_now()
    document.is_deleted = True
    document.deleted_at = now_utc
    document.updated_at = now_utc
    db.commit()


def restore_document(db: Session, document_id: int) -> Document:
    """Khôi phục tài liệu đã xóa mềm"""
    document = get_document_by_id(db, document_id, include_deleted=True)
    if not document.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tài liệu ID {document_id} đang hoạt động, không cần khôi phục.",
        )

    # Kiểm tra dossier cha
    dossier_stmt = select(Dossier).where(Dossier.id == document.dossier_id)
    dossier = db.scalar(dossier_stmt)
    if not dossier or dossier.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể khôi phục tài liệu vì bộ hồ sơ chứa nó đang bị xóa. Hãy khôi phục bộ hồ sơ trước.",
        )

    document.is_deleted = False
    document.deleted_at = None
    document.updated_at = get_utc_now()
    db.commit()
    db.refresh(document)
    return document
