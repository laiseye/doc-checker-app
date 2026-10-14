/**
 * Module Thông báo Toast (Toast Notifications)
 * --------------------------------------------
 * Hiển thị thông báo phản hồi thao tác đẹp mắt, hỗ trợ 3 kiểu: success, error, info.
 */

export function showToast(message, type = "success") {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `flex items-center gap-3 px-4 py-3 rounded-xl shadow-lg border text-sm font-medium transition-all duration-300 transform translate-y-2 opacity-0 fade-in ${getToastStyles(type)}`;

    const icon = getToastIcon(type);
    toast.innerHTML = `
        <span class="flex-shrink-0">${icon}</span>
        <span class="flex-1">${escapeHtml(message)}</span>
        <button class="flex-shrink-0 text-slate-400 hover:text-slate-600 transition-colors" onclick="this.parentElement.remove()">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
        </button>
    `;

    container.appendChild(toast);

    // Kích hoạt animation xuất hiện
    requestAnimationFrame(() => {
        toast.classList.remove("translate-y-2", "opacity-0");
    });

    // Tự động biến mất sau 3.5 giây
    setTimeout(() => {
        toast.classList.add("opacity-0", "translate-y-2");
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

function getToastStyles(type) {
    switch (type) {
        case "success":
            return "bg-emerald-50 text-emerald-900 border-emerald-200/80";
        case "error":
            return "bg-rose-50 text-rose-900 border-rose-200/80";
        case "info":
        default:
            return "bg-slate-50 text-slate-900 border-slate-200";
    }
}

function getToastIcon(type) {
    switch (type) {
        case "success":
            return `<svg class="w-5 h-5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>`;
        case "error":
            return `<svg class="w-5 h-5 text-rose-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>`;
        case "info":
        default:
            return `<svg class="w-5 h-5 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>`;
    }
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}
