"""
Module quản lý kết nối Cơ sở dữ liệu (Database Connection)
---------------------------------------------------------
- Sử dụng SQLAlchemy 2.x.
- Tự động chuẩn hóa đường dẫn SQLite thành ĐƯỜNG DẪN TUYỆT ĐỐI từ thư mục gốc dự án,
  giúp Alembic và Server luôn dùng chung một file DB dù chạy lệnh từ bất cứ đâu.
- Cung cấp kiểu dữ liệu UTCDateTime để giải quyết triệt để vấn đề so sánh naive/aware datetime của SQLite.
"""

import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Generator
from dotenv import load_dotenv
from sqlalchemy import create_engine, types, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# ==============================================================================
# 1. XÁC ĐỊNH THƯ MỤC GỐC DỰ ÁN VÀ NẠP BIẾN MÔI TRƯỜNG
# ==============================================================================
# File này nằm tại: [ROOT]/backend/app/database.py -> lùi 3 cấp thư mục để về [ROOT]
ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# Nạp file .env từ thư mục gốc dự án
env_path = ROOT_DIR / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

# Lấy DATABASE_URL, mặc định là sqlite:///./app.db
RAW_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

# ==============================================================================
# 2. CHUẨN HÓA ĐƯỜNG DẪN DATABASE SQLITE VỀ ĐƯỜNG DẪN TUYỆT ĐỐI
# ==============================================================================
def get_normalized_database_url(url: str) -> str:
    """
    Chuẩn hóa URL kết nối SQLite để luôn trỏ chính xác về thư mục gốc dự án.
    Ví dụ: 'sqlite:///./app.db' -> 'sqlite:///D:/doc_checker_app/app.db'
    """
    if url.startswith("sqlite:///./") or url.startswith("sqlite:////."):
        # Lấy tên file db phía sau ./
        relative_file = url.split("sqlite:///", 1)[1].lstrip("./\\")
        absolute_file = (ROOT_DIR / relative_file).resolve()
        # Chuyển dấu gạch chéo ngược trên Windows sang gạch chéo xuôi cho URL
        normalized = f"sqlite:///{absolute_file.as_posix()}"
        return normalized
    elif url == "sqlite:///app.db":
        absolute_file = (ROOT_DIR / "app.db").resolve()
        return f"sqlite:///{absolute_file.as_posix()}"
    return url

DATABASE_URL = get_normalized_database_url(RAW_DATABASE_URL)

# ==============================================================================
# 3. ĐỊNH NGHĨA KIỂU DỮ LIỆU UTCDateTime CHO SQLITE
# ==============================================================================
class UTCDateTime(types.TypeDecorator):
    """
    Kiểu dữ liệu DateTime đảm bảo:
    - Khi ghi vào CSDL: Tự động chuyển đổi sang múi giờ chuẩn UTC.
    - Khi đọc từ CSDL (đặc biệt là SQLite vốn lưu chuỗi text): Luôn gắn tzinfo=timezone.utc,
      tránh triệt để lỗi so sánh giữa naive datetime (không múi giờ) và aware datetime (có múi giờ).
    """
    impl = types.DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            if not isinstance(value, datetime):
                raise TypeError("Giá trị phải là đối tượng datetime")
            if value.tzinfo is None:
                # Nếu truyền naive datetime, coi như là giờ UTC
                value = value.replace(tzinfo=timezone.utc)
            else:
                # Chuyển đổi chính xác sang UTC
                value = value.astimezone(timezone.utc)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            if value.tzinfo is None:
                # Gán nhãn UTC cho dữ liệu trả về từ SQLite
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        return value

def get_utc_now() -> datetime:
    """Hàm tiện ích trả về thời gian hiện tại theo chuẩn UTC có thông tin timezone"""
    return datetime.now(timezone.utc)


# ==============================================================================
# BẬT RÀNG BUỘC KHÓA NGOẠI (FOREIGN KEYS) CHO SQLITE
# ==============================================================================
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """
    Bật tính năng kiểm tra khóa ngoại (Foreign Keys) cho mọi kết nối SQLite.
    Theo mặc định, SQLite tắt PRAGMA foreign_keys nên cần lệnh này để đảm bảo toàn vẹn dữ liệu.
    """
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    except Exception:
        pass

# ==============================================================================
# 4. KHỞI TẠO ENGINE VÀ SESSIONMAKER
# ==============================================================================
connect_args = {}
if "sqlite" in DATABASE_URL:
    # Với SQLite, cần tắt check_same_thread để cho phép FastAPI xử lý đa luồng an toàn
    connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False  # Đặt True nếu muốn in log câu lệnh SQL ra console khi debug
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class cho toàn bộ ORM Models theo chuẩn SQLAlchemy 2.x
Base = declarative_base()

# ==============================================================================
# 5. DEPENDENCY get_db CHO FASTAPI
# ==============================================================================
def get_db() -> Generator[Session, None, None]:
    """
    FastAPI Dependency: Tạo và cung cấp phiên làm việc (Session) cho mỗi request HTTP.
    Đảm bảo tự động đóng kết nối sau khi request hoàn thành để tránh rò rỉ tài nguyên.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
