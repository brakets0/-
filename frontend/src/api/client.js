import axios from "axios";

import { SESSION_EXPIRED_EVENT, clearSession, readSession } from "@/api/session";

// 后端业务接口统一挂在 /api 下，可用 VITE_API_BASE 覆盖（例如指向远端环境）。
const API_BASE = import.meta.env.VITE_API_BASE || "/api";

export const apiClient = axios.create({
    baseURL: API_BASE,
    timeout: 15000,
});

function describeDetail(detail) {
    if (typeof detail === "string" && detail) return detail;
    if (Array.isArray(detail)) {
        return detail
            .map((item) => item?.msg)
            .filter(Boolean)
            .join("；");
    }
    return "";
}

apiClient.interceptors.request.use((config) => {
    const session = readSession();
    if (session?.token) {
        config.headers.Authorization = `Bearer ${session.token}`;
    }
    return config;
});

apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        const status = error.response?.status;
        if (status === 401) {
            clearSession();
            window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
        }
        const detail = error.response?.data?.detail;
        const message =
            describeDetail(detail) ||
            (error.code === "ECONNABORTED"
                ? "请求超时，请稍后重试"
                : "请求失败，请稍后重试");
        return Promise.reject(new Error(message));
    }
);

export async function login(username, password) {
    const { data } = await apiClient.post("/auth/login", { username, password });
    return data;
}

export async function fetchProfile() {
    const { data } = await apiClient.get("/auth/me");
    return data;
}
