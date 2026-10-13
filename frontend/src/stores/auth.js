import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { fetchProfile, login as requestLogin } from "@/api/client";
import { clearSession, readSession, writeSession } from "@/api/session";
import { defaultRouteName } from "@/config/navigation";

export const useAuthStore = defineStore("auth", () => {
    const stored = readSession();
    const token = ref(stored?.token || "");
    const user = ref(stored?.user || null);
    const profileLoaded = ref(Boolean(stored?.user?.permissions));

    const isAuthenticated = computed(() => Boolean(token.value && user.value));
    const role = computed(() => user.value?.role || "");
    const permissions = computed(() => user.value?.permissions || []);
    const displayName = computed(() => user.value?.name || "未登录");

    function persist() {
        writeSession({ token: token.value, user: user.value });
    }

    function hasPermission(permission) {
        if (!permission) return true;
        return permissions.value.includes(permission) || role.value === "general_admin";
    }

    function applyProfile(profile) {
        user.value = {
            id: profile.id,
            employee_no: profile.employee_no,
            username: profile.username,
            name: profile.name,
            role: profile.role,
            department_id: profile.department_id,
            department_name: profile.department_name,
            permissions: profile.permissions || [],
        };
        profileLoaded.value = true;
        persist();
    }

    async function login(username, password) {
        const data = await requestLogin(username, password);
        token.value = data.access_token;
        user.value = data.user;
        profileLoaded.value = false;
        persist();
        const profile = await fetchProfile();
        applyProfile(profile);
        return profile;
    }

    async function loadProfile() {
        if (!token.value) return false;
        try {
            const profile = await fetchProfile();
            applyProfile(profile);
            return true;
        } catch (error) {
            logout();
            return false;
        }
    }

    function logout() {
        token.value = "";
        user.value = null;
        profileLoaded.value = false;
        clearSession();
    }

    return {
        token,
        user,
        profileLoaded,
        isAuthenticated,
        role,
        permissions,
        displayName,
        defaultRouteName: computed(() => defaultRouteName(role.value)),
        hasPermission,
        login,
        loadProfile,
        logout,
    };
});
