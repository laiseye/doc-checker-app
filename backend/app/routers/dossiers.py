"""
Router quản lý Bộ hồ sơ thẩm định (Dossiers API)
-----------------------------------------------
Đường dẫn cơ sở: /api/v1/dossiers
Cung cấp đầy đủ các thao tác CRUD, Khôi phục và Truy vấn tài liệu con:
- GET /api/v1/dossiers (Phân trang, tìm kiếm, lọc status, include_deleted)
- POST /api/v1/dossiers (Tạo mới bộ hồ sơ)
- GET /api/v1/dossiers/{id} (Chi tiết hồ sơ kèm danh sách documents đã lọc)
- PUT / PATCH /api/v1/dossiers/{id} (Cập nhật thông tin hồ sơ)
- DELETE /api/v1/dossiers/{id} (Xóa mềm hồ sơ + xóa mềm dây chuyền tài liệu con cùng đợt)
- POST /api/v1/dossiers/{id}/restore (Khôi phục hồ sơ + khôi phục tài liệu con bị xóa cùng đợt)
- GET /api/v1/dossiers/{id}/documents (Lấy danh sách tài liệu của một hồ sơ)
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, Query, status, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DossierStatus, DocumentType
from app.schemas import (
    DossierCreate,
    DossierUpdate,
    DossierOut,
    DossierDetailOut,
    DocumentOut,
    PaginationResponse,
    MessageResponse,
)
from app.services import dossier_service, document_service

router = APIRouter(prefix="/dossiers", tags=["Bộ hồ sơ thẩm định"])


@router.get(
    "",
    response_model=PaginationResponse[DossierOut],
    summary="Lấy danh sách bộ hồ sơ (phân trang & tìm kiếm)",
)
def list_dossiers(
    page: int = Query(1, ge=1, description="Số thứ tự trang"),
    page_size: int = Query(10, ge=1, le=100, description="Số lượng hồ sơ mỗi trang"),
    q: Optional[str] = Query(None, description="Từ khóa tìm kiếm theo tên hoặc mô tả"),
    status: Optional[DossierStatus] = Query(None, description="Lọc theo trạng thái hồ sơ"),
    include_deleted: bool = Query(False, description="Xem cả hồ sơ đã bị xóa mềm"),
    db: Session = Depends(get_db),
):
    items, total = dossier_service.get_dossiers(
        db=db,
        page=page,
        page_size=page_size,
        q=q,
        status_filter=status,
        include_deleted=include_deleted,
    )
    return PaginationResponse(items=items, total=total, page=page, page_size=page_size)


@router.post(
    "",
    response_model=DossierOut,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo mới bộ hồ sơ",
)
def create_dossier(
    payload: DossierCreate,
    db: Session = Depends(get_db),
):
    return dossier_service.create_dossier(db=db, payload=payload)


@router.get(
    "/{dossier_id}",
    response_model=DossierDetailOut,
    summary="Lấy thông tin chi tiết một bộ hồ sơ kèm danh sách tài liệu",
)
def get_dossier(
    dossier_id: int,
    include_deleted: bool = Query(False, description="Bao gồm cả tài liệu đã xóa mềm trong hồ sơ"),
    db: Session = Depends(get_db),
):
    """
    Theo quy chuẩn, DossierDetailOut chỉ trả về documents đang hoạt động (is_deleted=False),
    trừ khi người dùng truyền include_deleted=True.
    """
    return dossier_service.get_dossier_detail(
        db=db, dossier_id=dossier_id, include_deleted=include_deleted
    )


@router.put(
    "/{dossier_id}",
    response_model=DossierOut,
    summary="Cập nhật toàn bộ thông tin bộ hồ sơ",
)
@router.patch(
    "/{dossier_id}",
    response_model=DossierOut,
    summary="Cập nhật một phần thông tin bộ hồ sơ",
)
def update_dossier(
    dossier_id: int,
    payload: DossierUpdate,
    db: Session = Depends(get_db),
):
    return dossier_service.update_dossier(
        db=db, dossier_id=dossier_id, payload=payload
    )


@router.delete(
    "/{dossier_id}",
    response_model=MessageResponse,
    summary="Xóa mềm bộ hồ sơ (kéo theo các tài liệu đang hoạt động)",
)
def delete_dossier(
    dossier_id: int,
    db: Session = Depends(get_db),
):
    """
    Khi xóa mềm một dossier, hệ thống sẽ tự động xóa mềm luôn các documents đang hoạt động
    của nó với CÙNG giá trị deleted_at (Cascading Soft Delete).
    """
    affected_docs = dossier_service.soft_delete_dossier(db=db, dossier_id=dossier_id)
    return MessageResponse(
        message=f"Đã xóa mềm bộ hồ sơ ID {dossier_id} thành công.",
        detail=f"Đồng thời xóa mềm {affected_docs} tài liệu liên quan.",
    )


@router.post(
    "/{dossier_id}/restore",
    response_model=DossierDetailOut,
    summary="Khôi phục bộ hồ sơ (kéo theo các tài liệu bị xóa cùng đợt)",
)
def restore_dossier(
    dossier_id: int,
    db: Session = Depends(get_db),
):
    """
    Khôi phục dossier và chỉ tự động khôi phục các documents bị xóa CÙNG ĐỢT (cùng deleted_at)
    với dossier đó. Các tài liệu bị xóa riêng trước đó vẫn giữ nguyên trạng thái đã xóa.
    """
    return dossier_service.restore_dossier(db=db, dossier_id=dossier_id)


@router.get(
    "/{dossier_id}/documents",
    response_model=List[DocumentOut],
    summary="Lấy danh sách tài liệu thuộc bộ hồ sơ",
)
def list_dossier_documents(
    dossier_id: int,
    include_deleted: bool = Query(False, description="Bao gồm cả tài liệu đã xóa mềm"),
    db: Session = Depends(get_db),
):
    """
    Trả về danh sách tài liệu thuộc bộ hồ sơ.
    Chỉ trả về các tài liệu đang hoạt động trừ khi include_deleted=True.
    """
    return dossier_service.get_dossier_documents(
        db=db, dossier_id=dossier_id, include_deleted=include_deleted
    )


@router.post(
    "/{dossier_id}/documents",
    response_model=DocumentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Upload và parse tài liệu vào bộ hồ sơ",
)
def upload_dossier_document(
    dossier_id: int,
    file: UploadFile = File(..., description="Tệp tài liệu tải lên (PDF, DOCX, JPG, PNG)"),
    document_type: DocumentType = Form(DocumentType.OTHER, description="Loại tài liệu"),
    db: Session = Depends(get_db),
):
    """
    Tải file tài liệu lên gắn vào bộ hồ sơ, tự động lưu file vật lý và phân tích nội dung (parse).
    Hàm định nghĩa đồng bộ (def) để FastAPI tự động dispatch sang threadpool, không chặn event loop.
    """
    return document_service.upload_document_to_dossier(
        db=db,
        dossier_id=dossier_id,
        file=file,
        document_type=document_type,
    )

