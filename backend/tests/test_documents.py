"""
Kiểm thử Toàn diện cho Tài liệu trong Hồ sơ (/api/v1/documents)
--------------------------------------------------------------
- CRUD tài liệu trong hồ sơ.
- Ràng buộc: Chặn tạo tài liệu vào bộ hồ sơ đang bị xóa mềm -> 400.
- Ràng buộc: Chặn khôi phục tài liệu khi bộ hồ sơ cha đang bị xóa mềm -> 400.
"""

def test_documents_crud(client):
    """Kiểm tra CRUD tài liệu hợp lệ"""
    # 1. Tạo dossier
    res_d = client.post("/api/v1/dossiers", json={"name": "Hồ sơ test document CRUD"})
    d_id = res_d.json()["id"]

    # 2. Tạo document
    res_create = client.post(
        "/api/v1/documents",
        json={
            "dossier_id": d_id,
            "document_type": "CONTRACT",
            "original_name": "hop_dong_lao_dong_2026.pdf",
        },
    )
    assert res_create.status_code == 201
    doc_data = res_create.json()
    doc_id = doc_data["id"]
    assert doc_data["document_type"] == "CONTRACT"
    assert doc_data["original_name"] == "hop_dong_lao_dong_2026.pdf"
    assert doc_data["is_deleted"] is False

    # 3. Cập nhật document
    res_update = client.patch(
        f"/api/v1/documents/{doc_id}",
        json={"original_name": "hop_dong_lao_dong_da_ky.pdf", "document_type": "APPROVAL"},
    )
    assert res_update.status_code == 200
    assert res_update.json()["original_name"] == "hop_dong_lao_dong_da_ky.pdf"
    assert res_update.json()["document_type"] == "APPROVAL"

    # 4. Xóa mềm document
    res_del = client.delete(f"/api/v1/documents/{doc_id}")
    assert res_del.status_code == 200

    # Mặc định không thấy
    res_get = client.get(f"/api/v1/documents/{doc_id}")
    assert res_get.status_code == 404

    # Khôi phục document
    res_restore = client.post(f"/api/v1/documents/{doc_id}/restore")
    assert res_restore.status_code == 200
    assert res_restore.json()["is_deleted"] is False


def test_prevent_create_document_in_deleted_dossier(client):
    """Không cho phép tạo tài liệu vào dossier đang bị xóa mềm -> 400"""
    # Tạo và xóa mềm dossier
    res_d = client.post("/api/v1/dossiers", json={"name": "Dossier sắp xóa"})
    d_id = res_d.json()["id"]
    client.delete(f"/api/v1/dossiers/{d_id}")

    # Thử tạo document vào dossier đã xóa
    res_doc = client.post(
        "/api/v1/documents",
        json={
            "dossier_id": d_id,
            "document_type": "CONTRACT",
            "original_name": "file_bi_chan.pdf",
        },
    )
    assert res_doc.status_code == 400
    assert "đang bị xóa" in res_doc.json()["detail"]


def test_prevent_restore_document_in_deleted_dossier(client):
    """Không cho phép khôi phục tài liệu nếu dossier cha đang bị xóa mềm -> 400"""
    # 1. Tạo dossier và document
    res_d = client.post("/api/v1/dossiers", json={"name": "Dossier cha"})
    d_id = res_d.json()["id"]

    res_doc = client.post(
        "/api/v1/documents",
        json={"dossier_id": d_id, "document_type": "LICENSE", "original_name": "doc_test.pdf"},
    )
    doc_id = res_doc.json()["id"]

    # 2. Xóa mềm document
    client.delete(f"/api/v1/documents/{doc_id}")

    # 3. Xóa mềm dossier
    client.delete(f"/api/v1/dossiers/{d_id}")

    # 4. Thử khôi phục document đơn lẻ khi dossier cha vẫn đang bị xóa -> Phải trả lỗi 400
    res_restore = client.post(f"/api/v1/documents/{doc_id}/restore")
    assert res_restore.status_code == 400
    assert "bộ hồ sơ chứa nó đang bị xóa" in res_restore.json()["detail"]
