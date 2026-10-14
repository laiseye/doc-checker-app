"""
Alembic Environment Script
--------------------------
Cấu hình di chuyển dữ liệu (Migration) cho SQLAlchemy 2.x.
Tự động nạp Metadata từ app.models và cấu hình DATABASE_URL tuyệt đối.
"""

import sys
from logging.config import fileConfig
from pathlib import Path
from sqlalchemy import engine_from_config, pool
from alembic import context

# Đường dẫn đến thư mục 'backend' chứa module 'app'
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Nạp Base metadata và DATABASE_URL đã chuẩn hóa tuyệt đối
from app.database import Base, DATABASE_URL, connect_args
import app.models  # noqa: F401 - đảm bảo tất cả bảng được import để Base.metadata nhận diện

# Đối tượng cấu hình Alembic từ alembic.ini
config = context.config

# Thiết lập ghi log theo cấu hình file ini nếu có
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Ghi đè URL trong cấu hình bằng DATABASE_URL tuyệt đối từ app.database
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Chỉ định metadata chứa định nghĩa schema
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Chạy migration ở chế độ offline (tạo file script SQL trực tiếp)"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True if "sqlite" in url else False,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Chạy migration ở chế độ online (kết nối trực tiếp vào DB để cập nhật schema)"""
    configuration = config.get_section(config.config_ini_section)
    if configuration is None:
        configuration = {}
    configuration["sqlalchemy.url"] = DATABASE_URL

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True if "sqlite" in DATABASE_URL else False,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
