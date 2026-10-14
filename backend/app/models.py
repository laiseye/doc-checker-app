"""
Module định nghĩa các Mô hình Cơ sở dữ liệu (ORM Models)
--------------------------------------------------------
Sử dụng phong cách SQLAlchemy 2.x (Mapped, mapped_column).
Bao gồm 3 bảng chính:
1. regulations: Văn bản quy định (pháp lý, quy chuẩn)
2. dossiers: Bộ hồ sơ thẩm định
3. documents: Tài liệu siêu dữ liệu (metadata) thuộc bộ hồ sơ

Mọi bảng đều hỗ trợ cơ chế Xóa mềm (Soft Delete):
- is_deleted: Đánh dấu đã xóa hay chưa (mặc định False)
- deleted_at: Thời điểm xóa mềm tính theo UTC
"""

import enum
from datetime import date, datetime
from typing import Optional, List
from sqlalchemy import (
    String,
    Text,
    Date,
    Integer,
    Boolean,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base, UTCDateTime, get_utc_now

# ==============================================================================
# 1. ĐỊNH NGHĨA CÁC ENUM TRẠNG THÁI VÀ PHÂN LOẠI
# ==============================================================================
class RegulationStatus(str, enum.Enum):
    """Trạng thái hiệu lực của văn bản quy định"""
    ACTIVE = "ACTIVE"    # Có hiệu lực
    EXPIRED = "EXPIRED"  # Hết hiệu lực
    DRAFT = "DRAFT"      # Dự thảo / Chưa ban hành chính thức


class DossierStatus(str, enum.Enum):
    """Trạng thái thẩm định của bộ hồ sơ"""
    DRAFT = "DRAFT"        # Bản nháp mới tạo
    PENDING = "PENDING"    # Chờ thẩm định / kiểm tra
    APPROVED = "APPROVED"  # Đạt yêu cầu thẩm định
    REJECTED = "REJECTED"  # Không đạt yêu cầu


class DocumentType(str, enum.Enum):
    """Phân loại tài liệu trong bộ hồ sơ NCKH hợp đồng cung ứng"""
    CONTRACT = "CONTRACT"        # Hợp đồng cung ứng lao động
    LICENSE = "LICENSE"          # Giấy phép hoạt động dịch vụ
    APPROVAL = "APPROVAL"        # Văn bản chấp thuận đăng ký hợp đồng
    WORKER_LIST = "WORKER_LIST"  # Danh sách lao động xuất cảnh
    OTHER = "OTHER"              # Tài liệu bổ trợ khác


# ==============================================================================
# 2. BẢNG REGULATIONS (VĂN BẢN QUY ĐỊNH)
# ==============================================================================
class Regulation(Base):
    """
    Bảng lưu trữ thông tin văn bản quy định, luật, nghị định, thông tư.
    Ràng buộc quan trọng:
    - UNIQUE theo cặp (identifier, version)
    - effective_from & effective_to dùng kiểu Date
    """
    __tablename__ = "regulations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="Khóa chính ID")
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="Tiêu đề văn bản")
    identifier: Mapped[str] = mapped_column(String(100), nullable=False, index=True, comment="Số hiệu văn bản (VD: 69/2020/QH14)")
    version: Mapped[str] = mapped_column(String(50), default="1.0", nullable=False, comment="Phiên bản áp dụng (VD: 1.0, 2020)")
    issuing_body: Mapped[str] = mapped_column(String(255), nullable=False, comment="Cơ quan ban hành (VD: Quốc hội)")
    effective_from: Mapped[date] = mapped_column(Date, nullable=False, comment="Ngày bắt đầu có hiệu lực")
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True, comment="Ngày hết hiệu lực (nếu có)")
    status: Mapped[str] = mapped_column(String(50), default=RegulationStatus.ACTIVE.value, nullable=False, comment="Trạng thái hiệu lực")
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="Đường dẫn tra cứu văn bản gốc")
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="Đường dẫn file (chưa dùng ở Giai đoạn 1)")

    # Các cột quản lý kiểm toán và xóa mềm
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=get_utc_now, nullable=False, comment="Thời điểm tạo (UTC)")
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False, comment="Thời điểm cập nhật cuối (UTC)")
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False, comment="Đánh dấu xóa mềm")
    deleted_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, nullable=True, comment="Thời điểm xóa mềm (UTC)")

    # Ràng buộc UNIQUE theo cặp (identifier, version)
    __table_args__ = (
        UniqueConstraint("identifier", "version", name="uq_regulations_identifier_version"),
    )

    def __repr__(self) -> str:
        return f"<Regulation id={self.id} identifier='{self.identifier}' version='{self.version}' is_deleted={self.is_deleted}>"


# ==============================================================================
# 3. BẢNG DOSSIERS (BỘ HỒ SƠ THẨM ĐỊNH)
# ==============================================================================
class Dossier(Base):
    """
    Bảng lưu trữ thông tin bộ hồ sơ gồm nhiều tài liệu liên quan đến một hợp đồng.
    """
    __tablename__ = "dossiers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="Khóa chính ID")
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True, comment="Tên bộ hồ sơ thẩm định")
    status: Mapped[str] = mapped_column(String(50), default=DossierStatus.DRAFT.value, nullable=False, comment="Trạng thái bộ hồ sơ (DRAFT, PENDING, APPROVED, REJECTED)")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Ghi chú chi tiết về bộ hồ sơ")

    # Các cột quản lý kiểm toán và xóa mềm
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=get_utc_now, nullable=False, comment="Thời điểm tạo (UTC)")
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False, comment="Thời điểm cập nhật cuối (UTC)")
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False, comment="Đánh dấu xóa mềm")
    deleted_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, nullable=True, comment="Thời điểm xóa mềm (UTC)")

    # Quan hệ 1-Nhiều với bảng Document
    documents: Mapped[List["Document"]] = relationship(
        "Document",
        back_populates="dossier",
        order_by="Document.id"
    )

    def __repr__(self) -> str:
        return f"<Dossier id={self.id} name='{self.name}' status='{self.status}' is_deleted={self.is_deleted}>"


# ==============================================================================
# 4. BẢNG DOCUMENTS (TÀI LIỆU TRONG HỒ SƠ)
# ==============================================================================
class Document(Base):
    """
    Bảng lưu trữ thông tin tài liệu thuộc bộ hồ sơ:
    - Lưu đường dẫn lưu trữ tương đối trong thư mục storage/
    - Lưu mã băm sha256 và kích thước file
    - Lưu trạng thái xử lý parse_status (pending, processing, done, needs_ocr, failed, no_file)
    """
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="Khóa chính ID")
    dossier_id: Mapped[int] = mapped_column(Integer, ForeignKey("dossiers.id"), nullable=False, index=True, comment="Khóa ngoại trỏ đến dossiers.id")
    document_type: Mapped[str] = mapped_column(String(50), default=DocumentType.OTHER.value, nullable=False, comment="Loại tài liệu (CONTRACT, LICENSE, ...)")
    original_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="Tên file gốc tài liệu")
    storage_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="Đường dẫn tương đối của file trong storage/")
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="Định dạng tệp MIME thực tế")
    uploaded_at: Mapped[datetime] = mapped_column(UTCDateTime, default=get_utc_now, nullable=False, comment="Thời điểm ghi nhận tài liệu (UTC)")

    # Các cột bổ sung ở Giai đoạn 2 phục vụ parser và toàn vẹn file
    parse_status: Mapped[str] = mapped_column(
        String(50),
        default="no_file",
        server_default="no_file",
        nullable=False,
        comment="Trạng thái parse: pending, processing, done, needs_ocr, failed, no_file"
    )
    parse_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Chi tiết lỗi khi parse thất bại")
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="Kích thước tệp tin (bytes)")
    sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, comment="Mã băm SHA-256 xác minh file")

    # Các cột quản lý kiểm toán và xóa mềm
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=get_utc_now, nullable=False, comment="Thời điểm tạo (UTC)")
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False, comment="Thời điểm cập nhật cuối (UTC)")
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False, comment="Đánh dấu xóa mềm")
    deleted_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, nullable=True, comment="Thời điểm xóa mềm (UTC)")

    # Quan hệ ngược về Dossier cha
    dossier: Mapped["Dossier"] = relationship("Dossier", back_populates="documents")

    # Quan hệ 1-Nhiều với các trang văn bản đã trích xuất (lazy mặc định, không nạp text tự động)
    pages: Mapped[List["DocumentPage"]] = relationship(
        "DocumentPage",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentPage.page_number",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id} dossier_id={self.dossier_id} original_name='{self.original_name}' parse_status='{self.parse_status}'>"


# ==============================================================================
# 5. BẢNG DOCUMENT_PAGES (TRANG TÀI LIỆU TRÍCH XUẤT)
# ==============================================================================
class DocumentPage(Base):
    """
    Bảng lưu trữ nội dung văn bản trích xuất theo từng trang của tài liệu.
    - PDF: Mỗi trang vật lý ứng với 1 dòng (kể cả trang rỗng).
    - DOCX: Toàn bộ nội dung lưu trong 1 dòng với page_number=1.
    """
    __tablename__ = "document_pages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="Khóa chính ID")
    document_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Khóa ngoại trỏ đến documents.id"
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False, comment="Số thứ tự trang (bắt đầu từ 1)")
    raw_text: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="Nội dung text thô trích xuất từ trang")
    edited_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Nội dung text sau khi hiệu chỉnh thủ công (chưa dùng ở GĐ2)")
    parser_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="Loại parser: 'pymupdf' | 'python-docx'")
    engine_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="Phiên bản thư viện parser")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=get_utc_now, nullable=False, comment="Thời điểm trích xuất trang (UTC)")

    # Ràng buộc duy nhất: mỗi trang chỉ xuất hiện 1 lần trong 1 tài liệu
    __table_args__ = (
        UniqueConstraint("document_id", "page_number", name="uq_document_pages_doc_page"),
    )

    # Quan hệ ngược về Document cha
    document: Mapped["Document"] = relationship("Document", back_populates="pages")

    def __repr__(self) -> str:
        return f"<DocumentPage id={self.id} document_id={self.document_id} page={self.page_number} parser={self.parser_type}>"
