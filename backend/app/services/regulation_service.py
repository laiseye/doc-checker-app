"""
Service xử lý nghiệp vụ cho Văn bản quy định (Regulations)
---------------------------------------------------------
Chịu trách nhiệm:
- Kiểm tra trùng lặp theo cặp (identifier, version).
- Trả lỗi 409 với câu thông báo hướng dẫn khôi phục nếu trùng bản ghi đã xóa mềm.
- Kiểm tra ràng buộc ngày hiệu lực.
- Phân trang, tìm kiếm, lọc trạng thái, xóa mềm và khôi phục.
"""

from typing import Optional, Tuple, List
from fastapi import HTTPException, status
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session

from app.models import Regulation, RegulationStatus
from app.schemas import RegulationCreate, RegulationUpdate
from app.database import get_utc_now


def get_regulations(
    db: Session,
    page: int = 1,
    page_size: int = 10,
    q: Optional[str] = None,
    status_filter: Optional[RegulationStatus] = None,
    include_deleted: bool = False,
) -> Tuple[List[Regulation], int]:
    """
    Lấy danh sách văn bản quy định có phân trang, tìm kiếm và lọc.
    Mặc định không lấy bản ghi đã xóa mềm (is_deleted=True), trừ khi include_deleted=True.
    """
    query = select(Regulation)

    # Lọc theo cờ xóa mềm
    if not include_deleted:
        query = query.where(Regulation.is_deleted == False)

    # Lọc theo trạng thái hiệu lực
    if status_filter is not None:
        val = status_filter.value if hasattr(status_filter, "value") else str(status_filter)
        query = query.where(Regulation.status == val)

    # Tìm kiếm theo từ khóa (tiêu đề, số hiệu, cơ quan ban hành)
    if q and q.strip():
        search_term = f"%{q.strip()}%"
        query = query.where(
            or_(
                Regulation.title.ilike(search_term),
                Regulation.identifier.ilike(search_term),
                Regulation.issuing_body.ilike(search_term),
            )
        )

    # Đếm tổng số bản ghi thỏa điều kiện
    count_stmt = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_stmt) or 0

    # Phân trang và sắp xếp ID giảm dần (mới nhất lên trước)
    offset = (page - 1) * page_size
    items_stmt = query.order_by(Regulation.id.desc()).offset(offset).limit(page_size)
    items = db.scalars(items_stmt).all()

    return list(items), total


def get_regulation_by_id(
    db: Session, regulation_id: int, include_deleted: bool = False
) -> Regulation:
    """Lấy chi tiết một văn bản quy định theo ID"""
    stmt = select(Regulation).where(Regulation.id == regulation_id)
    if not include_deleted:
        stmt = stmt.where(Regulation.is_deleted == False)

    regulation = db.scalar(stmt)
    if not regulation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy văn bản quy định với ID {regulation_id}",
        )
    return regulation


def create_regulation(db: Session, payload: RegulationCreate) -> Regulation:
    """
    Tạo mới một văn bản quy định.
    Quy tắc kiểm tra:
    - Tìm xem cặp (identifier, version) đã tồn tại trong DB chưa.
    - Nếu đã có và đang xóa mềm -> Trả lỗi 409 nhắc người dùng khôi phục.
    - Nếu đã có và đang hoạt động -> Trả lỗi 409 đã tồn tại.
    """
    # 1. Kiểm tra ngày hiệu lực
    if payload.effective_to and payload.effective_from:
        if payload.effective_to < payload.effective_from:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Ngày hết hiệu lực (effective_to) không được trước ngày bắt đầu có hiệu lực (effective_from)",
            )

    # 2. Kiểm tra trùng lặp cặp (identifier, version)
    check_stmt = select(Regulation).where(
        Regulation.identifier == payload.identifier,
        Regulation.version == payload.version,
    )
    existing = db.scalar(check_stmt)
    if existing:
        if existing.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Văn bản với số hiệu '{payload.identifier}' và phiên bản '{payload.version}' "
                    f"đã tồn tại (đang ở trạng thái đã xóa), hãy khôi phục thay vì tạo mới."
                ),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Văn bản với số hiệu '{payload.identifier}' và phiên bản '{payload.version}' "
                    f"đã tồn tại trong hệ thống."
                ),
            )

    # 3. Tạo bản ghi mới
    new_reg = Regulation(
        title=payload.title,
        identifier=payload.identifier,
        version=payload.version,
        issuing_body=payload.issuing_body,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
        status=payload.status.value if hasattr(payload.status, "value") else str(payload.status),
        source_url=payload.source_url,
        file_path=payload.file_path,
        is_deleted=False,
        deleted_at=None,
    )
    db.add(new_reg)
    db.commit()
    db.refresh(new_reg)
    return new_reg


def update_regulation(
    db: Session, regulation_id: int, payload: RegulationUpdate
) -> Regulation:
    """
    Cập nhật thông tin văn bản quy định.
    Nếu sửa identifier hoặc version, phải kiểm tra không trùng với văn bản khác.
    """
    regulation = get_regulation_by_id(db, regulation_id, include_deleted=False)

    update_data = payload.model_dump(exclude_unset=True)

    # Kiểm tra ngày hiệu lực sau cập nhật
    new_from = update_data.get("effective_from", regulation.effective_from)
    new_to = update_data.get("effective_to", regulation.effective_to)
    if new_to and new_from and new_to < new_from:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Ngày hết hiệu lực (effective_to) không được trước ngày bắt đầu có hiệu lực (effective_from)",
        )

    # Kiểm tra trùng lặp (identifier, version) nếu có thay đổi
    new_identifier = update_data.get("identifier", regulation.identifier)
    new_version = update_data.get("version", regulation.version)
    if new_identifier != regulation.identifier or new_version != regulation.version:
        conflict_stmt = select(Regulation).where(
            Regulation.identifier == new_identifier,
            Regulation.version == new_version,
            Regulation.id != regulation.id,
        )
        conflict = db.scalar(conflict_stmt)
        if conflict:
            if conflict.is_deleted:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Văn bản với số hiệu '{new_identifier}' và phiên bản '{new_version}' "
                        f"đã tồn tại (đang ở trạng thái đã xóa), hãy khôi phục thay vì cập nhật trùng."
                    ),
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Văn bản với số hiệu '{new_identifier}' và phiên bản '{new_version}' đã tồn tại trong hệ thống.",
                )

    # Thực hiện cập nhật các trường
    for key, value in update_data.items():
        if key == "status" and value is not None:
            value = value.value if hasattr(value, "value") else str(value)
        setattr(regulation, key, value)

    regulation.updated_at = get_utc_now()
    db.commit()
    db.refresh(regulation)
    return regulation


def soft_delete_regulation(db: Session, regulation_id: int) -> None:
    """Xóa mềm văn bản quy định: Đặt is_deleted=True và ghi nhận deleted_at UTC"""
    regulation = get_regulation_by_id(db, regulation_id, include_deleted=False)
    now_utc = get_utc_now()
    regulation.is_deleted = True
    regulation.deleted_at = now_utc
    regulation.updated_at = now_utc
    db.commit()


def restore_regulation(db: Session, regulation_id: int) -> Regulation:
    """
    Khôi phục văn bản quy định đã bị xóa mềm.
    Kiểm tra xem cặp (identifier, version) có bị xung đột với văn bản đang active nào khác không.
    """
    regulation = get_regulation_by_id(db, regulation_id, include_deleted=True)
    if not regulation.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Văn bản ID {regulation_id} đang ở trạng thái hoạt động, không cần khôi phục.",
        )

    # Kiểm tra xem có bản ghi active nào khác trùng (identifier, version) không
    conflict_stmt = select(Regulation).where(
        Regulation.identifier == regulation.identifier,
        Regulation.version == regulation.version,
        Regulation.is_deleted == False,
        Regulation.id != regulation.id,
    )
    conflict = db.scalar(conflict_stmt)
    if conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Không thể khôi phục vì đã có văn bản hoạt động khác (ID {conflict.id}) "
                f"mang số hiệu '{regulation.identifier}' và phiên bản '{regulation.version}'."
            ),
        )

    regulation.is_deleted = False
    regulation.deleted_at = None
    regulation.updated_at = get_utc_now()
    db.commit()
    db.refresh(regulation)
    return regulation
