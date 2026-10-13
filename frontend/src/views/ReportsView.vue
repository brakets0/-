<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

import { fetchMonthlyReport } from "@/api/reports";
import { useAuthStore } from "@/stores/auth";
import { useDepartmentsStore } from "@/stores/departments";

const auth = useAuthStore();
const departmentsStore = useDepartmentsStore();

const month = ref(currentMonth());
const departmentId = ref(null);
const report = ref(null);
const loading = ref(false);
const errorMessage = ref("");

const isAdmin = computed(() => auth.role === "general_admin");
const rows = computed(() => report.value?.rows || []);

const summary = computed(() => {
    const items = rows.value;
    if (!items.length) {
        return { departments: 0, attendanceRate: 0, averageHours: 0, leaveDays: 0, tripDays: 0 };
    }
    const totalMinutes = items.reduce(
        (total, item) => total + item.average_working_minutes,
        0
    );
    return {
        departments: items.length,
        attendanceRate:
            items.reduce((total, item) => total + item.attendance_rate, 0) / items.length,
        averageHours: totalMinutes / items.length / 60,
        leaveDays: items.reduce((total, item) => total + item.leave_days, 0),
        tripDays: items.reduce((total, item) => total + item.trip_days, 0),
    };
});

function currentMonth() {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

function formatHours(minutes) {
    return minutes ? `${(minutes / 60).toFixed(1)}h` : "0.0h";
}

function formatRate(rate) {
    return `${Number(rate || 0).toFixed(1)}%`;
}

async function load() {
    loading.value = true;
    errorMessage.value = "";
    try {
        report.value = await fetchMonthlyReport({
            month: month.value,
            departmentId: isAdmin.value ? departmentId.value : undefined,
        });
    } catch (error) {
        report.value = null;
        errorMessage.value = error.message;
    } finally {
        loading.value = false;
    }
}

function resetFilters() {
    month.value = currentMonth();
    departmentId.value = null;
    load();
}

function exportCsv() {
    if (!rows.value.length) return;
    const headers = [
        "部门",
        "人数",
        "应出勤",
        "出勤",
        "迟到",
        "早退",
        "缺勤",
        "平均工时",
        "平均出勤率",
        "请假天数",
        "外派天数",
    ];
    const csvCell = (value) => `"${String(value ?? "").replaceAll('"', '""')}"`;
    const lines = rows.value.map((row) => [
        row.department_name,
        row.employee_count,
        row.work_days,
        row.attended_days,
        row.late_count,
        row.early_leave_count,
        row.absent_days,
        `${(row.average_working_minutes / 60).toFixed(1)}h`,
        `${row.attendance_rate.toFixed(1)}%`,
        row.leave_days.toFixed(1),
        row.trip_days.toFixed(1),
    ]);
    const csv = [headers, ...lines].map((line) => line.map(csvCell).join(",")).join("\r\n");
    const blob = new Blob([`\uFEFF${csv}`], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `考勤报表_${month.value}.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
}

onMounted(async () => {
    if (isAdmin.value) {
        try {
            await departmentsStore.ensureLoaded();
        } catch (error) {
            // 部门筛选加载失败不阻塞报表主体。
        }
    }
    await load();
    window.addEventListener("app:refresh", load);
});

onBeforeUnmount(() => {
    window.removeEventListener("app:refresh", load);
});
</script>

<template>
    <section class="panel page-enter">
        <div class="panel-header">
            <div>
                <h3>月度报表</h3>
                <p class="panel-sub">
                    {{ report?.scope_label || (isAdmin ? "全公司" : "本部门") }} ·
                    月度考勤、请假与外派统计
                </p>
            </div>
            <div class="row-actions">
                <button
                    class="btn btn-primary"
                    type="button"
                    :disabled="!rows.length"
                    @click="exportCsv"
                >
                    <span>导出 CSV</span>
                    <span class="btn-shine"></span>
                </button>
            </div>
        </div>

        <div class="filter-toolbar">
            <el-date-picker
                v-model="month"
                type="month"
                value-format="YYYY-MM"
                :clearable="false"
                class="filter-field"
                @change="load"
            />
            <el-select
                v-if="isAdmin"
                v-model="departmentId"
                placeholder="全公司"
                clearable
                class="filter-field"
                @change="load"
            >
                <el-option
                    v-for="department in departmentsStore.items"
                    :key="department.id"
                    :label="department.name"
                    :value="department.id"
                />
            </el-select>
            <div v-else class="filter-static">
                {{ report?.scope_label || auth.user?.department_name || "本部门" }}
            </div>
            <button class="btn btn-ghost" type="button" @click="load">刷新</button>
            <button class="btn btn-ghost" type="button" @click="resetFilters">重置筛选</button>
        </div>

        <div class="report-metrics">
            <article class="metric-card glass accent-cyan">
                <div class="metric-label"><span class="status-dot"></span>部门数</div>
                <h3>{{ summary.departments }}</h3>
                <span class="metric-delta">{{ month }}</span>
            </article>
            <article class="metric-card glass accent-violet">
                <div class="metric-label"><span class="status-dot"></span>平均出勤率</div>
                <h3>{{ formatRate(summary.attendanceRate) }}</h3>
                <span class="metric-delta">迟到、早退当天仍计出勤</span>
            </article>
            <article class="metric-card glass accent-pink">
                <div class="metric-label"><span class="status-dot"></span>平均工时</div>
                <h3>{{ summary.averageHours.toFixed(1) }}h</h3>
                <span class="metric-delta">按实际打卡记录平均</span>
            </article>
            <article class="metric-card glass accent-cyan">
                <div class="metric-label"><span class="status-dot"></span>请假 / 外派</div>
                <h3>{{ summary.leaveDays.toFixed(1) }} / {{ summary.tripDays.toFixed(1) }}</h3>
                <span class="metric-delta">单位：天</span>
            </article>
        </div>

        <div class="table-scroll">
            <el-table
                v-loading="loading"
                :data="rows"
                :empty-text="errorMessage || '当前筛选条件下暂无报表数据'"
                class="report-table"
            >
                <el-table-column prop="department_name" label="部门" min-width="130" />
                <el-table-column prop="employee_count" label="人数" min-width="80" />
                <el-table-column prop="work_days" label="应出勤" min-width="90" />
                <el-table-column prop="attended_days" label="出勤" min-width="80" />
                <el-table-column prop="late_count" label="迟到" min-width="80" />
                <el-table-column prop="early_leave_count" label="早退" min-width="80" />
                <el-table-column prop="absent_days" label="缺勤" min-width="80" />
                <el-table-column label="平均工时" min-width="100">
                    <template #default="{ row }">
                        {{ formatHours(row.average_working_minutes) }}
                    </template>
                </el-table-column>
                <el-table-column label="平均出勤率" min-width="110">
                    <template #default="{ row }">{{ formatRate(row.attendance_rate) }}</template>
                </el-table-column>
                <el-table-column label="请假" min-width="80">
                    <template #default="{ row }">{{ row.leave_days.toFixed(1) }}</template>
                </el-table-column>
                <el-table-column label="外派" min-width="80">
                    <template #default="{ row }">{{ row.trip_days.toFixed(1) }}</template>
                </el-table-column>
            </el-table>
        </div>
    </section>
</template>

<style scoped>
.filter-field {
    width: 100%;
    max-width: 200px;
}

.filter-static {
    display: flex;
    align-items: center;
    min-height: 38px;
    padding: 0 14px;
    border: 1px solid var(--line);
    border-radius: var(--radius-control);
    color: var(--muted);
}

.report-metrics {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 14px;
    margin-bottom: 18px;
}

.table-scroll {
    width: 100%;
}

@media (max-width: 960px) {
    .report-metrics {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
}

@media (max-width: 720px) {
    .report-metrics {
        grid-template-columns: minmax(0, 1fr);
    }

    .table-scroll {
        overflow-x: auto;
    }

    .table-scroll :deep(.report-table) {
        min-width: 980px;
    }
}
</style>
