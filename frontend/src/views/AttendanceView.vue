<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

import { fetchAttendanceDay } from "@/api/attendance";
import { useAuthStore } from "@/stores/auth";
import { useDepartmentsStore } from "@/stores/departments";

const auth = useAuthStore();
const departmentsStore = useDepartmentsStore();

const date = ref(todayIso());
const departmentId = ref(null);
const rows = ref([]);
const loading = ref(false);
const errorMessage = ref("");

const STATUS_META = {
    present: { label: "正常", tag: "tag-success" },
    late: { label: "迟到", tag: "tag-warning" },
    early_leave: { label: "早退", tag: "tag-warning" },
    absent: { label: "缺勤", tag: "tag-danger" },
    partial: { label: "未完成", tag: "tag-cyan" },
};

const isAdmin = computed(() => auth.role === "general_admin");

const summary = computed(() => {
    const total = rows.value.length;
    const punched = rows.value.filter((row) => row.has_record).length;
    const late = rows.value.filter((row) => row.status === "late").length;
    const absent = rows.value.filter((row) => row.status === "absent").length;
    return { total, punched, late, absent };
});

function todayIso() {
    const now = new Date();
    const pad = (value) => String(value).padStart(2, "0");
    return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

function shortTime(value) {
    return value ? value.slice(11, 16) : "—";
}

function formatHours(minutes) {
    return minutes ? `${(minutes / 60).toFixed(1)}h` : "0.0h";
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
        rows.value = await fetchAttendanceDay({
            date: date.value,
            departmentId: isAdmin.value ? departmentId.value : undefined,
        });
    } catch (error) {
        rows.value = [];
        errorMessage.value = error.message;
    } finally {
        loading.value = false;
    }
}

onMounted(async () => {
    if (isAdmin.value) {
        try {
            await departmentsStore.ensureLoaded();
        } catch (error) {
            // 部门下拉加载失败不阻塞考勤列表。
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
                <h3>考勤中心</h3>
                <p class="panel-sub">
                    {{ isAdmin ? "全部部门当日出勤对账" : "本部门当日出勤对账" }}
                </p>
            </div>
            <span class="status-pill">{{ date }}</span>
        </div>

        <div class="filter-toolbar">
            <el-date-picker
                v-model="date"
                type="date"
                value-format="YYYY-MM-DD"
                :clearable="false"
                class="filter-field"
                @change="load"
            />
            <el-select
                v-if="isAdmin"
                v-model="departmentId"
                placeholder="全部部门"
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
            <button class="btn btn-ghost" type="button" @click="load">刷新</button>
        </div>

        <div class="filter-summary">
            应出勤 {{ summary.total }} 人 · 已打卡 {{ summary.punched }} 人 ·
            迟到 {{ summary.late }} 人 · 缺勤 {{ summary.absent }} 人
        </div>

        <div class="table-scroll">
            <el-table
                v-loading="loading"
                :data="rows"
                :empty-text="errorMessage || '当日暂无可统计人员'"
                class="attendance-center-table"
            >
                <el-table-column label="部门" min-width="120">
                    <template #default="{ row }">{{ row.department_name || "—" }}</template>
                </el-table-column>
                <el-table-column prop="employee_no" label="工号" min-width="110" />
                <el-table-column prop="name" label="姓名" min-width="100" />
                <el-table-column label="上班" min-width="90">
                    <template #default="{ row }">{{ shortTime(row.sign_in_at) }}</template>
                </el-table-column>
                <el-table-column label="下班" min-width="90">
                    <template #default="{ row }">{{ shortTime(row.sign_out_at) }}</template>
                </el-table-column>
                <el-table-column label="状态" min-width="110">
                    <template #default="{ row }">
                        <span class="tag" :class="statusTag(row.status)">
                            {{ statusLabel(row.status) }}
                        </span>
                    </template>
                </el-table-column>
                <el-table-column label="工时" min-width="90">
                    <template #default="{ row }">{{ formatHours(row.working_minutes) }}</template>
                </el-table-column>
            </el-table>
        </div>
    </section>
</template>

<style scoped>
.filter-field {
    width: 100%;
    max-width: 220px;
}

.table-scroll {
    width: 100%;
}

@media (max-width: 720px) {
    .table-scroll {
        overflow-x: auto;
    }

    .table-scroll :deep(.attendance-center-table) {
        min-width: 820px;
    }
}
</style>
