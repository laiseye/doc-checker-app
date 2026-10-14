"""
Router kiểm tra trạng thái hệ thống (Health Check)
--------------------------------------------------
Endpoint: GET /api/v1/health
Mục đích: Xác thực server đang chạy và kết nối cơ sở dữ liệu hoạt động bình thường.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database import get_db

router = APIRouter(tags=["Hệ thống"])


@router.get(
    "/health",
    summary="Kiểm tra sức khỏe hệ thống",
    status_code=status.HTTP_200_OK,
)
def check_health(db: Session = Depends(get_db)):
    """
    Kiểm tra trạng thái server FastAPI và kết nối tới CSDL SQLite.
    Nếu kết nối CSDL thành công, trả về trạng thái ok.
    """
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "ok",
        "app_name": "Quản lý & Kiểm tra Hồ sơ điện tử NCKH",
        "version": "1.0.0",
        "phase": "Giai đoạn 2 - Upload tài liệu & Document Parser",
        "database": db_status,
    }
