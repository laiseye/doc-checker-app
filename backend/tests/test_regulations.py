"""
Kiểm thử Toàn diện cho Văn bản Quy định (/api/v1/regulations)
------------------------------------------------------------
- CRUD cơ bản: Tạo mới, đọc danh sách, phân trang, tìm kiếm, sửa, xóa mềm, khôi phục.
- Ràng buộc UNIQUE (identifier, version).
- Kiểm tra trùng với bản ghi đã xóa mềm (trả lỗi 409 gợi ý khôi phục).
- Sửa regulation thành trùng (identifier, version) của bản khác -> 409.
- Ràng buộc ngày hiệu lực: effective_to >= effective_from.
"""

def test_create_regulation_success(client):
    """Tạo mới văn bản quy định hợp lệ"""
    payload = {
        "title": "Luật Người lao động Việt Nam đi làm việc ở nước ngoài",
        "identifier": "69/2020/QH14",
        "version": "2020",
        "issuing_body": "Quốc hội",
        "effective_from": "2022-01-01",
        "effective_to": None,
        "status": "ACTIVE",
        "source_url": "https://vanban.chinhphu.vn",
    }
    response = client.post("/api/v1/regulations", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["identifier"] == "69/2020/QH14"
    assert data["version"] == "2020"
    assert data["is_deleted"] is False
    assert data["deleted_at"] is None


def test_create_regulation_invalid_dates(client):
    """Tạo văn bản có ngày hết hiệu lực trước ngày bắt đầu có hiệu lực -> 422"""
    payload = {
        "title": "Văn bản thử nghiệm ngày sai",
        "identifier": "99/2026/TEST",
        "version": "1.0",
        "issuing_body": "Cơ quan test",
        "effective_from": "2026-12-31",
        "effective_to": "2026-01-01",  # Trước effective_from
        "status": "ACTIVE",
    }
    response = client.post("/api/v1/regulations", json=payload)
    assert response.status_code == 422


def test_create_regulation_duplicate_identifier_version(client):
    """Trùng cặp (identifier, version) đang hoạt động -> 409"""
    payload = {
        "title": "Nghị định 112",
        "identifier": "112/2021/NĐ-CP",
        "version": "2021",
        "issuing_body": "Chính phủ",
        "effective_from": "2022-01-01",
        "status": "ACTIVE",
    }
    # Lần 1: Thành công
    res1 = client.post("/api/v1/regulations", json=payload)
    assert res1.status_code == 201

    # Lần 2: Trùng khi đang active -> 409
    res2 = client.post("/api/v1/regulations", json=payload)
    assert res2.status_code == 409
    assert "đã tồn tại trong hệ thống" in res2.json()["detail"]


def test_create_regulation_duplicate_soft_deleted_hint_restore(client):
    """
    Trùng cặp (identifier, version) với bản ghi đã xóa mềm
    -> 409 với câu thông báo hướng dẫn khôi phục thay vì tạo mới.
    """
    payload = {
        "title": "Thông tư mẫu",
        "identifier": "21/2021/TT-BLĐTBXH",
        "version": "2021",
        "issuing_body": "Bộ LĐ-TB&XH",
        "effective_from": "2022-02-01",
        "status": "ACTIVE",
    }
    # 1. Tạo mới
    res1 = client.post("/api/v1/regulations", json=payload)
    assert res1.status_code == 201
    reg_id = res1.json()["id"]

    # 2. Xóa mềm
    res_del = client.delete(f"/api/v1/regulations/{reg_id}")
    assert res_del.status_code == 200

    # 3. Thử tạo lại với cùng cặp (identifier, version)
    res_dup = client.post("/api/v1/regulations", json=payload)
    assert res_dup.status_code == 409
    detail = res_dup.json()["detail"]
    assert "đang ở trạng thái đã xóa" in detail
    assert "hãy khôi phục" in detail


def test_update_regulation_duplicate_identifier_version(client):
    """Sửa regulation thành (identifier, version) trùng với bản ghi khác -> 409"""
    # Tạo văn bản A
    res_a = client.post(
        "/api/v1/regulations",
        json={
            "title": "Văn bản A",
            "identifier": "DOC-A",
            "version": "1.0",
            "issuing_body": "Cơ quan A",
            "effective_from": "2026-01-01",
            "status": "ACTIVE",
        },
    )
    assert res_a.status_code == 201

    # Tạo văn bản B
    res_b = client.post(
        "/api/v1/regulations",
        json={
            "title": "Văn bản B",
            "identifier": "DOC-B",
            "version": "1.0",
            "issuing_body": "Cơ quan B",
            "effective_from": "2026-01-01",
            "status": "ACTIVE",
        },
    )
    assert res_b.status_code == 201
    b_id = res_b.json()["id"]

    # Sửa văn bản B thành trùng identifier và version của A -> Phải trả lỗi 409
    res_update = client.patch(
        f"/api/v1/regulations/{b_id}",
        json={"identifier": "DOC-A", "version": "1.0"},
    )
    assert res_update.status_code == 409
    assert "đã tồn tại" in res_update.json()["detail"]


def test_regulations_list_pagination_and_filter(client):
    """Kiểm tra danh sách, tìm kiếm từ khóa, lọc status và phân trang"""
    # Tạo 3 văn bản
    for i in range(1, 4):
        client.post(
            "/api/v1/regulations",
            json={
                "title": f"Văn bản pháp luật số {i}",
                "identifier": f"QD-{i}/2026",
                "version": "1.0",
                "issuing_body": "Cục Quản lý",
                "effective_from": "2026-01-01",
                "status": "ACTIVE" if i < 3 else "EXPIRED",
            },
        )

    # 1. Phân trang page=1, page_size=2
    res_page = client.get("/api/v1/regulations?page=1&page_size=2")
    assert res_page.status_code == 200
    data = res_page.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["page_size"] == 2

    # 2. Lọc status=EXPIRED
    res_expired = client.get("/api/v1/regulations?status=EXPIRED")
    assert res_expired.status_code == 200
    assert res_expired.json()["total"] == 1
    assert res_expired.json()["items"][0]["identifier"] == "QD-3/2026"

    # 3. Tìm kiếm q="số 2"
    res_search = client.get("/api/v1/regulations?q=số 2")
    assert res_search.status_code == 200
    assert res_search.json()["total"] == 1
    assert res_search.json()["items"][0]["identifier"] == "QD-2/2026"


def test_regulation_soft_delete_and_restore(client):
    """Kiểm tra xóa mềm và khôi phục văn bản quy định"""
    res = client.post(
        "/api/v1/regulations",
        json={
            "title": "Văn bản thử xóa",
            "identifier": "DEL-01",
            "version": "1.0",
            "issuing_body": "Test",
            "effective_from": "2026-01-01",
            "status": "ACTIVE",
        },
    )
    reg_id = res.json()["id"]

    # Xóa mềm
    res_del = client.delete(f"/api/v1/regulations/{reg_id}")
    assert res_del.status_code == 200

    # Mặc định không còn xuất hiện trong danh sách
    res_list = client.get("/api/v1/regulations")
    assert not any(item["id"] == reg_id for item in res_list.json()["items"])

    # Khi truyền include_deleted=true thì tìm thấy
    res_list_deleted = client.get("/api/v1/regulations?include_deleted=true")
    found = next((item for item in res_list_deleted.json()["items"] if item["id"] == reg_id), None)
    assert found is not None
    assert found["is_deleted"] is True
    assert found["deleted_at"] is not None

    # Khôi phục
    res_restore = client.post(f"/api/v1/regulations/{reg_id}/restore")
    assert res_restore.status_code == 200
    assert res_restore.json()["is_deleted"] is False
    assert res_restore.json()["deleted_at"] is None

    # Thử khôi phục lại khi đang active -> 400
    res_re_restore = client.post(f"/api/v1/regulations/{reg_id}/restore")
    assert res_re_restore.status_code == 400
