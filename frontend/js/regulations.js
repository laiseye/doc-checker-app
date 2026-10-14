/**
 * Module Quản lý Văn bản quy định (Regulations UI Controller)
 * -----------------------------------------------------------
 * Điều khiển danh sách, tìm kiếm, phân trang, thêm mới, sửa, xóa mềm và khôi phục.
 */

import { api } from "./api.js";
import { showToast } from "./toast.js";

export function initRegulations() {
    let state = {
        page: 1,
        page_size: 10,
        q: "",
        status: "",
        include_deleted: false,
        editingId: null,
    };

    const tbody = document.getElementById("regulations-tbody");
    const emptyState = document.getElementById("regulations-empty");
    const searchInput = document.getElementById("reg-search");
    const statusSelect = document.getElementById("reg-status-filter");
    const deletedToggle = document.getElementById("reg-include-deleted");
    const btnAdd = document.getElementById("btn-add-regulation");

    const modal = document.getElementById("modal-regulation");
    const modalTitle = document.getElementById("modal-regulation-title");
    const form = document.getElementById("form-regulation");
    const btnCancel = document.getElementById("btn-cancel-regulation");
    const formError = document.getElementById("form-reg-error");

    const prevBtn = document.getElementById("reg-prev-page");
    const nextBtn = document.getElementById("reg-next-page");
    const pageInfo = document.getElementById("reg-page-info");

    // =========================================================================
    // 1. TẢI DỮ LIỆU TỪ API VÀ RENDER BẢNG
    // =========================================================================
    async function loadRegulations() {
        try {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center py-10 text-slate-400"><div class="inline-block animate-spin rounded-full h-6 w-6 border-2 border-slate-300 border-t-indigo-600 mr-2"></div>Đang tải dữ liệu...</td></tr>`;
            emptyState.classList.add("hidden");

            const res = await api.get("/regulations", {
                page: state.page,
                page_size: state.page_size,
                q: state.q,
                status: state.status,
                include_deleted: state.include_deleted,
            });

            renderTable(res.items);
            renderPagination(res.total, res.page, res.page_size);
        } catch (err) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center py-8 text-rose-500 font-medium">${err.message}</td></tr>`;
            showToast(err.message, "error");
        }
    }

    function renderTable(items) {
        if (!items || items.length === 0) {
            tbody.innerHTML = "";
            emptyState.classList.remove("hidden");
            return;
        }

        emptyState.classList.add("hidden");
        tbody.innerHTML = items.map(item => {
            const isDel = item.is_deleted;
            const rowClass = isDel ? "bg-slate-50/60 opacity-75" : "hover:bg-slate-50/80 transition-colors";
            const statusBadge = getStatusBadge(item.status, isDel);
            const dateRange = formatDateRange(item.effective_from, item.effective_to);

            return `
                <tr class="border-b border-slate-100 ${rowClass}">
                    <td class="py-3.5 px-4">
                        <div class="font-mono text-xs font-semibold px-2 py-1 bg-slate-100 text-slate-800 rounded inline-block">
                            ${escapeHtml(item.identifier)}
                        </div>
                    </td>
                    <td class="py-3.5 px-4 max-w-xs">
                        <div class="font-medium text-slate-900 truncate" title="${escapeHtml(item.title)}">
                            ${escapeHtml(item.title)}
                        </div>
                        ${item.source_url ? `<a href="${item.source_url}" target="_blank" class="text-xs text-indigo-600 hover:underline inline-flex items-center gap-1 mt-0.5">Tra cứu nguồn văn bản ↗</a>` : ''}
                    </td>
                    <td class="py-3.5 px-4 text-xs font-medium text-slate-600">${escapeHtml(item.version)}</td>
                    <td class="py-3.5 px-4 text-xs text-slate-600">${escapeHtml(item.issuing_body)}</td>
                    <td class="py-3.5 px-4 text-xs text-slate-600">${dateRange}</td>
                    <td class="py-3.5 px-4">${statusBadge}</td>
                    <td class="py-3.5 px-4 text-right">
                        ${isDel ? `
                            <button class="btn-restore-reg px-2.5 py-1 text-xs font-medium text-emerald-700 bg-emerald-50 hover:bg-emerald-100 rounded-lg transition-colors" data-id="${item.id}" data-name="${escapeHtml(item.identifier)}">
                                Khôi phục
                            </button>
                        ` : `
                            <div class="inline-flex items-center gap-1.5">
                                <button class="btn-edit-reg p-1.5 text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors" data-id="${item.id}" title="Chỉnh sửa">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"></path></svg>
                                </button>
                                <button class="btn-delete-reg p-1.5 text-slate-500 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors" data-id="${item.id}" data-name="${escapeHtml(item.identifier)}" title="Xóa mềm">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                                </button>
                            </div>
                        `}
                    </td>
                </tr>
            `;
        }).join("");

        attachActionListeners();
    }

    function renderPagination(total, page, pageSize) {
        const totalPages = Math.ceil(total / pageSize) || 1;
        pageInfo.textContent = `Trang ${page} / ${totalPages} (Tổng ${total} văn bản)`;
        prevBtn.disabled = page <= 1;
        nextBtn.disabled = page >= totalPages;
    }

    function getStatusBadge(status, isDeleted) {
        if (isDeleted) {
            return `<span class="px-2 py-0.5 text-xs font-semibold rounded-full bg-slate-200 text-slate-700">Đã xóa mềm</span>`;
        }
        switch (status) {
            case "ACTIVE":
                return `<span class="px-2 py-0.5 text-xs font-semibold rounded-full bg-emerald-100 text-emerald-800">Có hiệu lực</span>`;
            case "EXPIRED":
                return `<span class="px-2 py-0.5 text-xs font-semibold rounded-full bg-rose-100 text-rose-800">Hết hiệu lực</span>`;
            case "DRAFT":
            default:
                return `<span class="px-2 py-0.5 text-xs font-semibold rounded-full bg-amber-100 text-amber-800">Dự thảo</span>`;
        }
    }

    function formatDateRange(from, to) {
        const f = from ? from : "?";
        const t = to ? to : "Hiện tại";
        return `${f} → ${t}`;
    }

    // =========================================================================
    // 2. GẮN SỰ KIỆN NÚT HÀNH ĐỘNG TRONG BẢNG
    // =========================================================================
    function attachActionListeners() {
        // Sửa
        document.querySelectorAll(".btn-edit-reg").forEach(btn => {
            btn.onclick = () => openEditModal(btn.dataset.id);
        });

        // Xóa
        document.querySelectorAll(".btn-delete-reg").forEach(btn => {
            btn.onclick = () => confirmDelete(btn.dataset.id, btn.dataset.name);
        });

        // Khôi phục
        document.querySelectorAll(".btn-restore-reg").forEach(btn => {
            btn.onclick = () => handleRestore(btn.dataset.id, btn.dataset.name);
        });
    }

    // =========================================================================
    // 3. XỬ LÝ MODAL FORM THÊM / SỬA
    // =========================================================================
    function openAddModal() {
        state.editingId = null;
        modalTitle.textContent = "Thêm văn bản quy định mới";
        form.reset();
        document.getElementById("reg-id-field").value = "";
        document.getElementById("reg-version").value = "1.0";
        document.getElementById("reg-status").value = "ACTIVE";
        formError.classList.add("hidden");
        formError.textContent = "";
        modal.classList.remove("hidden");
    }

    async function openEditModal(id) {
        try {
            formError.classList.add("hidden");
            formError.textContent = "";
            const reg = await api.get(`/regulations/${id}`);
            state.editingId = id;
            modalTitle.textContent = `Chỉnh sửa văn bản: ${reg.identifier}`;

            document.getElementById("reg-id-field").value = reg.id;
            document.getElementById("reg-title").value = reg.title || "";
            document.getElementById("reg-identifier").value = reg.identifier || "";
            document.getElementById("reg-version").value = reg.version || "1.0";
            document.getElementById("reg-issuing-body").value = reg.issuing_body || "";
            document.getElementById("reg-effective-from").value = reg.effective_from || "";
            document.getElementById("reg-effective-to").value = reg.effective_to || "";
            document.getElementById("reg-status").value = reg.status || "ACTIVE";
            document.getElementById("reg-source-url").value = reg.source_url || "";

            modal.classList.remove("hidden");
        } catch (err) {
            showToast(err.message, "error");
        }
    }

    function closeModal() {
        modal.classList.add("hidden");
        form.reset();
        state.editingId = null;
    }

    form.onsubmit = async (e) => {
        e.preventDefault();
        formError.classList.add("hidden");

        const payload = {
            title: document.getElementById("reg-title").value.trim(),
            identifier: document.getElementById("reg-identifier").value.trim(),
            version: document.getElementById("reg-version").value.trim() || "1.0",
            issuing_body: document.getElementById("reg-issuing-body").value.trim(),
            effective_from: document.getElementById("reg-effective-from").value,
            effective_to: document.getElementById("reg-effective-to").value || null,
            status: document.getElementById("reg-status").value,
            source_url: document.getElementById("reg-source-url").value.trim() || null,
        };

        // Client validation
        if (payload.effective_to && payload.effective_from && payload.effective_to < payload.effective_from) {
            formError.textContent = "Ngày hết hiệu lực không được trước ngày bắt đầu có hiệu lực.";
            formError.classList.remove("hidden");
            return;
        }

        try {
            if (state.editingId) {
                await api.patch(`/regulations/${state.editingId}`, payload);
                showToast(`Đã cập nhật văn bản ${payload.identifier} thành công!`, "success");
            } else {
                await api.post("/regulations", payload);
                showToast(`Đã thêm mới văn bản ${payload.identifier} thành công!`, "success");
            }
            closeModal();
            loadRegulations();
        } catch (err) {
            formError.textContent = err.message;
            formError.classList.remove("hidden");
            showToast(err.message, "error");
        }
    };

    btnCancel.onclick = closeModal;

    // =========================================================================
    // 4. XÓA MỀM & KHÔI PHỤC
    // =========================================================================
    function confirmDelete(id, name) {
        if (confirm(`Bạn có chắc chắn muốn xóa mềm văn bản quy định "${name}"?\nVăn bản sẽ được chuyển sang trạng thái đã xóa và có thể khôi phục lại sau.`)) {
            handleDelete(id, name);
        }
    }

    async function handleDelete(id, name) {
        try {
            await api.delete(`/regulations/${id}`);
            showToast(`Đã xóa mềm văn bản "${name}" thành công!`, "success");
            loadRegulations();
        } catch (err) {
            showToast(err.message, "error");
        }
    }

    async function handleRestore(id, name) {
        try {
            await api.post(`/regulations/${id}/restore`);
            showToast(`Đã khôi phục văn bản "${name}" thành công!`, "success");
            loadRegulations();
        } catch (err) {
            showToast(err.message, "error");
        }
    }

    // =========================================================================
    // 5. SỰ KIỆN LỌC, TÌM KIẾM, PHÂN TRANG
    // =========================================================================
    let searchTimeout = null;
    searchInput.oninput = (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            state.q = e.target.value.trim();
            state.page = 1;
            loadRegulations();
        }, 300);
    };

    statusSelect.onchange = (e) => {
        state.status = e.target.value;
        state.page = 1;
        loadRegulations();
    };

    deletedToggle.onchange = (e) => {
        state.include_deleted = e.target.checked;
        state.page = 1;
        loadRegulations();
    };

    btnAdd.onclick = openAddModal;

    prevBtn.onclick = () => {
        if (state.page > 1) {
            state.page -= 1;
            loadRegulations();
        }
    };

    nextBtn.onclick = () => {
        state.page += 1;
        loadRegulations();
    };

    // Khởi tạo ban đầu
    loadRegulations();
}

function escapeHtml(text) {
    if (!text) return "";
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}
