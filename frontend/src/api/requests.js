import { apiClient } from "@/api/client";

export async function listLeaveRequests(params) {
    const { data } = await apiClient.get("/leave-requests", { params });
    return data;
}

export async function listBusinessTrips(params) {
    const { data } = await apiClient.get("/business-trips", { params });
    return data;
}

export async function createLeaveRequest(payload) {
    const { data } = await apiClient.post("/leave-requests", payload);
    return data;
}

export async function createBusinessTrip(payload) {
    const { data } = await apiClient.post("/business-trips", payload);
    return data;
}

export async function reviewLeaveRequest(requestId, payload) {
    const { data } = await apiClient.patch(
        `/leave-requests/${requestId}/review`,
        payload
    );
    return data;
}

export async function reviewBusinessTrip(requestId, payload) {
    const { data } = await apiClient.patch(
        `/business-trips/${requestId}/review`,
        payload
    );
    return data;
}

export async function deleteLeaveRequest(requestId) {
    await apiClient.delete(`/leave-requests/${requestId}`);
}

export async function deleteBusinessTrip(requestId) {
    await apiClient.delete(`/business-trips/${requestId}`);
}
