"""
Service xử lý nghiệp vụ cho Bộ hồ sơ thẩm định (Dossiers)
---------------------------------------------------------
Chịu trách nhiệm:
- CRUD bộ hồ sơ.
- Đếm số lượng tài liệu hoạt động.
- Xóa mềm dây chuyền (Cascading Soft Delete): Xóa dossier kéo theo xóa các documents đang hoạt động với CÙNG deleted_at.
- Khôi phục dây chuyền (Cascading Restore): Khôi phục dossier chỉ khôi phục các documents bị xóa CÙNG ĐỢT (cùng deleted_at).
- Đảm bảo DossierDetailOut và danh sách documents chỉ trả tài liệu hoạt động trừ khi include_deleted=True.
"""

from typing import Optional, Tuple, List
from fastapi import HTTPException, status
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session

from app.models import Dossier, DossierStatus, Document
from app.schemas import DossierCreate, DossierUpdate, DossierDetailOut, DocumentOut
from app.database import get_utc_now


def get_dossiers(
    db: Session,
    page: int = 1,
    page_size: int = 10,
    q: Optional[str] = None,
    status_filter: Optional[DossierStatus] = None,
    include_deleted: bool = False,
) -> Tuple[List[Dossier], int]:
    """
    Lấy danh sách bộ hồ sơ có phân trang, tìm kiếm và lọc.
    Đồng thời tính toán document_count (số tài liệu đang hoạt động) cho mỗi hồ sơ.
    """
    query = select(Dossier)

    # Lọc xóa mềm
    if not include_deleted:
        query = query.where(Dossier.is_deleted == False)

    # Lọc trạng thái
    if status_filter is not None:
        val = status_filter.value if hasattr(status_filter, "value") else str(status_filter)
        query = query.where(Dossier.status == val)

    # Tìm kiếm theo tên hoặc mô tả
    if q and q.strip():
        search_term = f"%{q.strip()}%"
        query = query.where(
            or_(
                Dossier.name.ilike(search_term),
                Dossier.description.ilike(search_term),
            )
        )

    # Đếm tổng số bản ghi thỏa điều kiện
    count_stmt = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_stmt) or 0

    # Phân trang và sắp xếp mới nhất lên trước
    offset = (page - 1) * page_size
    items_stmt = query.order_by(Dossier.id.desc()).offset(offset).limit(page_size)
    dossiers = list(db.scalars(items_stmt).all())

    # Tính số lượng tài liệu đang hoạt động cho từng dossier
    if dossiers:
        dossier_ids = [d.id for d in dossiers]
        count_query = (
            select(Document.dossier_id, func.count(Document.id))
            .where(
                Document.dossier_id.in_(dossier_ids),
                Document.is_deleted == False,
            )
            .group_by(Document.dossier_id)
        )
        counts_dict = dict(db.execute(count_query).all())
        for d in dossiers:
            d.document_count = counts_dict.get(d.id, 0)
    else:
        for d in dossiers:
            d.document_count = 0

    return dossiers, total


def get_dossier_by_id(
    db: Session, dossier_id: int, include_deleted: bool = False
) -> Dossier:
    """
    Lấy đối tượng ORM Dossier theo ID.
    Không chỉnh sửa hoặc gán đè lên relationship documents để tránh kích hoạt cơ chế xóa của SQLAlchemy.
    """
    stmt = select(Dossier).where(Dossier.id == dossier_id)
    if not include_deleted:
        stmt = stmt.where(Dossier.is_deleted == False)

    dossier = db.scalar(stmt)
    if not dossier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy bộ hồ sơ với ID {dossier_id}",
        )
    return dossier


def get_dossier_detail(
    db: Session, dossier_id: int, include_deleted: bool = False
) -> DossierDetailOut:
    """
    Lấy thông tin chi tiết của một bộ hồ sơ dưới dạng DossierDetailOut.
    Chỉ nạp danh sách tài liệu chưa bị xóa mềm vào documents, trừ khi include_deleted=True.
    """
    dossier = get_dossier_by_id(db, dossier_id, include_deleted=include_deleted)

    # Truy vấn tường minh danh sách documents theo yêu cầu quy chuẩn
    doc_stmt = select(Document).where(Document.dossier_id == dossier.id)
    if not include_deleted:
        doc_stmt = doc_stmt.where(Document.is_deleted == False)
    docs = list(db.scalars(doc_stmt.order_by(Document.id.asc())).all())

    # Gán số lượng trang cho từng document mà không nạp raw_text
    from app.services.document_service import attach_page_counts
    attach_page_counts(db, docs)

    # Đóng gói an toàn sang Pydantic schema mà không can thiệp vào ORM collection
    out = DossierDetailOut.model_validate(dossier)
    out.documents = [DocumentOut.model_validate(d) for d in docs]
    out.document_count = len([d for d in docs if not d.is_deleted])
    return out


def create_dossier(db: Session, payload: DossierCreate) -> Dossier:
    """Tạo mới một bộ hồ sơ thẩm định"""
    status_val = payload.status.value if hasattr(payload.status, "value") else str(payload.status)
    new_dossier = Dossier(
        name=payload.name,
        status=status_val,
        description=payload.description,
        is_deleted=False,
        deleted_at=None,
    )
    db.add(new_dossier)
    db.commit()
    db.refresh(new_dossier)
    new_dossier.document_count = 0
    return new_dossier


def update_dossier(db: Session, dossier_id: int, payload: DossierUpdate) -> Dossier:
    """Cập nhật thông tin bộ hồ sơ"""
    dossier = get_dossier_by_id(db, dossier_id, include_deleted=False)

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == "status" and value is not None:
            value = value.value if hasattr(value, "value") else str(value)
        setattr(dossier, key, value)

    dossier.updated_at = get_utc_now()
    db.commit()
    db.refresh(dossier)
    return dossier


def soft_delete_dossier(db: Session, dossier_id: int) -> int:
    """
    Xóa mềm bộ hồ sơ VÀ xóa mềm dây chuyền các tài liệu đang hoạt động thuộc về nó.
    Các tài liệu này sẽ được ghi nhận CÙNG giá trị deleted_at với bộ hồ sơ.
    Các tài liệu đã bị xóa riêng từ trước sẽ giữ nguyên deleted_at cũ.
    Trả về số lượng tài liệu bị xóa mềm cùng đợt.
    """
    dossier = get_dossier_by_id(db, dossier_id, include_deleted=False)
    now_utc = get_utc_now()

    # 1. Đánh dấu xóa mềm cho dossier
    dossier.is_deleted = True
    dossier.deleted_at = now_utc
    dossier.updated_at = now_utc

    # 2. Tìm tất cả documents đang còn hoạt động thuộc dossier này
    active_docs_stmt = select(Document).where(
        Document.dossier_id == dossier.id,
        Document.is_deleted == False,
    )
    active_docs = list(db.scalars(active_docs_stmt).all())

    # 3. Đánh dấu xóa mềm cùng đợt với cùng mốc deleted_at
    for doc in active_docs:
        doc.is_deleted = True
        doc.deleted_at = now_utc
        doc.updated_at = now_utc

    affected_count = len(active_docs)
    db.commit()
    return affected_count


def restore_dossier(db: Session, dossier_id: int) -> DossierDetailOut:
    """
    Khôi phục bộ hồ sơ và khôi phục dây chuyền các tài liệu bị xóa CÙNG ĐỢT.
    Tài liệu cùng đợt là tài liệu có doc.deleted_at == dossier.deleted_at (trước khi khôi phục).
    Tài liệu bị xóa riêng trước đó sẽ không bị khôi phục nhầm.
    """
    dossier = get_dossier_by_id(db, dossier_id, include_deleted=True)
    if not dossier.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bộ hồ sơ ID {dossier_id} đang hoạt động, không cần khôi phục.",
        )

    target_deleted_at = dossier.deleted_at
    now_utc = get_utc_now()

    # 1. Khôi phục dossier
    dossier.is_deleted = False
    dossier.deleted_at = None
    dossier.updated_at = now_utc

    # 2. Khôi phục các tài liệu bị xóa cùng đợt
    if target_deleted_at is not None:
        batch_docs_stmt = select(Document).where(
            Document.dossier_id == dossier.id,
            Document.is_deleted == True,
            Document.deleted_at == target_deleted_at,
        )
        batch_docs = list(db.scalars(batch_docs_stmt).all())
        for doc in batch_docs:
            doc.is_deleted = False
            doc.deleted_at = None
            doc.updated_at = now_utc

    db.commit()

    # Trả về chi tiết sau khôi phục
    return get_dossier_detail(db, dossier_id, include_deleted=False)


def get_dossier_documents(
    db: Session, dossier_id: int, include_deleted: bool = False
) -> List[Document]:
    """Lấy danh sách tài liệu của một hồ sơ cụ thể"""
    # Đảm bảo dossier tồn tại
    _ = get_dossier_by_id(db, dossier_id, include_deleted=include_deleted)

    doc_stmt = select(Document).where(Document.dossier_id == dossier_id)
    if not include_deleted:
        doc_stmt = doc_stmt.where(Document.is_deleted == False)

    docs = list(db.scalars(doc_stmt.order_by(Document.id.asc())).all())
    from app.services.document_service import attach_page_counts
    attach_page_counts(db, docs)
    return docs
