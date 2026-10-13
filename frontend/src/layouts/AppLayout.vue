<script setup>
import { ElMessage } from "element-plus";
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import NavIcon from "@/components/NavIcon.vue";
import { NAV_ITEMS, PAGE_TITLES, ROLE_LABELS } from "@/config/navigation";
import { useAuthStore } from "@/stores/auth";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();

const navItems = computed(() =>
    NAV_ITEMS.filter((item) => {
        if (item.hiddenForRoles?.includes(auth.role)) return false;
        if (item.permission && !auth.hasPermission(item.permission)) return false;
        return true;
    })
);

const pageTitle = computed(
    () => PAGE_TITLES[route.name] || route.meta.title || "工作台"
);
const roleLabel = computed(() => ROLE_LABELS[auth.role] || auth.role);
const avatarText = computed(() => (auth.user?.name || "A").slice(0, 1).toUpperCase());

const clock = ref("");
let clockTimer = null;

function tick() {
    const now = new Date();
    const pad = (value) => String(value).padStart(2, "0");
    clock.value = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(
        now.getDate()
    )} ${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
}

async function refreshProfile() {
    await auth.loadProfile();
    window.dispatchEvent(new CustomEvent("app:refresh"));
    ElMessage.success("数据已刷新");
}

function logout() {
    auth.logout();
    router.replace({ name: "login" });
}

onMounted(() => {
    tick();
    clockTimer = setInterval(tick, 1000);
});

onBeforeUnmount(() => {
    clearInterval(clockTimer);
});
</script>

<template>
    <div class="app-shell">
        <aside class="sidebar glass">
            <div class="sidebar-brand">
                <div class="brand-icon small"></div>
                <div>
                    <p class="brand-eyebrow">employee attendance</p>
                    <strong>员工考勤系统</strong>
                </div>
            </div>
            <nav class="side-nav">
                <router-link
                    v-for="item in navItems"
                    :key="item.name"
                    class="nav-item"
                    :class="{ active: route.name === item.name }"
                    :to="{ name: item.name }"
                >
                    <NavIcon :name="item.icon" />
                    <span>{{ item.label }}</span>
                </router-link>
            </nav>
            <div class="sidebar-user">
                <div class="avatar">{{ avatarText }}</div>
                <div class="sidebar-user-text">
                    <strong>{{ auth.user?.name || "管理员" }}</strong>
                    <span>{{ roleLabel }}</span>
                </div>
                <button
                    class="icon-btn logout-btn"
                    type="button"
                    title="退出登录"
                    aria-label="退出登录"
                    @click="logout"
                >
                    <NavIcon name="logout" />
                </button>
            </div>
        </aside>

        <main class="content">
            <header class="topbar">
                <div>
                    <p class="topbar-kicker">ATTENDANCE CONSOLE</p>
                    <h2>{{ pageTitle }}</h2>
                </div>
                <div class="topbar-actions">
                    <span class="topbar-time">{{ clock }}</span>
                    <button
                        class="icon-btn"
                        type="button"
                        title="刷新数据"
                        aria-label="刷新数据"
                        @click="refreshProfile"
                    >
                        <NavIcon name="refresh" />
                    </button>
                </div>
            </header>
            <section class="page-content">
                <router-view />
            </section>
        </main>
    </div>
</template>
