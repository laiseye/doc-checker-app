"""
Điểm khởi chạy ứng dụng FastAPI (Main Application Entrypoint)
------------------------------------------------------------
- Cấu hình CORS middleware từ biến môi trường CORS_ORIGINS.
- Đăng ký các router tiền tố /api/v1: health, regulations, dossiers, documents.
- Phục vụ trực tiếp giao diện người dùng tĩnh (Frontend Static Files) tại "/".
"""

import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.database import ROOT_DIR
from app.routers import health, regulations, dossiers, documents

# ==============================================================================
# 1. KHỞI TẠO ỨNG DỤNG FASTAPI
# ==============================================================================
app = FastAPI(
    title="Hệ thống Quản lý & Kiểm tra Hồ sơ điện tử NCKH",
    description=(
        "API phục vụ Quản lý & Kiểm tra Hồ sơ Hợp đồng Cung ứng Lao động Việt Nam "
        "đi làm việc ở nước ngoài. Giai đoạn 1: CRUD, Cơ sở dữ liệu và Giao diện quản lý."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ==============================================================================
# 2. CẤU HÌNH BẢO MẬT CORS (CROSS-ORIGIN RESOURCE SHARING)
# ==============================================================================
# Đọc danh sách domain được phép từ biến môi trường, tuyệt đối không dùng "*"
raw_cors = os.getenv("CORS_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000")
origins = [origin.strip() for origin in raw_cors.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# ==============================================================================
# 3. ĐĂNG KÝ CÁC ROUTER API VỚI TIỀN TỐ /api/v1
# ==============================================================================
app.include_router(health.router, prefix="/api/v1")
app.include_router(regulations.router, prefix="/api/v1")
app.include_router(dossiers.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")

# ==============================================================================
# 4. PHỤC VỤ GIAO DIỆN TĨNH (FRONTEND)
# ==============================================================================
FRONTEND_DIR = ROOT_DIR / "frontend"

# Đảm bảo thư mục frontend tồn tại trước khi mount
if not FRONTEND_DIR.exists():
    FRONTEND_DIR.mkdir(parents=True, exist_ok=True)

# Endpoint phục vụ trang chủ index.html
@app.get("/", include_in_schema=False)
def serve_home():
    """Phục vụ file index.html chính của giao diện web"""
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {
        "message": "Hệ thống Quản lý & Kiểm tra Hồ sơ điện tử NCKH",
        "docs": "/docs",
        "health": "/api/v1/health",
        "status": "Frontend index.html đang được khởi tạo.",
    }

# Mount toàn bộ thư mục frontend tại gốc để nạp css, js tĩnh
# Mount sau cùng để không chặn các đường dẫn /api/v1 và /docs
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
