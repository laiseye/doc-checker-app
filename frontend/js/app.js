/**
 * Main Application Script (Frontend Entrypoint)
 * ---------------------------------------------
 * Điều khiển điều hướng chuyển đổi tab chính và khởi tạo các module.
 */

import { api } from "./api.js";
import { initRegulations } from "./regulations.js";
import { initDossiers } from "./dossiers.js";
import { showToast } from "./toast.js";

document.addEventListener("DOMContentLoaded", () => {
    // 1. Quản lý chuyển Tab chính
    const tabBtnReg = document.getElementById("tab-btn-regulations");
    const tabBtnDos = document.getElementById("tab-btn-dossiers");
    const sectionReg = document.getElementById("section-regulations");
    const sectionDos = document.getElementById("section-dossiers");

    function switchTab(target) {
        if (target === "regulations") {
            tabBtnReg.className = "flex items-center gap-2 px-4 py-2 text-sm font-semibold text-indigo-700 bg-white shadow-sm rounded-xl transition-all";
            tabBtnDos.className = "flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-500 hover:text-slate-800 rounded-xl transition-all";
            sectionReg.classList.remove("hidden");
            sectionDos.classList.add("hidden");
        } else {
            tabBtnDos.className = "flex items-center gap-2 px-4 py-2 text-sm font-semibold text-indigo-700 bg-white shadow-sm rounded-xl transition-all";
            tabBtnReg.className = "flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-500 hover:text-slate-800 rounded-xl transition-all";
            sectionDos.classList.remove("hidden");
            sectionReg.classList.add("hidden");
        }
    }

    tabBtnReg.onclick = () => switchTab("regulations");
    tabBtnDos.onclick = () => switchTab("dossiers");

    // 2. Kiểm tra kết nối API Health
    async function checkHealth() {
        const badge = document.getElementById("api-health-badge");
        try {
            const data = await api.get("/health");
            if (data.status === "ok") {
                badge.innerHTML = `<span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span><span class="text-xs font-medium text-emerald-700">API Sẵn sàng</span>`;
            }
        } catch (err) {
            badge.innerHTML = `<span class="w-2 h-2 rounded-full bg-rose-500"></span><span class="text-xs font-medium text-rose-700">Mất kết nối API</span>`;
        }
    }

    // 3. Khởi tạo các module
    initRegulations();
    initDossiers();
    checkHealth();
});
