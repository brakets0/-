<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

import { fetchAttendanceDay } from "@/api/attendance";
import { listBusinessTrips, listLeaveRequests } from "@/api/requests";
import { fetchMonthlyReport } from "@/api/reports";
import { ROLE_LABELS } from "@/config/navigation";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();

const loading = ref(false);
const errorMessage = ref("");
const report = ref(null);
const attendanceRows = ref([]);
const pendingCount = ref(0);

const roleLabel = computed(() => ROLE_LABELS[auth.role] || auth.role);
const departmentLabel = computed(() => auth.user?.department_name || "未分配");
const canReview = computed(() => auth.hasPermission("leave.review.department"));

const today = computed(() => todayIso());
const currentMonth = computed(() => today.value.slice(0, 7));

const attendanceSummary = computed(() => {
    const rows = attendanceRows.value;
    return {
        total: rows.length,
        punched: rows.filter((row) => row.has_record).length,
        late: rows.filter((row) => row.status === "late").length,
        absent: rows.filter((row) => row.status === "absent").length,
    };
});

const reportSummary = computed(() => {
    const rows = report.value?.rows || [];
    if (!rows.length) {
        return { rate: 0, hours: 0, leaveDays: 0, tripDays: 0 };
    }
    const totalMinutes = rows.reduce(
        (total, item) => total + item.average_working_minutes,
        0
    );
    return {
        rate: rows.reduce((total, item) => total + item.attendance_rate, 0) / rows.length,
        hours: totalMinutes / rows.length / 60,
        leaveDays: rows.reduce((total, item) => total + item.leave_days, 0),
        tripDays: rows.reduce((total, item) => total + item.trip_days, 0),
    };
});

function todayIso() {
    const now = new Date();
    const pad = (value) => String(value).padStart(2, "0");
    return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

function formatRate(value) {
    return `${Number(value || 0).toFixed(1)}%`;
}

async function load() {
    loading.value = true;
    errorMessage.value = "";

    const tasks = [
        fetchMonthlyReport({ month: currentMonth.value })
            .then((data) => {
                report.value = data;
            })
            .catch((error) => {
                report.value = null;
                throw error;
            }),
        fetchAttendanceDay({ date: today.value })
            .then((rows) => {
                attendanceRows.value = rows;
            })
            .catch((error) => {
                attendanceRows.value = [];
                throw error;
            }),
    ];
    if (canReview.value) {
        tasks.push(
            Promise.all([
                listLeaveRequests({ status: "pending" }),
                listBusinessTrips({ status: "pending" }),
            ])
                .then(([leaves, trips]) => {
                    pendingCount.value = leaves.length + trips.length;
                })
                .catch((error) => {
                    pendingCount.value = 0;
                    throw error;
                })
        );
    }

    try {
        await Promise.all(tasks);
    } catch (error) {
        errorMessage.value = error.message;
    } finally {
        loading.value = false;
    }
}

onMounted(() => {
    load();
    window.addEventListener("app:refresh", load);
});

onBeforeUnmount(() => {
    window.removeEventListener("app:refresh", load);
});
</script>

<template>
    <div class="hero-grid">
        <article class="metric-card glass accent-cyan">
            <div class="metric-label"><span class="status-dot"></span>姓名 / 工号</div>
            <h3 class="account-metric">{{ auth.user?.name || "-" }}</h3>
            <span class="metric-delta">{{ auth.user?.employee_no || "无工号" }}</span>
        </article>
        <article class="metric-card glass accent-violet">
            <div class="metric-label"><span class="status-dot"></span>角色 / 部门</div>
            <h3 class="account-metric">{{ roleLabel }}</h3>
            <span class="metric-delta">
                {{ departmentLabel }} · {{ auth.permissions.length }} 项权限
            </span>
        </article>
    </div>

    <section class="panel page-enter" v-loading="loading">
        <div class="panel-header">
            <div>
                <h3>今日出勤</h3>
                <p class="panel-sub">{{ today }} · {{ report?.scope_label || "当前范围" }}</p>
            </div>
            <span class="status-pill">{{ attendanceSummary.punched }} / {{ attendanceSummary.total }}</span>
        </div>
        <div class="hero-grid">
            <article class="metric-card glass accent-cyan">
                <div class="metric-label"><span class="status-dot"></span>应出勤</div>
                <h3>{{ attendanceSummary.total }}</h3>
                <span class="metric-delta">人</span>
            </article>
            <article class="metric-card glass accent-violet">
                <div class="metric-label"><span class="status-dot"></span>已打卡</div>
                <h3>{{ attendanceSummary.punched }}</h3>
                <span class="metric-delta">人</span>
            </article>
            <article class="metric-card glass accent-pink">
                <div class="metric-label"><span class="status-dot"></span>迟到 / 缺勤</div>
                <h3>{{ attendanceSummary.late }} / {{ attendanceSummary.absent }}</h3>
                <span class="metric-delta">人</span>
            </article>
        </div>
        <p v-if="errorMessage" class="demo-note">{{ errorMessage }}</p>
    </section>

    <section class="panel page-enter" v-loading="loading">
        <div class="panel-header">
            <div>
                <h3>本月概览</h3>
                <p class="panel-sub">{{ currentMonth }} · 出勤率、工时与申请</p>
            </div>
        </div>
        <div class="hero-grid">
            <article class="metric-card glass accent-cyan">
                <div class="metric-label"><span class="status-dot"></span>平均出勤率</div>
                <h3>{{ formatRate(reportSummary.rate) }}</h3>
                <span class="metric-delta">迟到、早退当天仍计出勤</span>
            </article>
            <article class="metric-card glass accent-violet">
                <div class="metric-label"><span class="status-dot"></span>平均工时</div>
                <h3>{{ reportSummary.hours.toFixed(1) }}h</h3>
                <span class="metric-delta">按实际打卡记录平均</span>
            </article>
            <article class="metric-card glass accent-pink">
                <div class="metric-label"><span class="status-dot"></span>请假 / 外派</div>
                <h3>
                    {{ reportSummary.leaveDays.toFixed(1) }} /
                    {{ reportSummary.tripDays.toFixed(1) }}
                </h3>
                <span class="metric-delta">单位：天</span>
            </article>
            <article v-if="canReview" class="metric-card glass accent-cyan">
                <div class="metric-label"><span class="status-dot"></span>待审批</div>
                <h3>{{ pendingCount }}</h3>
                <span class="metric-delta">条请假 / 外派申请</span>
            </article>
        </div>
    </section>
</template>

<style scoped>
.account-metric {
    font-size: 22px;
    overflow-wrap: anywhere;
}
</style>
