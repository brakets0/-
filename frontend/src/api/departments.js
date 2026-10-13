import { apiClient } from "@/api/client";

export async function listDepartments() {
    const { data } = await apiClient.get("/departments");
    return data;
}

export async function createDepartment(payload) {
    const { data } = await apiClient.post("/departments", payload);
    return data;
}

export async function updateDepartment(departmentId, payload) {
    const { data } = await apiClient.patch(`/departments/${departmentId}`, payload);
    return data;
}

export async function deleteDepartment(departmentId) {
    await apiClient.delete(`/departments/${departmentId}`);
}
