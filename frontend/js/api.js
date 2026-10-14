/**
 * Module API Client
 * -----------------
 * Xử lý các yêu cầu HTTP fetch tới backend FastAPI (/api/v1).
 * Bắt lỗi và chuẩn hóa thông báo phản hồi (HTTP 400, 404, 409, 422).
 */

const API_BASE = "/api/v1";

async function request(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const defaultHeaders = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    };

    const config = {
        ...options,
        headers: {
            ...defaultHeaders,
            ...options.headers,
        },
    };

    try {
        const response = await fetch(url, config);
        const isJson = response.headers.get("content-type")?.includes("application/json");
        const data = isJson ? await response.json() : null;

        if (!response.ok) {
            let errorMessage = "Đã xảy ra lỗi hệ thống.";
            if (data && data.detail) {
                if (typeof data.detail === "string") {
                    errorMessage = data.detail;
                } else if (Array.isArray(data.detail)) {
                    // Định dạng lỗi validation của Pydantic
                    errorMessage = data.detail.map(err => `${err.loc?.slice(-1)[0] || 'Dữ liệu'}: ${err.msg}`).join("; ");
                }
            }
            const error = new Error(errorMessage);
            error.status = response.status;
            error.data = data;
            throw error;
        }

        return data;
    } catch (err) {
        if (!err.status) {
            err.message = "Không thể kết nối đến máy chủ. Vui lòng kiểm tra server!";
        }
        throw err;
    }
}

export const api = {
    get: (endpoint, params = {}) => {
        const query = new URLSearchParams();
        Object.entries(params).forEach(([key, value]) => {
            if (value !== null && value !== undefined && value !== "") {
                query.append(key, value);
            }
        });
        const qs = query.toString() ? `?${query.toString()}` : "";
        return request(`${endpoint}${qs}`, { method: "GET" });
    },
    post: (endpoint, body = {}) => request(endpoint, { method: "POST", body: JSON.stringify(body) }),
    put: (endpoint, body = {}) => request(endpoint, { method: "PUT", body: JSON.stringify(body) }),
    patch: (endpoint, body = {}) => request(endpoint, { method: "PATCH", body: JSON.stringify(body) }),
    delete: (endpoint) => request(endpoint, { method: "DELETE" }),
    upload: async (endpoint, formData) => {
        const url = `${API_BASE}${endpoint}`;
        try {
            const response = await fetch(url, {
                method: "POST",
                headers: {
                    "Accept": "application/json",
                },
                body: formData,
            });
            const isJson = response.headers.get("content-type")?.includes("application/json");
            const data = isJson ? await response.json() : null;

            if (!response.ok) {
                let errorMessage = "Đã xảy ra lỗi khi tải lên tệp tin.";
                if (data && data.detail) {
                    if (typeof data.detail === "string") {
                        errorMessage = data.detail;
                    } else if (Array.isArray(data.detail)) {
                        errorMessage = data.detail.map(err => `${err.loc?.slice(-1)[0] || 'Dữ liệu'}: ${err.msg}`).join("; ");
                    }
                }
                const error = new Error(errorMessage);
                error.status = response.status;
                error.data = data;
                throw error;
            }
            return data;
        } catch (err) {
            if (!err.status) {
                err.message = "Không thể kết nối đến máy chủ khi tải tệp lên!";
            }
            throw err;
        }
    },
};

