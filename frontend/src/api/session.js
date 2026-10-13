const STORAGE_KEY = "employee_attendance_session";

export function readSession() {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        return raw ? JSON.parse(raw) : null;
    } catch (error) {
        return null;
    }
}

export function writeSession(session) {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
    } catch (error) {
        // 隐私模式等场景写入失败时保持内存态会话，不影响本次使用。
    }
}

export function clearSession() {
    try {
        localStorage.removeItem(STORAGE_KEY);
    } catch (error) {
        // 忽略清理失败。
    }
}

export const SESSION_EXPIRED_EVENT = "app:session-expired";
