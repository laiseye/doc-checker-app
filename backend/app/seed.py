"""
Script khởi tạo dữ liệu mẫu (Database Seeding)
---------------------------------------------
Tạo dữ liệu ban đầu gồm:
- 5 văn bản quy định thực tế (Luật 69/2020, Nghị định 112/2021, Thông tư 21/2021, Luật 72/2006, Dự thảo 2026).
- 3 bộ hồ sơ thẩm định tiêu biểu trong ngành cung ứng lao động.
- 6 siêu dữ liệu tài liệu gắn với các bộ hồ sơ.

Đặc tính Idempotent:
Chạy lại nhiều lần không gây lỗi và không làm nhân đôi dữ liệu.
Cách chạy từ thư mục gốc dự án:
    .\\.venv\\Scripts\\python -m app.seed
"""

import sys
from pathlib import Path
from datetime import date

# Đảm bảo in tiếng Việt trên console Windows không bị lỗi cp1252
try:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# Đảm bảo import được module 'app'
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select
from app.database import SessionLocal, get_utc_now
from app.models import (
    Regulation,
    RegulationStatus,
    Dossier,
    DossierStatus,
    Document,
    DocumentType,
)


def seed_database() -> None:
    """Nạp dữ liệu mẫu vào CSDL"""
    db = SessionLocal()
    print("=" * 60)
    print("BẮT ĐẦU NẠP DỮ LIỆU MẪU (SEEDING)...")
    print("=" * 60)

    try:
        # ----------------------------------------------------------------------
        # 1. Nạp 5 Văn bản quy định mẫu
        # ----------------------------------------------------------------------
        regulations_data = [
            {
                "title": "Luật Người lao động Việt Nam đi làm việc ở nước ngoài theo hợp đồng",
                "identifier": "69/2020/QH14",
                "version": "2020",
                "issuing_body": "Quốc hội",
                "effective_from": date(2022, 1, 1),
                "effective_to": None,
                "status": RegulationStatus.ACTIVE.value,
                "source_url": "https://vanban.chinhphu.vn/?pageid=27160&docid=202102",
            },
            {
                "title": "Nghị định quy định chi tiết một số điều của Luật Người lao động Việt Nam đi làm việc ở nước ngoài",
                "identifier": "112/2021/NĐ-CP",
                "version": "2021",
                "issuing_body": "Chính phủ",
                "effective_from": date(2022, 1, 1),
                "effective_to": None,
                "status": RegulationStatus.ACTIVE.value,
                "source_url": "https://vanban.chinhphu.vn/?pageid=27160&docid=204732",
            },
            {
                "title": "Thông tư quy định chi tiết một số điều của Luật Người lao động Việt Nam đi làm việc ở nước ngoài",
                "identifier": "21/2021/TT-BLĐTBXH",
                "version": "2021",
                "issuing_body": "Bộ Lao động - Thương binh và Xã hội",
                "effective_from": date(2022, 2, 1),
                "effective_to": None,
                "status": RegulationStatus.ACTIVE.value,
                "source_url": "https://molisa.gov.vn/Pages/vanban/chitiet.aspx?idx=39618",
            },
            {
                "title": "Luật Người lao động Việt Nam đi làm việc ở nước ngoài 2006 (Đã hết hiệu lực)",
                "identifier": "72/2006/QH11",
                "version": "2006",
                "issuing_body": "Quốc hội",
                "effective_from": date(2007, 7, 1),
                "effective_to": date(2021, 12, 31),
                "status": RegulationStatus.EXPIRED.value,
                "source_url": "https://vanban.chinhphu.vn/?pageid=27160&docid=30514",
            },
            {
                "title": "Dự thảo Quy chuẩn kỹ thuật thẩm định dữ liệu điện tử hồ sơ phái cử lao động",
                "identifier": "DT-01/2026/QĐ-CLLĐ",
                "version": "v1.0",
                "issuing_body": "Cục Quản lý lao động ngoài nước",
                "effective_from": date(2026, 12, 1),
                "effective_to": None,
                "status": RegulationStatus.DRAFT.value,
                "source_url": None,
            },
        ]

        reg_count = 0
        for item in regulations_data:
            stmt = select(Regulation).where(
                Regulation.identifier == item["identifier"],
                Regulation.version == item["version"],
            )
            existing = db.scalar(stmt)
            if not existing:
                reg = Regulation(
                    title=item["title"],
                    identifier=item["identifier"],
                    version=item["version"],
                    issuing_body=item["issuing_body"],
                    effective_from=item["effective_from"],
                    effective_to=item["effective_to"],
                    status=item["status"],
                    source_url=item["source_url"],
                    is_deleted=False,
                    deleted_at=None,
                )
                db.add(reg)
                reg_count += 1
        db.commit()
        print(f"[+] Văn bản quy định: Đã thêm mới {reg_count} bản ghi (bỏ qua bản ghi đã có).")

        # ----------------------------------------------------------------------
        # 2. Nạp 3 Bộ hồ sơ mẫu
        # ----------------------------------------------------------------------
        dossiers_data = [
            {
                "name": "Hồ sơ phái cử thực tập sinh ngành cơ khí sang Nhật Bản - Đợt 1/2026",
                "status": DossierStatus.PENDING.value,
                "description": "Bộ hồ sơ đăng ký hợp đồng cung ứng 50 thực tập sinh kỹ năng ngành gia công cơ khí sang nghiệp đoàn Tokyo (Nhật Bản).",
            },
            {
                "name": "Hồ sơ cung ứng lao động kỹ thuật xây dựng tại Hàn Quốc (Visa E-7)",
                "status": DossierStatus.APPROVED.value,
                "description": "Bộ hồ sơ hợp đồng cung ứng 30 kỹ sư và công nhân kỹ thuật lành nghề cho dự án công trình của đối tác tại Seoul (Hàn Quốc).",
            },
            {
                "name": "Hồ sơ đăng ký chương trình điều dưỡng viên tại CHLB Đức",
                "status": DossierStatus.DRAFT.value,
                "description": "Dự thảo đợt tuyển chọn và phái cử 25 ứng viên học nghề điều dưỡng theo khuôn khổ thỏa thuận song phương.",
            },
        ]

        dossier_map = {}
        dos_count = 0
        for item in dossiers_data:
            stmt = select(Dossier).where(Dossier.name == item["name"])
            existing = db.scalar(stmt)
            if not existing:
                dos = Dossier(
                    name=item["name"],
                    status=item["status"],
                    description=item["description"],
                    is_deleted=False,
                    deleted_at=None,
                )
                db.add(dos)
                db.commit()
                db.refresh(dos)
                dossier_map[dos.name] = dos.id
                dos_count += 1
            else:
                dossier_map[existing.name] = existing.id
        print(f"[+] Bộ hồ sơ: Đã thêm mới {dos_count} bộ hồ sơ (bỏ qua hồ sơ đã có).")

        # ----------------------------------------------------------------------
        # 3. Nạp 6 Siêu dữ liệu tài liệu mẫu (Documents)
        # ----------------------------------------------------------------------
        now = get_utc_now()
        documents_data = [
            # Tài liệu cho Hồ sơ 1 (Nhật Bản)
            {
                "dossier_name": "Hồ sơ phái cử thực tập sinh ngành cơ khí sang Nhật Bản - Đợt 1/2026",
                "document_type": DocumentType.CONTRACT.value,
                "original_name": "hop_dong_cung_ung_lao_dong_nhat_ban_so_01.pdf",
            },
            {
                "dossier_name": "Hồ sơ phái cử thực tập sinh ngành cơ khí sang Nhật Bản - Đợt 1/2026",
                "document_type": DocumentType.LICENSE.value,
                "original_name": "giay_phep_hoat_dong_dich_vu_doanh_nghiep_2025.pdf",
            },
            {
                "dossier_name": "Hồ sơ phái cử thực tập sinh ngành cơ khí sang Nhật Bản - Đợt 1/2026",
                "document_type": DocumentType.APPROVAL.value,
                "original_name": "van_ban_chap_thuan_dang_ky_hop_dong_cuc_qlldnn.pdf",
            },
            # Tài liệu cho Hồ sơ 2 (Hàn Quốc)
            {
                "dossier_name": "Hồ sơ cung ứng lao động kỹ thuật xây dựng tại Hàn Quốc (Visa E-7)",
                "document_type": DocumentType.CONTRACT.value,
                "original_name": "hop_dong_cung_ung_ky_su_han_quoc_e7_signed.pdf",
            },
            {
                "dossier_name": "Hồ sơ cung ứng lao động kỹ thuật xây dựng tại Hàn Quốc (Visa E-7)",
                "document_type": DocumentType.WORKER_LIST.value,
                "original_name": "danh_sach_30_lao_dong_chuyen_nganh_xay_dung.xlsx",
            },
            # Tài liệu cho Hồ sơ 3 (Đức)
            {
                "dossier_name": "Hồ sơ đăng ký chương trình điều dưỡng viên tại CHLB Đức",
                "document_type": DocumentType.CONTRACT.value,
                "original_name": "du_thao_thoa_thuan_hop_tac_dieu_duong_duc.docx",
            },
        ]

        doc_count = 0
        for item in documents_data:
            dossier_id = dossier_map.get(item["dossier_name"])
            if dossier_id:
                stmt = select(Document).where(
                    Document.dossier_id == dossier_id,
                    Document.original_name == item["original_name"],
                )
                existing = db.scalar(stmt)
                if not existing:
                    doc = Document(
                        dossier_id=dossier_id,
                        document_type=item["document_type"],
                        original_name=item["original_name"],
                        uploaded_at=now,
                        is_deleted=False,
                        deleted_at=None,
                    )
                    db.add(doc)
                    doc_count += 1
        db.commit()
        print(f"[+] Tài liệu trong hồ sơ: Đã thêm mới {doc_count} tài liệu.")

        print("=" * 60)
        print("HOÀN TẤT NẠP DỮ LIỆU MẪU THÀNH CÔNG!")
        print("=" * 60)

    except Exception as e:
        db.rollback()
        print(f"[-] Đã xảy ra lỗi khi nạp dữ liệu: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
