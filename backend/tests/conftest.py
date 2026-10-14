"""
Cấu hình Fixture cho Pytest (Test Configuration & Fixtures)
-----------------------------------------------------------
- Sử dụng SQLite in-memory (:memory:) với StaticPool để đảm bảo toàn bộ request
  trong cùng một test case truy cập vào cùng một CSDL tạm thời.
- Tự động tạo bảng (create_all) trước mỗi test và dọn dẹp (drop_all) sau mỗi test.
- Ghi đè dependency get_db của FastAPI bằng session test.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

# Sử dụng SQLite in-memory với StaticPool
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session():
    """Tạo mới schema CSDL cho mỗi test function và drop sau khi hoàn tất"""
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    """
    TestClient gọi vào FastAPI app, đã được override dependency get_db
    để trỏ sang CSDL SQLite in-memory của test.
    """
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
