import { apiClient } from "@/api/client";

export async function listShifts() {
    const { data } = await apiClient.get("/shifts");
    return data;
}

export async function createShift(payload) {
    const { data } = await apiClient.post("/shifts", payload);
    return data;
}

export async function updateShift(shiftId, payload) {
    const { data } = await apiClient.patch(`/shifts/${shiftId}`, payload);
    return data;
}

export async function deleteShift(shiftId) {
    await apiClient.delete(`/shifts/${shiftId}`);
}
