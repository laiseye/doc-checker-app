/**
 * Module Quản lý Bộ hồ sơ & Tài liệu (Giai đoạn 2: Upload & Phân tích văn bản)
 * ----------------------------------------------------------------------------
 * Quản lý danh sách hồ sơ, chi tiết hồ sơ, Drag-and-Drop Upload tài liệu,
 * hiển thị trạng thái phân tích (done, needs_ocr, failed, no_file),
 * và mở Modal Document Viewer 2 cột (Cột 1: Preview gốc | Cột 2: Văn bản bóc tách theo trang).
 */

import { api } from "./api.js";
import { showToast } from "./toast.js";

export function initDossiers() {
    let state = {
        page: 1,
        page_size: 10,
        q: "",
        status: "",
        include_deleted: false,
        editingId: null,
        // Trạng thái màn hình chi tiết hồ sơ
        activeDossierId: null,
        docIncludeDeleted: false,
        editingDocId: null,
        // File đang chọn để upload
        selectedUploadFile: null,
        // Trạng thái Document Viewer modal
        viewerDoc: null,
        viewerPages: [],
        viewerCurrentPage: 1,
    };

    // DOM Elements - Danh sách hồ sơ
    const listView = document.getElementById("dossiers-list-view");
    const detailView = document.getElementById("dossier-detail-view");

    const tbody = document.getElementById("dossiers-tbody");
    const emptyState = document.getElementById("dossiers-empty");
    const searchInput = document.getElementById("dos-search");
    const statusSelect = document.getElementById("dos-status-filter");
    const deletedToggle = document.getElementById("dos-include-deleted");
    const btnAdd = document.getElementById("btn-add-dossier");

    const prevBtn = document.getElementById("dos-prev-page");
    const nextBtn = document.getElementById("dos-next-page");
    const pageInfo = document.getElementById("dos-page-info");

    // DOM Elements - Modal Hồ sơ
    const modalDossier = document.getElementById("modal-dossier");
    const modalDossierTitle = document.getElementById("modal-dossier-title");
    const formDossier = document.getElementById("form-dossier");
    const btnCancelDossier = document.getElementById("btn-cancel-dossier");
    const formDossierError = document.getElementById("form-dos-error");

    // DOM Elements - Chi tiết Hồ sơ & Tài liệu
    const btnBackToList = document.getElementById("btn-back-to-dossiers");
    const detailTitle = document.getElementById("detail-dos-title");
    const detailStatus = document.getElementById("detail-dos-status");
    const detailDesc = document.getElementById("detail-dos-desc");
    const docsTbody = document.getElementById("docs-tbody");
    const docsEmpty = document.getElementById("docs-empty");
    const docDeletedToggle = document.getElementById("doc-include-deleted");
    const btnAddDoc = document.getElementById("btn-add-doc");

    // DOM Elements - Upload Zone
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");
    const uploadDocType = document.getElementById("upload-doc-type");
    const selectedFileInfo = document.getElementById("selected-file-info");
    const selectedFileName = document.getElementById("selected-file-name");
    const selectedFileSize = document.getElementById("selected-file-size");
    const btnClearFile = document.getElementById("btn-clear-file");
    const btnUploadFile = document.getElementById("btn-upload-file");
    const uploadProgressContainer = document.getElementById("upload-progress-container");
    const uploadStatusText = document.getElementById("upload-status-text");

    // DOM Elements - Modal Document Metadata
    const modalDoc = document.getElementById("modal-document");
    const modalDocTitle = document.getElementById("modal-doc-title");
    const formDoc = document.getElementById("form-document");
    const btnCancelDoc = document.getElementById("btn-cancel-doc");
    const formDocError = document.getElementById("form-doc-error");

    // DOM Elements - Modal Viewer 2 Cột
    const modalViewer = document.getElementById("modal-viewer");
    const viewerDocName = document.getElementById("viewer-doc-name");
    const viewerStatusBadge = document.getElementById("viewer-status-badge");
    const viewerDocMeta = document.getElementById("viewer-doc-meta");
    const viewerBtnReparse = document.getElementById("viewer-btn-reparse");
    const viewerBtnDownload = document.getElementById("viewer-btn-download");
    const viewerBtnClose = document.getElementById("viewer-btn-close");
    const viewerPreviewType = document.getElementById("viewer-preview-type");
    const viewerPreviewBody = document.getElementById("viewer-preview-body");
    const viewerParserBadge = document.getElementById("viewer-parser-badge");
    const viewerPageControls = document.getElementById("viewer-page-controls");
    const viewerPageSelect = document.getElementById("viewer-page-select");
    const viewerBtnCopy = document.getElementById("viewer-btn-copy");
    const viewerPageNotice = document.getElementById("viewer-page-notice");
    const viewerPageNoticeText = document.getElementById("viewer-page-notice-text");
    const viewerRawText = document.getElementById("viewer-raw-text");
    const viewerNoTextNotice = document.getElementById("viewer-no-text-notice");
    const viewerNoTextDesc = document.getElementById("viewer-no-text-desc");

    // =========================================================================
    // 1. TẢI DANH SÁCH BỘ HỒ SƠ
    // =========================================================================
    async function loadDossiers() {
        try {
            tbody.innerHTML = `<tr><td colspan="5" class="text-center py-10 text-slate-400"><div class="inline-block animate-spin rounded-full h-6 w-6 border-2 border-slate-300 border-t-indigo-600 mr-2"></div>Đang tải dữ liệu hồ sơ...</td></tr>`;
            emptyState.classList.add("hidden");

            const res = await api.get("/dossiers", {
                page: state.page,
                page_size: state.page_size,
                q: state.q,
                status: state.status,
                include_deleted: state.include_deleted,
            });

            renderDossiersTable(res.items);
            renderDossiersPagination(res.total, res.page, res.page_size);
        } catch (err) {
            tbody.innerHTML = `<tr><td colspan="5" class="text-center py-8 text-rose-500 font-medium">${err.message}</td></tr>`;
            showToast(err.message, "error");
        }
    }

    function renderDossiersTable(items) {
        if (!items || items.length === 0) {
            tbody.innerHTML = "";
            emptyState.classList.remove("hidden");
            return;
        }

        emptyState.classList.add("hidden");
        tbody.innerHTML = items.map(item => {
            const isDel = item.is_deleted;
            const rowClass = isDel ? "bg-slate-50/60 opacity-75" : "hover:bg-slate-50/80 transition-colors";
            const statusBadge = getDossierStatusBadge(item.status, isDel);
            const docCountBadge = `<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700">${item.document_count || 0} tài liệu</span>`;

            return `
                <tr class="border-b border-slate-100 ${rowClass}">
                    <td class="py-3.5 px-4 max-w-sm">
                        <div class="font-medium text-slate-900 truncate" title="${escapeHtml(item.name)}">
                            ${escapeHtml(item.name)}
                        </div>
                        ${item.description ? `<p class="text-xs text-slate-500 truncate mt-0.5">${escapeHtml(item.description)}</p>` : ''}
                    </td>
                    <td class="py-3.5 px-4">${docCountBadge}</td>
                    <td class="py-3.5 px-4">${statusBadge}</td>
                    <td class="py-3.5 px-4 text-xs text-slate-500">${formatDate(item.created_at)}</td>
                    <td class="py-3.5 px-4 text-right">
                        ${isDel ? `
                            <button class="btn-restore-dos px-2.5 py-1 text-xs font-medium text-emerald-700 bg-emerald-50 hover:bg-emerald-100 rounded-lg transition-colors" data-id="${item.id}" data-name="${escapeHtml(item.name)}">
                                Khôi phục
                            </button>
                        ` : `
                            <div class="inline-flex items-center gap-1.5">
                                <button class="btn-view-dos px-2.5 py-1 text-xs font-medium text-indigo-700 bg-indigo-50 hover:bg-indigo-100 rounded-lg transition-colors" data-id="${item.id}" title="Xem chi tiết hồ sơ & tài liệu">
                                    Chi tiết
                                </button>
                                <button class="btn-edit-dos p-1.5 text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors" data-id="${item.id}" title="Sửa thông tin hồ sơ">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"></path></svg>
                                </button>
                                <button class="btn-delete-dos p-1.5 text-slate-500 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors" data-id="${item.id}" data-name="${escapeHtml(item.name)}" title="Xóa mềm">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                                </button>
                            </div>
                        `}
                    </td>
                </tr>
            `;
        }).join("");

        attachDossierActionListeners();
    }

    function renderDossiersPagination(total, page, pageSize) {
        const totalPages = Math.ceil(total / pageSize) || 1;
        pageInfo.textContent = `Trang ${page} / ${totalPages} (Tổng ${total} bộ hồ sơ)`;
        prevBtn.disabled = page <= 1;
        nextBtn.disabled = page >= totalPages;
    }

    function getDossierStatusBadge(status, isDeleted) {
        if (isDeleted) {
            return `<span class="px-2 py-0.5 text-xs font-semibold rounded-full bg-slate-200 text-slate-700">Đã xóa mềm</span>`;
        }
        switch (status) {
            case "APPROVED":
                return `<span class="px-2 py-0.5 text-xs font-semibold rounded-full bg-emerald-100 text-emerald-800">Đạt yêu cầu</span>`;
            case "PENDING":
                return `<span class="px-2 py-0.5 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">Chờ thẩm định</span>`;
            case "REJECTED":
                return `<span class="px-2 py-0.5 text-xs font-semibold rounded-full bg-rose-100 text-rose-800">Không đạt</span>`;
            case "DRAFT":
            default:
                return `<span class="px-2 py-0.5 text-xs font-semibold rounded-full bg-slate-100 text-slate-700">Bản nháp</span>`;
        }
    }

    function attachDossierActionListeners() {
        document.querySelectorAll(".btn-view-dos").forEach(btn => {
            btn.onclick = () => openDossierDetail(btn.dataset.id);
        });

        document.querySelectorAll(".btn-edit-dos").forEach(btn => {
            btn.onclick = () => openEditDossierModal(btn.dataset.id);
        });

        document.querySelectorAll(".btn-delete-dos").forEach(btn => {
            btn.onclick = () => confirmDeleteDossier(btn.dataset.id, btn.dataset.name);
        });

        document.querySelectorAll(".btn-restore-dos").forEach(btn => {
            btn.onclick = () => handleRestoreDossier(btn.dataset.id);
        });
    }

    // =========================================================================
    // 2. MODAL THÊM / SỬA BỘ HỒ SƠ
    // =========================================================================
    function openAddDossierModal() {
        state.editingId = null;
        modalDossierTitle.textContent = "Tạo mới bộ hồ sơ";
        formDossier.reset();
        document.getElementById("dos-id-field").value = "";
        document.getElementById("dos-status").value = "DRAFT";
        formDossierError.classList.add("hidden");
        modalDossier.classList.remove("hidden");
    }

    async function openEditDossierModal(id) {
        try {
            formDossierError.classList.add("hidden");
            const dossier = await api.get(`/dossiers/${id}`);
            state.editingId = id;
            modalDossierTitle.textContent = `Chỉnh sửa hồ sơ: ${dossier.name}`;

            document.getElementById("dos-id-field").value = dossier.id;
            document.getElementById("dos-name").value = dossier.name;
            document.getElementById("dos-status").value = dossier.status;
            document.getElementById("dos-desc").value = dossier.description || "";

            modalDossier.classList.remove("hidden");
        } catch (err) {
            showToast(err.message, "error");
        }
    }

    function closeDossierModal() {
        modalDossier.classList.add("hidden");
        formDossier.reset();
        state.editingId = null;
    }

    formDossier.onsubmit = async (e) => {
        e.preventDefault();
        formDossierError.classList.add("hidden");

        const payload = {
            name: document.getElementById("dos-name").value.trim(),
            status: document.getElementById("dos-status").value,
            description: document.getElementById("dos-desc").value.trim() || null,
        };

        try {
            if (state.editingId) {
                await api.put(`/dossiers/${state.editingId}`, payload);
                showToast("Cập nhật bộ hồ sơ thành công!", "success");
            } else {
                await api.post("/dossiers", payload);
                showToast("Tạo mới bộ hồ sơ thành công!", "success");
            }
            closeDossierModal();
            loadDossiers();
        } catch (err) {
            formDossierError.textContent = err.message;
            formDossierError.classList.remove("hidden");
            showToast(err.message, "error");
        }
    };

    btnCancelDossier.onclick = closeDossierModal;

    function confirmDeleteDossier(id, name) {
        if (confirm(`Bạn có chắc chắn muốn xóa mềm bộ hồ sơ "${name}"?\n(Toàn bộ tài liệu con đang hoạt động sẽ bị xóa mềm cùng đợt)`)) {
            handleDeleteDossier(id);
        }
    }

    async function handleDeleteDossier(id) {
        try {
            const res = await api.delete(`/dossiers/${id}`);
            showToast(res.message || "Đã xóa mềm hồ sơ!", "success");
            loadDossiers();
        } catch (err) {
            showToast(err.message, "error");
        }
    }

    async function handleRestoreDossier(id) {
        try {
            await api.post(`/dossiers/${id}/restore`);
            showToast("Đã khôi phục bộ hồ sơ và các tài liệu bị xóa cùng đợt!", "success");
            loadDossiers();
        } catch (err) {
            showToast(err.message, "error");
        }
    }

    // =========================================================================
    // 3. CHI TIẾT BỘ HỒ SƠ & TÀI LIỆU
    // =========================================================================
    async function openDossierDetail(dossierId) {
        state.activeDossierId = dossierId;
        listView.classList.add("hidden");
        detailView.classList.remove("hidden");
        clearSelectedUploadFile();
        loadDossierDetailData();
    }

    function closeDossierDetail() {
        state.activeDossierId = null;
        detailView.classList.add("hidden");
        listView.classList.remove("hidden");
        loadDossiers();
    }

    async function loadDossierDetailData() {
        if (!state.activeDossierId) return;

        try {
            docsTbody.innerHTML = `<tr><td colspan="6" class="text-center py-8 text-slate-400"><div class="inline-block animate-spin rounded-full h-5 w-5 border-2 border-slate-300 border-t-indigo-600 mr-2"></div>Đang tải tài liệu...</td></tr>`;
            docsEmpty.classList.add("hidden");

            const dossier = await api.get(`/dossiers/${state.activeDossierId}?include_deleted=${state.docIncludeDeleted}`);

            detailTitle.textContent = dossier.name;
            detailStatus.innerHTML = getDossierStatusBadge(dossier.status, dossier.is_deleted);
            detailDesc.textContent = dossier.description || "Chưa có ghi chú mô tả cho bộ hồ sơ này.";

            renderDocsTable(dossier.documents);
        } catch (err) {
            showToast(err.message, "error");
            closeDossierDetail();
        }
    }

    function renderDocsTable(documents) {
        if (!documents || documents.length === 0) {
            docsTbody.innerHTML = "";
            docsEmpty.classList.remove("hidden");
            return;
        }

        docsEmpty.classList.add("hidden");
        docsTbody.innerHTML = documents.map(doc => {
            const isDel = doc.is_deleted;
            const rowClass = isDel ? "bg-slate-50/60 opacity-75" : "hover:bg-slate-50/80 transition-colors";
            const typeBadge = getDocTypeBadge(doc.document_type);
            const parseBadge = getParseStatusBadge(doc.parse_status, doc.parse_error);
            const sizeStr = formatBytes(doc.file_size);
            const pageStr = doc.page_count ? `${doc.page_count} trang` : "0 trang";
            const hasFile = Boolean(doc.storage_path);

            return `
                <tr class="border-b border-slate-100 ${rowClass}">
                    <td class="py-3 px-4 font-mono text-xs">
                        <div class="font-medium text-slate-900 truncate max-w-xs" title="${escapeHtml(doc.original_name)}">
                            ${escapeHtml(doc.original_name)}
                        </div>
                        <div class="text-[10px] text-slate-400 font-sans mt-0.5">
                            ${formatDate(doc.uploaded_at || doc.created_at)}
                        </div>
                    </td>
                    <td class="py-3 px-4">${typeBadge}</td>
                    <td class="py-3 px-4 text-xs font-mono text-slate-600">
                        <div>${sizeStr}</div>
                        <div class="text-[11px] text-slate-400 font-sans">${pageStr}</div>
                    </td>
                    <td class="py-3 px-4">${parseBadge}</td>
                    <td class="py-3 px-4">
                        ${isDel ? `<span class="px-2 py-0.5 text-xs font-semibold rounded-full bg-slate-200 text-slate-700">Đã xóa</span>` : `<span class="px-2 py-0.5 text-xs font-semibold rounded-full bg-emerald-100 text-emerald-800">Hoạt động</span>`}
                    </td>
                    <td class="py-3 px-4 text-right">
                        ${isDel ? `
                            <button class="btn-restore-doc px-2.5 py-1 text-xs font-medium text-emerald-700 bg-emerald-50 hover:bg-emerald-100 rounded-lg transition-colors" data-id="${doc.id}">
                                Khôi phục
                            </button>
                        ` : `
                            <div class="inline-flex items-center gap-1">
                                ${hasFile ? `
                                    <button class="btn-view-doc-content px-2 py-1 text-xs font-medium text-indigo-700 bg-indigo-50 hover:bg-indigo-100 rounded-lg transition-colors flex items-center gap-1" data-id="${doc.id}" title="Xem văn bản & bản gốc">
                                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path></svg>
                                        <span>Xem</span>
                                    </button>
                                    <button class="btn-reparse-doc p-1 text-slate-500 hover:text-amber-600 hover:bg-amber-50 rounded transition-colors" data-id="${doc.id}" title="Phân tích lại văn bản">
                                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
                                    </button>
                                ` : ''}
                                <button class="btn-edit-doc p-1 text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 rounded transition-colors" data-id="${doc.id}" title="Sửa metadata">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"></path></svg>
                                </button>
                                <button class="btn-delete-doc p-1 text-slate-500 hover:text-rose-600 hover:bg-rose-50 rounded transition-colors" data-id="${doc.id}" data-name="${escapeHtml(doc.original_name)}" title="Xóa mềm">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                                </button>
                            </div>
                        `}
                    </td>
                </tr>
            `;
        }).join("");

        attachDocActionListeners();
    }

    function getDocTypeBadge(type) {
        switch (type) {
            case "CONTRACT":
                return `<span class="px-2 py-0.5 text-xs font-semibold rounded bg-blue-100 text-blue-800">Hợp đồng</span>`;
            case "LICENSE":
                return `<span class="px-2 py-0.5 text-xs font-semibold rounded bg-purple-100 text-purple-800">Giấy phép</span>`;
            case "APPROVAL":
                return `<span class="px-2 py-0.5 text-xs font-semibold rounded bg-teal-100 text-teal-800">Văn bản chấp thuận</span>`;
            case "WORKER_LIST":
                return `<span class="px-2 py-0.5 text-xs font-semibold rounded bg-orange-100 text-orange-800">Danh sách lao động</span>`;
            case "OTHER":
            default:
                return `<span class="px-2 py-0.5 text-xs font-semibold rounded bg-slate-100 text-slate-700">Khác</span>`;
        }
    }

    function getParseStatusBadge(status, errorMsg) {
        const titleAttr = errorMsg ? `title="${escapeHtml(errorMsg)}"` : '';
        switch (status) {
            case "done":
                return `<span class="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-semibold rounded-full bg-emerald-100 text-emerald-800"><span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>Đã bóc tách</span>`;
            case "needs_ocr":
                return `<span ${titleAttr} class="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-semibold rounded-full bg-amber-100 text-amber-800 cursor-help"><span class="w-1.5 h-1.5 rounded-full bg-amber-500"></span>Cần OCR</span>`;
            case "failed":
                return `<span ${titleAttr} class="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-semibold rounded-full bg-rose-100 text-rose-800 cursor-help"><span class="w-1.5 h-1.5 rounded-full bg-rose-500"></span>Lỗi bóc tách</span>`;
            case "processing":
                return `<span class="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-semibold rounded-full bg-blue-100 text-blue-800"><span class="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse"></span>Đang xử lý</span>`;
            case "pending":
                return `<span class="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-semibold rounded-full bg-slate-100 text-slate-700">Chờ xử lý</span>`;
            case "no_file":
            default:
                return `<span class="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-semibold rounded-full bg-slate-100 text-slate-600">Chưa có file</span>`;
        }
    }

    function attachDocActionListeners() {
        document.querySelectorAll(".btn-view-doc-content").forEach(btn => {
            btn.onclick = () => openDocumentViewer(btn.dataset.id);
        });

        document.querySelectorAll(".btn-reparse-doc").forEach(btn => {
            btn.onclick = () => handleReparseDoc(btn.dataset.id);
        });

        document.querySelectorAll(".btn-edit-doc").forEach(btn => {
            btn.onclick = () => openEditDocModal(btn.dataset.id);
        });

        document.querySelectorAll(".btn-delete-doc").forEach(btn => {
            btn.onclick = () => confirmDeleteDoc(btn.dataset.id, btn.dataset.name);
        });

        document.querySelectorAll(".btn-restore-doc").forEach(btn => {
            btn.onclick = () => handleRestoreDoc(btn.dataset.id);
        });
    }

    // =========================================================================
    // 4. DRAG-AND-DROP UPLOAD TÀI LIỆU
    // =========================================================================
    const ALLOWED_EXTS = [".pdf", ".docx", ".jpg", ".jpeg", ".png"];
    const MAX_UPLOAD_BYTES = 20 * 1024 * 1024; // 20 MB

    dropZone.onclick = (e) => {
        if (e.target !== btnClearFile && !btnClearFile.contains(e.target)) {
            fileInput.click();
        }
    };

    dropZone.ondragover = (e) => {
        e.preventDefault();
        dropZone.classList.add("border-indigo-500", "bg-indigo-50/40");
    };

    dropZone.ondragleave = (e) => {
        e.preventDefault();
        dropZone.classList.remove("border-indigo-500", "bg-indigo-50/40");
    };

    dropZone.ondrop = (e) => {
        e.preventDefault();
        dropZone.classList.remove("border-indigo-500", "bg-indigo-50/40");
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            handleFileSelect(e.dataTransfer.files[0]);
        }
    };

    fileInput.onchange = (e) => {
        if (e.target.files && e.target.files.length > 0) {
            handleFileSelect(e.target.files[0]);
        }
    };

    function handleFileSelect(file) {
        if (!file) return;

        // Kiểm tra phần mở rộng
        const name = file.name.toLowerCase();
        const isValidExt = ALLOWED_EXTS.some(ext => name.endsWith(ext));
        if (!isValidExt) {
            showToast("Định dạng file không được hỗ trợ. Vui lòng chọn file PDF, DOCX, JPG hoặc PNG!", "error");
            return;
        }

        // Kiểm tra dung lượng
        if (file.size > MAX_UPLOAD_BYTES) {
            showToast(`File vượt quá dung lượng tối đa cho phép (20MB). File của bạn: ${formatBytes(file.size)}`, "error");
            return;
        }

        state.selectedUploadFile = file;
        selectedFileName.textContent = file.name;
        selectedFileSize.textContent = `(${formatBytes(file.size)})`;
        selectedFileInfo.classList.remove("hidden");
        btnUploadFile.disabled = false;
    }

    function clearSelectedUploadFile() {
        state.selectedUploadFile = null;
        fileInput.value = "";
        selectedFileInfo.classList.add("hidden");
        btnUploadFile.disabled = true;
        uploadProgressContainer.classList.add("hidden");
    }

    btnClearFile.onclick = (e) => {
        e.stopPropagation();
        clearSelectedUploadFile();
    };

    btnUploadFile.onclick = async () => {
        if (!state.selectedUploadFile || !state.activeDossierId) return;

        try {
            btnUploadFile.disabled = true;
            uploadProgressContainer.classList.remove("hidden");
            uploadStatusText.textContent = `Đang tải lên "${state.selectedUploadFile.name}" và phân tích văn bản...`;

            const formData = new FormData();
            formData.append("file", state.selectedUploadFile);
            formData.append("document_type", uploadDocType.value);

            const newDoc = await api.upload(`/dossiers/${state.activeDossierId}/documents`, formData);

            showToast(`Đã tải lên và xử lý "${newDoc.original_name}" thành công!`, "success");
            clearSelectedUploadFile();
            loadDossierDetailData();

            // Tự động mở viewer để người dùng xem kết quả ngay
            openDocumentViewer(newDoc.id);

        } catch (err) {
            uploadProgressContainer.classList.add("hidden");
            btnUploadFile.disabled = false;
            showToast(err.message, "error");
        }
    };

    // =========================================================================
    // 5. DOCUMENT VIEWER MODAL 2 CỘT (PREVIEW & TRÍCH XUẤT VĂN BẢN)
    // =========================================================================
    async function openDocumentViewer(docId) {
        try {
            modalViewer.classList.remove("hidden");
            viewerRawText.textContent = "Đang tải dữ liệu văn bản bóc tách...";
            viewerPageNotice.classList.add("hidden");
            viewerNoTextNotice.classList.add("hidden");
            viewerPreviewBody.innerHTML = `<div class="text-slate-400 text-xs flex items-center gap-2"><div class="animate-spin rounded-full h-4 w-4 border-2 border-slate-300 border-t-indigo-600"></div>Đang nạp file gốc...</div>`;

            // Lấy chi tiết Document và danh sách các Pages
            const [doc, pages] = await Promise.all([
                api.get(`/documents/${docId}`),
                api.get(`/documents/${docId}/pages`),
            ]);

            state.viewerDoc = doc;
            state.viewerPages = pages || [];
            state.viewerCurrentPage = 1;

            // Render Header
            viewerDocName.textContent = doc.original_name;
            viewerStatusBadge.innerHTML = getParseStatusBadge(doc.parse_status, doc.parse_error);
            const shaBrief = doc.sha256 ? `${doc.sha256.substring(0, 16)}...` : "N/A";
            viewerDocMeta.textContent = `Loại: ${doc.document_type} | Kích thước: ${formatBytes(doc.file_size)} | SHA-256: ${shaBrief}`;

            // Nút tải file gốc
            viewerBtnDownload.href = `/api/v1/documents/${doc.id}/file`;
            viewerBtnDownload.setAttribute("download", doc.original_name);

            // Nút phân tích lại
            viewerBtnReparse.onclick = () => handleReparseDoc(doc.id, true);

            // Render Cột 1: Preview file gốc
            renderViewerPreview(doc);

            // Render Cột 2: Danh sách trang và text
            renderViewerPages(pages, doc);

        } catch (err) {
            modalViewer.classList.add("hidden");
            showToast(err.message, "error");
        }
    }

    function renderViewerPreview(doc) {
        const fileUrl = `/api/v1/documents/${doc.id}/file`;
        const mime = doc.mime_type || "";

        if (mime === "application/pdf") {
            viewerPreviewType.textContent = "Định dạng PDF (PyMuPDF)";
            viewerPreviewBody.innerHTML = `
                <iframe src="${fileUrl}" class="w-full h-full border-0 rounded-xl bg-white shadow-sm" title="PDF Preview"></iframe>
            `;
        } else if (mime.startsWith("image/")) {
            viewerPreviewType.textContent = "Hình ảnh scan (Chờ OCR GĐ3)";
            viewerPreviewBody.innerHTML = `
                <div class="w-full h-full flex items-center justify-center p-4">
                    <img src="${fileUrl}" alt="${escapeHtml(doc.original_name)}" class="max-w-full max-h-full object-contain rounded-xl shadow-md border border-slate-200">
                </div>
            `;
        } else if (mime.includes("wordprocessingml") || mime.includes("docx")) {
            viewerPreviewType.textContent = "Văn bản Word (.docx)";
            viewerPreviewBody.innerHTML = `
                <div class="text-center p-8 bg-white rounded-2xl border border-slate-200 shadow-sm max-w-md mx-auto flex flex-col items-center gap-3">
                    <div class="w-14 h-14 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center shadow-sm">
                        <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                    </div>
                    <h4 class="font-bold text-slate-800 text-sm">Tài liệu Microsoft Word (.docx)</h4>
                    <p class="text-xs text-slate-500 leading-relaxed">
                        Trình duyệt không hỗ trợ hiển thị trực tiếp DOCX nhúng trong trang.
                        Bạn có thể tải tệp gốc về máy hoặc xem toàn bộ nội dung văn bản & bảng biểu đã trích xuất ở cột bên phải.
                    </p>
                    <a href="${fileUrl}" target="_blank" download="${escapeHtml(doc.original_name)}" class="mt-2 inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-xl shadow-sm transition-all">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                        <span>Tải tệp tin Word về máy</span>
                    </a>
                </div>
            `;
        } else {
            viewerPreviewType.textContent = "Tệp tin nhị phân";
            viewerPreviewBody.innerHTML = `
                <div class="text-center text-xs text-slate-500">
                    Không thể xem trước loại tệp tin này. <a href="${fileUrl}" class="text-indigo-600 underline">Tải về</a> để xem.
                </div>
            `;
        }
    }

    function renderViewerPages(pages, doc) {
        if (!pages || pages.length === 0) {
            viewerParserBadge.textContent = "Không có trang";
            viewerPageControls.classList.add("hidden");
            viewerRawText.classList.add("hidden");
            viewerNoTextNotice.classList.remove("hidden");
            viewerNoTextDesc.textContent = doc.parse_error || "Chưa có nội dung văn bản nào được trích xuất cho tài liệu này.";
            return;
        }

        viewerNoTextNotice.classList.add("hidden");
        viewerRawText.classList.remove("hidden");
        viewerPageControls.classList.remove("hidden");

        const firstPage = pages[0];
        const engineStr = firstPage.engine_version ? `(${firstPage.engine_version})` : "";
        viewerParserBadge.textContent = `${firstPage.parser_type} ${engineStr}`;

        // Populate dropdown chọn trang
        viewerPageSelect.innerHTML = pages.map(p => `
            <option value="${p.page_number}">Trang ${p.page_number} / ${pages.length}</option>
        `).join("");

        viewerPageSelect.onchange = (e) => {
            state.viewerCurrentPage = parseInt(e.target.value, 10);
            renderSelectedPage();
        };

        renderSelectedPage();
    }

    function renderSelectedPage() {
        const page = state.viewerPages.find(p => p.page_number === state.viewerCurrentPage);
        if (!page) {
            viewerRawText.textContent = "Không tìm thấy dữ liệu trang.";
            return;
        }

        // Kiểm tra nếu có edited_text
        if (page.edited_text) {
            viewerPageNotice.classList.remove("hidden");
            viewerPageNoticeText.textContent = "Trang này có bản sửa đổi thủ công (edited_text) được bảo lưu từ lần phân tích trước.";
            viewerRawText.textContent = page.edited_text;
        } else {
            viewerPageNotice.classList.add("hidden");
            viewerRawText.textContent = page.raw_text || "(Trang này không có ký tự văn bản nào)";
        }
    }

    viewerBtnCopy.onclick = () => {
        const text = viewerRawText.textContent;
        if (!text) return;
        navigator.clipboard.writeText(text).then(() => {
            showToast("Đã sao chép nội dung văn bản của trang vào clipboard!", "success");
        }).catch(() => {
            showToast("Không thể sao chép văn bản.", "error");
        });
    };

    function closeViewerModal() {
        modalViewer.classList.add("hidden");
        viewerPreviewBody.innerHTML = "";
        state.viewerDoc = null;
        state.viewerPages = [];
    }

    viewerBtnClose.onclick = closeViewerModal;

    // Phân tích lại tài liệu
    async function handleReparseDoc(docId, updateViewer = false) {
        try {
            showToast("Đang thực hiện phân tích lại văn bản từ file gốc...", "info");
            const updatedDoc = await api.post(`/documents/${docId}/parse`);
            showToast(`Đã phân tích lại xong "${updatedDoc.original_name}"! Trạng thái: ${updatedDoc.parse_status}`, "success");

            loadDossierDetailData();

            if (updateViewer && state.viewerDoc && state.viewerDoc.id === docId) {
                openDocumentViewer(docId);
            }
        } catch (err) {
            showToast(err.message, "error");
        }
    }

    // =========================================================================
    // 6. MODAL METADATA TÀI LIỆU (TƯƠNG THÍCH GIAI ĐOẠN 1)
    // =========================================================================
    function openAddDocModal() {
        state.editingDocId = null;
        modalDocTitle.textContent = "Khai báo tài liệu (Metadata không file)";
        formDoc.reset();
        document.getElementById("doc-id-field").value = "";
        document.getElementById("doc-type").value = "CONTRACT";
        formDocError.classList.add("hidden");
        modalDoc.classList.remove("hidden");
    }

    async function openEditDocModal(docId) {
        try {
            formDocError.classList.add("hidden");
            const doc = await api.get(`/documents/${docId}`);
            state.editingDocId = docId;
            modalDocTitle.textContent = `Sửa thông tin: ${doc.original_name}`;

            document.getElementById("doc-id-field").value = doc.id;
            document.getElementById("doc-name").value = doc.original_name || "";
            document.getElementById("doc-type").value = doc.document_type || "OTHER";

            modalDoc.classList.remove("hidden");
        } catch (err) {
            showToast(err.message, "error");
        }
    }

    function closeDocModal() {
        modalDoc.classList.add("hidden");
        formDoc.reset();
        state.editingDocId = null;
    }

    formDoc.onsubmit = async (e) => {
        e.preventDefault();
        formDocError.classList.add("hidden");

        const originalName = document.getElementById("doc-name").value.trim();
        const documentType = document.getElementById("doc-type").value;

        try {
            if (state.editingDocId) {
                await api.patch(`/documents/${state.editingDocId}`, {
                    original_name: originalName,
                    document_type: documentType,
                });
                showToast("Đã cập nhật siêu dữ liệu tài liệu!", "success");
            } else {
                await api.post("/documents", {
                    dossier_id: state.activeDossierId,
                    original_name: originalName,
                    document_type: documentType,
                });
                showToast("Đã thêm tài liệu thành công!", "success");
            }
            closeDocModal();
            loadDossierDetailData();
        } catch (err) {
            formDocError.textContent = err.message;
            formDocError.classList.remove("hidden");
            showToast(err.message, "error");
        }
    };

    btnCancelDoc.onclick = closeDocModal;

    function confirmDeleteDoc(id, name) {
        if (confirm(`Bạn có chắc muốn xóa mềm tài liệu "${name}"?\n(File vật lý trên máy chủ vẫn được lưu trữ nguyên vẹn)`)) {
            handleDeleteDoc(id);
        }
    }

    async function handleDeleteDoc(id) {
        try {
            await api.delete(`/documents/${id}`);
            showToast("Đã xóa mềm tài liệu thành công!", "success");
            loadDossierDetailData();
        } catch (err) {
            showToast(err.message, "error");
        }
    }

    async function handleRestoreDoc(id) {
        try {
            await api.post(`/documents/${id}/restore`);
            showToast("Đã khôi phục tài liệu!", "success");
            loadDossierDetailData();
        } catch (err) {
            showToast(err.message, "error");
        }
    }

    // =========================================================================
    // 7. GẮN SỰ KIỆN TÌM KIẾM, PHÂN TRANG HỒ SƠ
    // =========================================================================
    let searchTimeout = null;
    searchInput.oninput = (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            state.q = e.target.value.trim();
            state.page = 1;
            loadDossiers();
        }, 300);
    };

    statusSelect.onchange = (e) => {
        state.status = e.target.value;
        state.page = 1;
        loadDossiers();
    };

    deletedToggle.onchange = (e) => {
        state.include_deleted = e.target.checked;
        state.page = 1;
        loadDossiers();
    };

    btnAdd.onclick = openAddDossierModal;

    prevBtn.onclick = () => {
        if (state.page > 1) {
            state.page -= 1;
            loadDossiers();
        }
    };

    nextBtn.onclick = () => {
        state.page += 1;
        loadDossiers();
    };

    btnBackToList.onclick = closeDossierDetail;

    docDeletedToggle.onchange = (e) => {
        state.docIncludeDeleted = e.target.checked;
        loadDossierDetailData();
    };

    btnAddDoc.onclick = openAddDocModal;

    // Khởi tạo ban đầu
    loadDossiers();
}

function formatBytes(bytes) {
    if (!bytes && bytes !== 0) return "-";
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(2) + " MB";
}

function formatDate(isoString) {
    if (!isoString) return "-";
    try {
        const d = new Date(isoString);
        return d.toLocaleDateString("vi-VN", {
            year: "numeric",
            month: "2-digit",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
        });
    } catch {
        return isoString;
    }
}

function escapeHtml(text) {
    if (!text) return "";
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}
