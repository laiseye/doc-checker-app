"""
Router quản lý Văn bản quy định (Regulations API)
------------------------------------------------
Đường dẫn cơ sở: /api/v1/regulations
Cung cấp đầy đủ các thao tác CRUD và Khôi phục (Restore):
- GET /api/v1/regulations (Phân trang, tìm kiếm, lọc status, include_deleted)
- POST /api/v1/regulations (Tạo mới, kiểm tra unique (identifier, version))
- GET /api/v1/regulations/{id} (Chi tiết)
- PUT / PATCH /api/v1/regulations/{id} (Cập nhật)
- DELETE /api/v1/regulations/{id} (Xóa mềm)
- POST /api/v1/regulations/{id}/restore (Khôi phục)
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import RegulationStatus
from app.schemas import (
    RegulationCreate,
    RegulationUpdate,
    RegulationOut,
    PaginationResponse,
    MessageResponse,
)
from app.services import regulation_service

router = APIRouter(prefix="/regulations", tags=["Văn bản quy định"])


@router.get(
    "",
    response_model=PaginationResponse[RegulationOut],
    summary="Lấy danh sách văn bản quy định (phân trang & tìm kiếm)",
)
def list_regulations(
    page: int = Query(1, ge=1, description="Số trang hiện tại"),
    page_size: int = Query(10, ge=1, le=100, description="Số lượng mục trên mỗi trang"),
    q: Optional[str] = Query(None, description="Từ khóa tìm kiếm (tiêu đề, số hiệu, cơ quan ban hành)"),
    status: Optional[RegulationStatus] = Query(None, description="Lọc theo trạng thái hiệu lực"),
    include_deleted: bool = Query(False, description="Có bao gồm văn bản đã xóa mềm hay không"),
    db: Session = Depends(get_db),
):
    """
    Trả về danh sách văn bản quy định theo trang.
    Mặc định các văn bản đã xóa mềm (is_deleted=True) sẽ bị ẩn.
    """
    items, total = regulation_service.get_regulations(
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
    response_model=RegulationOut,
    status_code=status.HTTP_201_CREATED,
    summary="Thêm mới văn bản quy định",
)
def create_regulation(
    payload: RegulationCreate,
    db: Session = Depends(get_db),
):
    """
    Tạo mới một văn bản quy định.
    Nếu số hiệu và phiên bản đã tồn tại trong trạng thái đã xóa, API trả về lỗi 409
    yêu cầu người dùng khôi phục thay vì tạo mới.
    """
    return regulation_service.create_regulation(db=db, payload=payload)


@router.get(
    "/{regulation_id}",
    response_model=RegulationOut,
    summary="Lấy chi tiết văn bản quy định theo ID",
)
def get_regulation(
    regulation_id: int,
    include_deleted: bool = Query(False, description="Cho phép xem văn bản đã xóa mềm nếu biết ID"),
    db: Session = Depends(get_db),
):
    return regulation_service.get_regulation_by_id(
        db=db, regulation_id=regulation_id, include_deleted=include_deleted
    )


@router.put(
    "/{regulation_id}",
    response_model=RegulationOut,
    summary="Cập nhật toàn bộ thông tin văn bản quy định",
)
@router.patch(
    "/{regulation_id}",
    response_model=RegulationOut,
    summary="Cập nhật một phần thông tin văn bản quy định",
)
def update_regulation(
    regulation_id: int,
    payload: RegulationUpdate,
    db: Session = Depends(get_db),
):
    return regulation_service.update_regulation(
        db=db, regulation_id=regulation_id, payload=payload
    )


@router.delete(
    "/{regulation_id}",
    response_model=MessageResponse,
    summary="Xóa mềm văn bản quy định",
)
def delete_regulation(
    regulation_id: int,
    db: Session = Depends(get_db),
):
    """
    Xóa mềm văn bản quy định. Đặt is_deleted=True và lưu mốc thời gian deleted_at.
    Không xóa vật lý khỏi cơ sở dữ liệu.
    """
    regulation_service.soft_delete_regulation(db=db, regulation_id=regulation_id)
    return MessageResponse(
        message=f"Đã xóa mềm văn bản quy định ID {regulation_id} thành công."
    )


@router.post(
    "/{regulation_id}/restore",
    response_model=RegulationOut,
    summary="Khôi phục văn bản quy định đã xóa mềm",
)
def restore_regulation(
    regulation_id: int,
    db: Session = Depends(get_db),
):
    """Khôi phục lại văn bản đã bị xóa mềm về trạng thái hoạt động bình thường."""
    return regulation_service.restore_regulation(db=db, regulation_id=regulation_id)
