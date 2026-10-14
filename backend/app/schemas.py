"""
Module định nghĩa các Lược đồ Pydantic (Data Schemas & Validation)
-----------------------------------------------------------------
Sử dụng Pydantic v2 để kiểm thực dữ liệu (Validate) cho đầu vào và đầu ra của API:
- Kiểm tra kiểu dữ liệu, độ dài chuỗi, định dạng ngày tháng Date/DateTime.
- Ràng buộc ngày hiệu lực: effective_to >= effective_from.
- Cấu trúc phản hồi phân trang chuẩn hóa: items, total, page, page_size.
- Trả về thông báo lỗi rõ ràng, chi tiết bằng Tiếng Việt.
"""

from datetime import date, datetime
from typing import Generic, List, Optional, TypeVar
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.models import RegulationStatus, DossierStatus, DocumentType

# TypeVar dùng cho lược đồ phân trang Generic
T = TypeVar("T")


# ==============================================================================
# 1. LƯỢC ĐỒ PHÂN TRANG CHUẨN HÓA (PAGINATION)
# ==============================================================================
class PaginationResponse(BaseModel, Generic[T]):
    """Phản hồi danh sách phân trang thống nhất cho toàn bộ hệ thống"""
    items: List[T] = Field(..., description="Danh sách các bản ghi của trang hiện tại")
    total: int = Field(..., description="Tổng số bản ghi thỏa mãn điều kiện lọc")
    page: int = Field(..., ge=1, description="Số thứ tự trang hiện tại (bắt đầu từ 1)")
    page_size: int = Field(..., ge=1, le=100, description="Số bản ghi trên mỗi trang")


class MessageResponse(BaseModel):
    """Phản hồi thông báo chung (khi xóa, khôi phục thành công)"""
    message: str
    detail: Optional[str] = None


# ==============================================================================
# 2. LƯỢC ĐỒ VĂN BẢN QUY ĐỊNH (REGULATIONS)
# ==============================================================================
class RegulationBase(BaseModel):
    """Các trường thông tin cơ bản của văn bản quy định"""
    title: str = Field(..., min_length=1, max_length=255, description="Tiêu đề văn bản")
    identifier: str = Field(..., min_length=1, max_length=100, description="Số hiệu văn bản (VD: 69/2020/QH14)")
    version: str = Field("1.0", min_length=1, max_length=50, description="Phiên bản áp dụng (VD: 1.0, 2020)")
    issuing_body: str = Field(..., min_length=1, max_length=255, description="Cơ quan ban hành (VD: Quốc hội)")
    effective_from: date = Field(..., description="Ngày bắt đầu có hiệu lực (Kiểu Date: YYYY-MM-DD)")
    effective_to: Optional[date] = Field(None, description="Ngày hết hiệu lực nếu có (Kiểu Date: YYYY-MM-DD)")
    status: RegulationStatus = Field(default=RegulationStatus.ACTIVE, description="Trạng thái hiệu lực")
    source_url: Optional[str] = Field(None, max_length=500, description="Đường dẫn tra cứu văn bản gốc")
    file_path: Optional[str] = Field(None, max_length=500, description="Đường dẫn file (chưa dùng ở Giai đoạn 1)")

    @model_validator(mode="after")
    def validate_effective_dates(self) -> "RegulationBase":
        """Kiểm tra logic nghiệp vụ: effective_to không được trước effective_from"""
        if self.effective_to is not None and self.effective_from is not None:
            if self.effective_to < self.effective_from:
                raise ValueError("Ngày hết hiệu lực (effective_to) không được trước ngày bắt đầu có hiệu lực (effective_from)")
        return self


class RegulationCreate(RegulationBase):
    """Dữ liệu yêu cầu khi tạo mới văn bản quy định"""
    pass


class RegulationUpdate(BaseModel):
    """Dữ liệu yêu cầu khi cập nhật văn bản quy định (toàn bộ các trường là tùy chọn)"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    identifier: Optional[str] = Field(None, min_length=1, max_length=100)
    version: Optional[str] = Field(None, min_length=1, max_length=50)
    issuing_body: Optional[str] = Field(None, min_length=1, max_length=255)
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    status: Optional[RegulationStatus] = None
    source_url: Optional[str] = Field(None, max_length=500)
    file_path: Optional[str] = Field(None, max_length=500)

    @model_validator(mode="after")
    def validate_update_dates(self) -> "RegulationUpdate":
        """Kiểm tra ngày nếu cả hai cùng được truyền vào khi update"""
        if self.effective_to is not None and self.effective_from is not None:
            if self.effective_to < self.effective_from:
                raise ValueError("Ngày hết hiệu lực (effective_to) không được trước ngày bắt đầu có hiệu lực (effective_from)")
        return self


class RegulationOut(RegulationBase):
    """Dữ liệu trả về chi tiết của văn bản quy định"""
    id: int
    created_at: datetime
    updated_at: datetime
    is_deleted: bool
    deleted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# 3. LƯỢC ĐỒ TÀI LIỆU (DOCUMENTS)
# ==============================================================================
class DocumentBase(BaseModel):
    """Các trường thông tin cơ bản của tài liệu trong hồ sơ"""
    dossier_id: int = Field(..., description="ID của bộ hồ sơ chứa tài liệu")
    document_type: DocumentType = Field(default=DocumentType.OTHER, description="Loại tài liệu")
    original_name: str = Field(..., min_length=1, max_length=255, description="Tên file gốc tài liệu")
    storage_path: Optional[str] = Field(None, max_length=500, description="Đường dẫn lưu trữ nội bộ (nullable)")
    mime_type: Optional[str] = Field(None, max_length=100, description="Loại định dạng MIME (nullable)")


class DocumentCreate(DocumentBase):
    """Dữ liệu yêu cầu khi tạo mới metadata tài liệu"""
    pass


class DocumentUpdate(BaseModel):
    """Dữ liệu yêu cầu khi cập nhật metadata tài liệu"""
    document_type: Optional[DocumentType] = None
    original_name: Optional[str] = Field(None, min_length=1, max_length=255)
    storage_path: Optional[str] = Field(None, max_length=500)
    mime_type: Optional[str] = Field(None, max_length=100)


class DocumentOut(DocumentBase):
    """Dữ liệu trả về của một tài liệu"""
    id: int
    parse_status: str = Field(default="no_file", description="Trạng thái parse: pending, processing, done, needs_ocr, failed, no_file")
    parse_error: Optional[str] = Field(default=None, description="Chi tiết lỗi nếu parse thất bại")
    file_size: Optional[int] = Field(default=None, description="Kích thước tệp tin (bytes)")
    sha256: Optional[str] = Field(default=None, description="Mã băm SHA-256 xác minh file")
    page_count: int = Field(default=0, description="Tổng số trang văn bản đã trích xuất")
    uploaded_at: datetime
    created_at: datetime
    updated_at: datetime
    is_deleted: bool
    deleted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentPageOut(BaseModel):
    """Dữ liệu trả về của một trang tài liệu đã trích xuất text"""
    id: int
    document_id: int
    page_number: int
    raw_text: str
    edited_text: Optional[str] = None
    parser_type: str
    engine_version: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# 4. LƯỢC ĐỒ BỘ HỒ SƠ (DOSSIERS)
# ==============================================================================
class DossierBase(BaseModel):
    """Các trường thông tin cơ bản của bộ hồ sơ thẩm định"""
    name: str = Field(..., min_length=1, max_length=255, description="Tên bộ hồ sơ")
    status: DossierStatus = Field(default=DossierStatus.DRAFT, description="Trạng thái hồ sơ")
    description: Optional[str] = Field(None, description="Ghi chú chi tiết về bộ hồ sơ")


class DossierCreate(DossierBase):
    """Dữ liệu yêu cầu khi tạo mới bộ hồ sơ"""
    pass


class DossierUpdate(BaseModel):
    """Dữ liệu yêu cầu khi cập nhật bộ hồ sơ"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[DossierStatus] = None
    description: Optional[str] = None


class DossierOut(DossierBase):
    """Dữ liệu trả về danh sách bộ hồ sơ"""
    id: int
    created_at: datetime
    updated_at: datetime
    is_deleted: bool
    deleted_at: Optional[datetime] = None
    document_count: Optional[int] = Field(0, description="Số lượng tài liệu hoạt động thuộc hồ sơ")

    model_config = ConfigDict(from_attributes=True)


class DossierDetailOut(DossierOut):
    """
    Dữ liệu trả về chi tiết của một bộ hồ sơ.
    Lưu ý: Chỉ trả về danh sách tài liệu chưa bị xóa (is_deleted=False),
    trừ khi include_deleted=True theo đúng quy tắc nghiệp vụ.
    """
    documents: List[DocumentOut] = Field(default_factory=list, description="Danh sách tài liệu thuộc bộ hồ sơ")

    model_config = ConfigDict(from_attributes=True)
