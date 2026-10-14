"""
Router quản lý Tài liệu trong hồ sơ (Documents API)
--------------------------------------------------
Đường dẫn cơ sở: /api/v1/documents
Cung cấp đầy đủ các thao tác CRUD và Khôi phục metadata tài liệu:
- GET /api/v1/documents (Phân trang, lọc dossier_id, document_type, q, include_deleted)
- POST /api/v1/documents (Tạo metadata tài liệu, chặn nếu dossier cha đang bị xóa)
- GET /api/v1/documents/{id} (Chi tiết tài liệu)
- PUT / PATCH /api/v1/documents/{id} (Cập nhật thông tin tài liệu)
- DELETE /api/v1/documents/{id} (Xóa mềm tài liệu đơn lẻ)
- POST /api/v1/documents/{id}/restore (Khôi phục, chặn nếu dossier cha đang bị xóa)
"""

from typing import Optional, List
from urllib.parse import quote
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DocumentType
from app.schemas import (
    DocumentCreate,
    DocumentUpdate,
    DocumentOut,
    DocumentPageOut,
    PaginationResponse,
    MessageResponse,
)
from app.services import document_service

router = APIRouter(prefix="/documents", tags=["Tài liệu trong hồ sơ"])


@router.get(
    "",
    response_model=PaginationResponse[DocumentOut],
    summary="Lấy danh sách tài liệu (phân trang & tìm kiếm)",
)
def list_documents(
    dossier_id: Optional[int] = Query(None, description="Lọc theo ID bộ hồ sơ"),
    document_type: Optional[DocumentType] = Query(None, description="Lọc theo loại tài liệu"),
    q: Optional[str] = Query(None, description="Từ khóa tìm kiếm theo tên gốc file"),
    page: int = Query(1, ge=1, description="Số thứ tự trang"),
    page_size: int = Query(10, ge=1, le=100, description="Số lượng mục mỗi trang"),
    include_deleted: bool = Query(False, description="Xem cả tài liệu đã xóa mềm"),
    db: Session = Depends(get_db),
):
    items, total = document_service.get_documents(
        db=db,
        dossier_id=dossier_id,
        document_type=document_type,
        q=q,
        page=page,
        page_size=page_size,
        include_deleted=include_deleted,
    )
    return PaginationResponse(items=items, total=total, page=page, page_size=page_size)


@router.post(
    "",
    response_model=DocumentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Thêm mới siêu dữ liệu tài liệu vào hồ sơ",
)
def create_document(
    payload: DocumentCreate,
    db: Session = Depends(get_db),
):
    """
    Tạo mới metadata tài liệu.
    Ràng buộc: Không cho phép tạo tài liệu vào bộ hồ sơ đang ở trạng thái xóa mềm.
    """
    return document_service.create_document(db=db, payload=payload)


@router.get(
    "/{document_id}",
    response_model=DocumentOut,
    summary="Lấy chi tiết thông tin tài liệu",
)
def get_document(
    document_id: int,
    include_deleted: bool = Query(False, description="Xem tài liệu kể cả khi đã xóa mềm"),
    db: Session = Depends(get_db),
):
    return document_service.get_document_by_id(
        db=db, document_id=document_id, include_deleted=include_deleted
    )


@router.put(
    "/{document_id}",
    response_model=DocumentOut,
    summary="Cập nhật toàn bộ thông tin tài liệu",
)
@router.patch(
    "/{document_id}",
    response_model=DocumentOut,
    summary="Cập nhật một phần thông tin tài liệu",
)
def update_document(
    document_id: int,
    payload: DocumentUpdate,
    db: Session = Depends(get_db),
):
    return document_service.update_document(
        db=db, document_id=document_id, payload=payload
    )


@router.delete(
    "/{document_id}",
    response_model=MessageResponse,
    summary="Xóa mềm tài liệu",
)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
):
    """Xóa mềm tài liệu riêng lẻ. Không xóa vật lý."""
    document_service.soft_delete_document(db=db, document_id=document_id)
    return MessageResponse(
        message=f"Đã xóa mềm tài liệu ID {document_id} thành công."
    )


@router.post(
    "/{document_id}/restore",
    response_model=DocumentOut,
    summary="Khôi phục tài liệu đã xóa mềm",
)
def restore_document(
    document_id: int,
    db: Session = Depends(get_db),
):
    """
    Khôi phục tài liệu riêng lẻ.
    Ràng buộc: Nếu bộ hồ sơ cha đang bị xóa mềm, API sẽ từ chối và yêu cầu khôi phục hồ sơ cha trước.
    """
    return document_service.restore_document(db=db, document_id=document_id)


@router.get(
    "/{document_id}/file",
    summary="Tải về hoặc xem trực tiếp file gốc của tài liệu",
)
def get_document_file(
    document_id: int,
    db: Session = Depends(get_db),
):
    """
    Trả về tệp tin vật lý gốc để xem trước (preview) hoặc tải về.
    Đặt Header Content-Disposition theo chuẩn RFC 5987 để hỗ trợ tên file tiếng Việt UTF-8.
    Header X-Content-Type-Options: nosniff để chống MIME confusion attack.
    Hàm đồng bộ (def) để FastAPI tự xử lý I/O trong threadpool.
    """
    doc, file_path = document_service.get_document_file_path(db=db, document_id=document_id)
    encoded_filename = quote(doc.original_name)
    media_type = doc.mime_type or "application/octet-stream"
    headers = {
        "Content-Disposition": f"inline; filename*=UTF-8''{encoded_filename}",
        "X-Content-Type-Options": "nosniff",
    }
    return FileResponse(path=str(file_path), media_type=media_type, headers=headers)


@router.get(
    "/{document_id}/pages",
    response_model=List[DocumentPageOut],
    summary="Lấy danh sách các trang và nội dung văn bản đã trích xuất",
)
def get_document_pages(
    document_id: int,
    db: Session = Depends(get_db),
):
    """
    Lấy danh sách các trang đã được bóc tách nội dung (raw_text, parser_type, engine_version...).
    Sắp xếp tuần tự theo page_number tăng dần.
    """
    return document_service.get_document_pages(db=db, document_id=document_id)


@router.post(
    "/{document_id}/parse",
    response_model=DocumentOut,
    summary="Phân tích lại (reparse) nội dung từ file vật lý gốc",
)
def reparse_document(
    document_id: int,
    db: Session = Depends(get_db),
):
    """
    Thực hiện phân tích lại văn bản từ file gốc đã lưu trên máy chủ:
    - Xóa các trang cũ và nạp lại các trang mới.
    - Bảo lưu edited_text của các trang cũ nếu trùng page_number.
    - Cập nhật parse_status và trả về thông tin tài liệu mới nhất.
    """
    return document_service.reparse_document(db=db, document_id=document_id)

