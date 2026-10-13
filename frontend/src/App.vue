<script setup>
import { onBeforeUnmount, onMounted } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";

import { SESSION_EXPIRED_EVENT } from "@/api/session";
import { useAuthStore } from "@/stores/auth";

const router = useRouter();
const auth = useAuthStore();

function handleSessionExpired() {
    if (!auth.isAuthenticated) return;
    auth.logout();
    ElMessage.warning("登录状态已失效，请重新登录");
    router.replace({ name: "login" });
}

onMounted(() => {
    window.addEventListener(SESSION_EXPIRED_EVENT, handleSessionExpired);
});

onBeforeUnmount(() => {
    window.removeEventListener(SESSION_EXPIRED_EVENT, handleSessionExpired);
});
</script>

<template>
    <router-view />
</template>
