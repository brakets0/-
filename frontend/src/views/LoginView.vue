<script setup>
import { ElMessage } from "element-plus";
import { reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { defaultRouteName } from "@/config/navigation";
import { useAuthStore } from "@/stores/auth";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();

const form = reactive({ username: "", password: "" });
const errorMessage = ref("");
const submitting = ref(false);

const demoAccounts = [
    { username: "admin", password: "admin123", label: "总管理员 admin" },
    { username: "manager", password: "manager123", label: "部门管理员 manager" },
    { username: "employee", password: "employee123", label: "员工 employee" },
];

function fillDemoAccount(account) {
    form.username = account.username;
    form.password = account.password;
}

async function submit() {
    errorMessage.value = "";
    submitting.value = true;
    try {
        const profile = await auth.login(form.username.trim(), form.password);
        ElMessage.success(`欢迎回来，${profile.name || profile.username}`);
        const redirect = typeof route.query.redirect === "string" ? route.query.redirect : "";
        router.replace(redirect || { name: defaultRouteName(profile.role) });
    } catch (error) {
        errorMessage.value = error.message || "登录失败，请稍后重试";
    } finally {
        submitting.value = false;
    }
}
</script>

<template>
    <div class="login-shell">
        <main class="login-panel glass">
            <div class="login-left">
                <div class="brand-mark">
                    <div class="brand-icon"></div>
                    <div>
                        <p class="brand-eyebrow">employee attendance</p>
                        <h1>员工考勤系统</h1>
                    </div>
                </div>
                <p class="brand-copy">
                    部门与总管理员双入口 · 人脸识别打卡 · 审批与月度报表协同管理
                </p>
                <div class="login-stats">
                    <span>实时考勤</span><span>智能审批</span><span>月度报表</span>
                </div>
            </div>
            <div class="login-right">
                <div class="login-heading">
                    <span class="status-dot"></span>
                    <span>账号登录</span>
                </div>
                <p class="login-sub">欢迎回来，请登录管理台</p>
                <form autocomplete="off" @submit.prevent="submit">
                    <label class="field">
                        <span>用户名</span>
                        <div class="input-wrap">
                            <input
                                v-model="form.username"
                                name="username"
                                autocomplete="username"
                                maxlength="50"
                                placeholder="请输入用户名"
                                required
                            >
                            <span class="input-glow"></span>
                        </div>
                    </label>
                    <label class="field">
                        <span>密码</span>
                        <div class="input-wrap">
                            <input
                                v-model="form.password"
                                name="password"
                                type="password"
                                autocomplete="current-password"
                                maxlength="128"
                                placeholder="请输入密码"
                                required
                            >
                            <span class="input-glow"></span>
                        </div>
                    </label>
                    <p class="form-error" role="alert">{{ errorMessage }}</p>
                    <button class="btn btn-primary" type="submit" :disabled="submitting">
                        <span>{{ submitting ? "登录中..." : "登录管理台" }}</span>
                        <span class="btn-shine"></span>
                    </button>
                </form>
                <div class="demo-accounts">
                    <span>演示账号</span>
                    <button
                        v-for="account in demoAccounts"
                        :key="account.username"
                        class="account-chip"
                        type="button"
                        @click="fillDemoAccount(account)"
                    >
                        {{ account.label }}
                    </button>
                </div>
            </div>
        </main>
    </div>
</template>
