import { apiClient } from "@/api/client";

export async function fetchMonthlyReport({ month, departmentId } = {}) {
    const { data } = await apiClient.get("/reports/monthly", {
        params: {
            month,
            department_id: departmentId ?? undefined,
        },
    });
    return data;
}
