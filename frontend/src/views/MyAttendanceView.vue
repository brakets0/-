<script setup>
import { ElMessage } from "element-plus";
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

import { fetchMyAttendance, punch as punchRequest } from "@/api/attendance";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();

const month = ref(currentMonth());
const data = ref(null);
const loading = ref(false);
const punching = ref(false);
const errorMessage = ref("");
const clock = ref("");
let clockTimer = null;

const STATUS_META = {
    present: { label: "正常", tag: "tag-success" },
    late: { label: "迟到", tag: "tag-warning" },
    early_leave: { label: "早退", tag: "tag-warning" },
    absent: { label: "缺勤", tag: "tag-danger" },
    partial: { label: "未完成", tag: "tag-cyan" },
};

const summary = computed(() => data.value?.summary || null);
const records = computed(() => data.value?.records || []);
const todayRecord = computed(
    () => records.value.find((item) => item.work_date === todayIso()) || null
);
const canSignIn = computed(() => !todayRecord.value?.sign_in_at);
const canSignOut = computed(
    () => Boolean(todayRecord.value?.sign_in_at) && !todayRecord.value?.sign_out_at
);

const todayStatus = computed(() => {
    const record = todayRecord.value;
    if (!record) return "未打卡";
    if (!record.is_workday) return "休息日打卡";
    if (record.sign_in_at && record.sign_out_at) return "已签退";
    if (record.sign_in_at) return "已签到";
    return "未打卡";
});

const todayDetail = computed(() => {
    const record = todayRecord.value;
    if (!record) return "今日暂无打卡记录";
    const start = shortTime(record.sign_in_at) || "--:--";
    const end = shortTime(record.sign_out_at) || "--:--";
    return `${start} 上班 · ${end} 下班`;
});

const todayHours = computed(
    () => formatHours(todayRecord.value?.working_minutes || 0)
);

function currentMonth() {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

function todayIso() {
    const now = new Date();
    const pad = (value) => String(value).padStart(2, "0");
    return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

function tick() {
    const now = new Date();
    const pad = (value) => String(value).padStart(2, "0");
    clock.value = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
}

function shortTime(value) {
    return value ? value.slice(11, 16) : "";
}

function shortDate(value) {
    return value ? value.slice(5) : "—";
}

function formatHours(minutes) {
    if (!minutes) return "0.0h";
    return `${(minutes / 60).toFixed(1)}h`;
}

function statusLabel(status) {
    if (!status) return "休息";
    return STATUS_META[status]?.label || status;
}

function statusTag(status) {
    return STATUS_META[status]?.tag || "tag-cyan";
}

async function load() {
    loading.value = true;
    errorMessage.value = "";
    try {
        data.value = await fetchMyAttendance(month.value);
    } catch (error) {
        data.value = null;
        errorMessage.value = error.message;
    } finally {
        loading.value = false;
    }
}

async function doPunch(punchType) {
    punching.value = true;
    try {
        await punchRequest(punchType);
        ElMessage.success(punchType === "in" ? "签到成功" : "签退成功");
        await load();
    } catch (error) {
        ElMessage.error(error.message);
    } finally {
        punching.value = false;
    }
}

onMounted(() => {
    tick();
    clockTimer = setInterval(tick, 1000);
    load();
    window.addEventListener("app:refresh", load);
});

onBeforeUnmount(() => {
    clearInterval(clockTimer);
    window.removeEventListener("app:refresh", load);
});
</script>

<template>
    <div class="hero-grid">
        <article class="metric-card glass accent-cyan">
            <div class="metric-label"><span class="status-dot"></span>今日状态</div>
            <h3>{{ todayStatus }}</h3>
            <span class="metric-delta">{{ todayDetail }}</span>
        </article>
        <article class="metric-card glass accent-violet">
            <div class="metric-label"><span class="status-dot"></span>今日工时</div>
            <h3>{{ todayHours }}</h3>
            <span class="metric-delta">按班次扣除午休</span>
        </article>
        <article class="metric-card glass accent-pink">
            <div class="metric-label"><span class="status-dot"></span>本月出勤</div>
            <h3>{{ summary ? `${summary.attended_days}天` : "—" }}</h3>
            <span class="metric-delta">
                <template v-if="summary">
                    应出勤 {{ summary.work_days }} 天 · 缺勤 {{ summary.absent_days }} 天 ·
                    迟到 {{ summary.late_count }} 次
                </template>
                <template v-else>暂无数据</template>
            </span>
        </article>
    </div>

    <section class="panel page-enter">
        <div class="panel-header">
            <div>
                <h3>打卡</h3>
                <p class="panel-sub">
                    {{ auth.user?.name }} ·
                    {{ auth.user?.department_name || "未分配部门" }}
                </p>
            </div>
            <span class="status-pill">{{ clock }}</span>
        </div>
        <div class="row-actions punch-actions">
            <button
                class="btn btn-primary"
                type="button"
                :disabled="!canSignIn || punching"
                @click="doPunch('in')"
            >
                <span>签到</span>
                <span class="btn-shine"></span>
            </button>
            <button
                class="btn btn-ghost"
                type="button"
                :disabled="!canSignOut || punching"
                @click="doPunch('out')"
            >
                签退
            </button>
        </div>
    </section>

    <div class="deep-panel">
        <section class="panel page-enter">
            <div class="panel-header">
                <div>
                    <h3>考勤明细</h3>
                    <p class="panel-sub">仅展示当前账号的打卡记录</p>
                </div>
                <el-date-picker
                    v-model="month"
                    type="month"
                    value-format="YYYY-MM"
                    :clearable="false"
                    class="month-picker"
                    @change="load"
                />
            </div>
            <div class="table-scroll">
                <el-table
                    v-loading="loading"
                    :data="records"
                    :empty-text="errorMessage || '暂无考勤记录'"
                    class="attendance-table"
                >
                    <el-table-column label="日期" min-width="110">
                        <template #default="{ row }">{{ shortDate(row.work_date) }}</template>
                    </el-table-column>
                    <el-table-column label="上班" min-width="90">
                        <template #default="{ row }">
                            {{ shortTime(row.sign_in_at) || "—" }}
                        </template>
                    </el-table-column>
                    <el-table-column label="下班" min-width="90">
                        <template #default="{ row }">
                            {{ shortTime(row.sign_out_at) || "—" }}
                        </template>
                    </el-table-column>
                    <el-table-column label="状态" min-width="110">
                        <template #default="{ row }">
                            <span class="tag" :class="statusTag(row.status)">
                                {{ statusLabel(row.status) }}
                            </span>
                        </template>
                    </el-table-column>
                    <el-table-column label="工时" min-width="90">
                        <template #default="{ row }">
                            {{ formatHours(row.working_minutes) }}
                        </template>
                    </el-table-column>
                </el-table>
            </div>
        </section>

        <section class="panel page-enter">
            <div class="panel-header">
                <div>
                    <h3>个人档案</h3>
                    <p class="panel-sub">账号与所属部门</p>
                </div>
            </div>
            <div class="recent-row">
                <div class="mini-avatar">{{ (auth.user?.name || "员").slice(0, 1) }}</div>
                <div class="recent-info">
                    <strong>{{ auth.user?.name || "员工" }}</strong>
                    <span>
                        {{ auth.user?.employee_no || "—" }} ·
                        {{ auth.user?.department_name || "未分配" }}
                    </span>
                </div>
                <span class="tag tag-cyan">在职</span>
            </div>
        </section>
    </div>
</template>

<style scoped>
.punch-actions :deep(.btn) {
    width: auto;
    min-width: 132px;
    height: 46px;
}

.month-picker {
    max-width: 160px;
}

.table-scroll {
    width: 100%;
}

@media (max-width: 720px) {
    .table-scroll {
        overflow-x: auto;
    }

    .table-scroll :deep(.attendance-table) {
        min-width: 520px;
    }
}
</style>
