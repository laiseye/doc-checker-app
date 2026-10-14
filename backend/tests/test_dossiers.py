"""
Kiểm thử Toàn diện cho Bộ Hồ sơ (/api/v1/dossiers)
-------------------------------------------------
- CRUD bộ hồ sơ: Tạo, đọc, cập nhật, phân trang.
- Xóa mềm dây chuyền (Cascading Soft Delete): Xóa dossier kéo theo xóa mềm các documents đang hoạt động với CÙNG deleted_at.
- Khôi phục dây chuyền (Cascading Restore): Restore dossier chỉ khôi phục các documents bị xóa cùng đợt.
- DossierDetailOut và GET /dossiers/{id}/documents KHÔNG trả documents đã xóa mềm trừ khi include_deleted=True.
"""

def test_dossiers_crud(client):
    """Kiểm tra CRUD cơ bản cho bộ hồ sơ"""
    # 1. Tạo mới
    res_create = client.post(
        "/api/v1/dossiers",
        json={
            "name": "Hồ sơ thực tập sinh Nhật Bản 2026",
            "status": "DRAFT",
            "description": "Giai đoạn chuẩn bị hồ sơ phái cử",
        },
    )
    assert res_create.status_code == 201
    dossier_id = res_create.json()["id"]

    # 2. Chi tiết
    res_get = client.get(f"/api/v1/dossiers/{dossier_id}")
    assert res_get.status_code == 200
    assert res_get.json()["name"] == "Hồ sơ thực tập sinh Nhật Bản 2026"
    assert res_get.json()["documents"] == []

    # 3. Cập nhật trạng thái sang PENDING
    res_update = client.patch(
        f"/api/v1/dossiers/{dossier_id}",
        json={"status": "PENDING", "description": "Đã hoàn tất nộp hồ sơ"},
    )
    assert res_update.status_code == 200
    assert res_update.json()["status"] == "PENDING"
    assert res_update.json()["description"] == "Đã hoàn tất nộp hồ sơ"


def test_dossier_detail_and_documents_filter_deleted(client):
    """
    Quy chuẩn: DossierDetailOut và GET /dossiers/{id}/documents
    chỉ trả documents is_deleted=False, trừ khi include_deleted=true.
    """
    # Tạo dossier
    res_d = client.post("/api/v1/dossiers", json={"name": "Hồ sơ kiểm tra lọc doc"})
    d_id = res_d.json()["id"]

    # Tạo 2 documents
    res_doc1 = client.post(
        "/api/v1/documents",
        json={"dossier_id": d_id, "document_type": "CONTRACT", "original_name": "doc1.pdf"},
    )
    doc1_id = res_doc1.json()["id"]

    res_doc2 = client.post(
        "/api/v1/documents",
        json={"dossier_id": d_id, "document_type": "LICENSE", "original_name": "doc2.pdf"},
    )
    doc2_id = res_doc2.json()["id"]

    # Xóa mềm doc1
    client.delete(f"/api/v1/documents/{doc1_id}")

    # 1. Kiểm tra GET /dossiers/{id} (DossierDetailOut) mặc định: chỉ có doc2
    res_detail = client.get(f"/api/v1/dossiers/{d_id}")
    assert res_detail.status_code == 200
    docs_in_detail = res_detail.json()["documents"]
    assert len(docs_in_detail) == 1
    assert docs_in_detail[0]["id"] == doc2_id

    # Với include_deleted=true: có cả doc1 và doc2
    res_detail_all = client.get(f"/api/v1/dossiers/{d_id}?include_deleted=true")
    assert len(res_detail_all.json()["documents"]) == 2

    # 2. Kiểm tra GET /dossiers/{id}/documents mặc định: chỉ có doc2
    res_sub_docs = client.get(f"/api/v1/dossiers/{d_id}/documents")
    assert len(res_sub_docs.json()) == 1
    assert res_sub_docs.json()[0]["id"] == doc2_id

    # Với include_deleted=true
    res_sub_docs_all = client.get(f"/api/v1/dossiers/{d_id}/documents?include_deleted=true")
    assert len(res_sub_docs_all.json()) == 2


def test_dossier_cascade_soft_delete_and_restore(client):
    """
    Kiểm tra xóa mềm dây chuyền & khôi phục dây chuyền:
    1. Doc1 bị xóa riêng trước.
    2. Xóa Dossier -> Doc2 và Doc3 bị xóa mềm cùng đợt (cùng deleted_at với Dossier).
    3. Doc1 giữ nguyên deleted_at cũ.
    4. Khôi phục Dossier -> Doc2 và Doc3 được khôi phục. Doc1 vẫn bị xóa.
    """
    # Tạo dossier
    res_d = client.post("/api/v1/dossiers", json={"name": "Hồ sơ cascade test"})
    d_id = res_d.json()["id"]

    # Tạo 3 documents
    doc1_id = client.post("/api/v1/documents", json={"dossier_id": d_id, "document_type": "CONTRACT", "original_name": "doc1.pdf"}).json()["id"]
    doc2_id = client.post("/api/v1/documents", json={"dossier_id": d_id, "document_type": "LICENSE", "original_name": "doc2.pdf"}).json()["id"]
    doc3_id = client.post("/api/v1/documents", json={"dossier_id": d_id, "document_type": "APPROVAL", "original_name": "doc3.pdf"}).json()["id"]

    # 1. Xóa riêng doc1 trước
    client.delete(f"/api/v1/documents/{doc1_id}")
    doc1_data = client.get(f"/api/v1/documents/{doc1_id}?include_deleted=true").json()
    deleted_at_doc1_old = doc1_data["deleted_at"]

    # 2. Xóa mềm dossier
    res_del_d = client.delete(f"/api/v1/dossiers/{d_id}")
    assert res_del_d.status_code == 200

    dossier_deleted = client.get(f"/api/v1/dossiers/{d_id}?include_deleted=true").json()
    dossier_deleted_at = dossier_deleted["deleted_at"]
    assert dossier_deleted["is_deleted"] is True
    assert dossier_deleted_at is not None

    # Kiểm tra doc2 và doc3 bị xóa cùng đợt với cùng deleted_at
    doc2_del = client.get(f"/api/v1/documents/{doc2_id}?include_deleted=true").json()
    doc3_del = client.get(f"/api/v1/documents/{doc3_id}?include_deleted=true").json()
    assert doc2_del["is_deleted"] is True
    assert doc3_del["is_deleted"] is True
    assert doc2_del["deleted_at"] == dossier_deleted_at
    assert doc3_del["deleted_at"] == dossier_deleted_at

    # Kiểm tra doc1 vẫn giữ deleted_at cũ
    doc1_after = client.get(f"/api/v1/documents/{doc1_id}?include_deleted=true").json()
    assert doc1_after["deleted_at"] == deleted_at_doc1_old

    # 3. Khôi phục Dossier
    res_restore_d = client.post(f"/api/v1/dossiers/{d_id}/restore")
    assert res_restore_d.status_code == 200
    dossier_restored = res_restore_d.json()
    assert dossier_restored["is_deleted"] is False
    assert dossier_restored["deleted_at"] is None

    # doc2 và doc3 được khôi phục về active
    doc2_restored = client.get(f"/api/v1/documents/{doc2_id}").json()
    doc3_restored = client.get(f"/api/v1/documents/{doc3_id}").json()
    assert doc2_restored["is_deleted"] is False
    assert doc3_restored["is_deleted"] is False

    # doc1 KHÔNG được khôi phục vì bị xóa riêng từ đợt trước
    res_doc1_check = client.get(f"/api/v1/documents/{doc1_id}")
    assert res_doc1_check.status_code == 404  # Vì mặc định không trả bản ghi đã xóa
    doc1_still_deleted = client.get(f"/api/v1/documents/{doc1_id}?include_deleted=true").json()
    assert doc1_still_deleted["is_deleted"] is True
