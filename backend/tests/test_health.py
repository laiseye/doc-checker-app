"""
Kiểm thử Endpoint Kiểm tra Sức khỏe (/api/v1/health)
"""

def test_health_check_endpoint(client):
    """Kiểm tra GET /api/v1/health trả về status 200 và kết nối database ok"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"
    assert data["version"] == "1.0.0"
