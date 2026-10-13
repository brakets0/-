import { apiClient } from "@/api/client";

export async function punch(punchType) {
    const { data } = await apiClient.post("/attendance/punch", {
        punch_type: punchType,
    });
    return data;
}

export async function fetchMyAttendance(month) {
    const { data } = await apiClient.get("/attendance/me", { params: { month } });
    return data;
}

export async function fetchAttendanceDay({ date, departmentId } = {}) {
    const { data } = await apiClient.get("/attendance", {
        params: {
            date,
            department_id: departmentId ?? undefined,
        },
    });
    return data;
}

export async function fetchEmployeeAttendance(employeeId, month) {
    const { data } = await apiClient.get(`/attendance/employee/${employeeId}`, {
        params: { month },
    });
    return data;
}
