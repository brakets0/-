import { apiClient } from "@/api/client";

export async function listEmployees() {
    const { data } = await apiClient.get("/employees");
    return data;
}

export async function createEmployee(payload) {
    const { data } = await apiClient.post("/employees", payload);
    return data;
}

export async function updateEmployee(employeeId, payload) {
    const { data } = await apiClient.patch(`/employees/${employeeId}`, payload);
    return data;
}

export async function deleteEmployee(employeeId) {
    await apiClient.delete(`/employees/${employeeId}`);
}
