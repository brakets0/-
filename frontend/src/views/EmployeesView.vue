<script setup>
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";

import {
    createEmployee,
    deleteEmployee,
    listEmployees,
    updateEmployee,
} from "@/api/employees";
import { fetchEmployeeAttendance } from "@/api/attendance";
import { ROLE_LABELS } from "@/config/navigation";
import { useAuthStore } from "@/stores/auth";
import { useDepartmentsStore } from "@/stores/departments";

const auth = useAuthStore();
const departmentsStore = useDepartmentsStore();

const employees = ref([]);
const loading = ref(false);
const loadError = ref("");

const dialogVisible = ref(false);
const submitting = ref(false);
const editingId = ref(null);
const formRef = ref(null);

const form = reactive({
    employee_no: "",
    username: "",
    name: "",
    department_id: null,
    role: "employee",
    status: "active",
    password: "",
});

const isAdmin = computed(() => auth.role === "general_admin");
const canViewAttendance = computed(() =>
    auth.hasPermission("attendance.view.department")
);
const panelSub = computed(() =>
    isAdmin.value ? "账号、所属部门与角色状态" : "仅本部门员工档案"
);
const dialogTitle = computed(() => (editingId.value ? "编辑员工" : "新建员工"));

const departmentOptions = computed(() => {
    if (isAdmin.value) return departmentsStore.items;
    return departmentsStore.items.filter(
        (department) => department.id === auth.user?.department_id
    );
});

const roleOptions = computed(() =>
    isAdmin.value
        ? [
              { value: "employee", label: "普通员工" },
              { value: "department_manager", label: "部门管理员" },
              { value: "general_admin", label: "总管理员" },
          ]
        : [{ value: "employee", label: "普通员工" }]
);

const departmentDisabled = computed(
    () => form.role === "general_admin" || !isAdmin.value
);

const rules = computed(() => ({
    employee_no: [{ required: true, message: "请输入工号", trigger: "blur" }],
    username: [{ required: true, message: "请输入用户名", trigger: "blur" }],
    name: [{ required: true, message: "请输入姓名", trigger: "blur" }],
    ...(editingId.value
        ? {}
        : {
              password: [
                  { required: true, message: "请输入初始密码", trigger: "blur" },
                  { min: 6, message: "密码至少 6 位", trigger: "blur" },
              ],
          }),
}));

const emptyText = computed(() => loadError.value || "暂无员工");

const ATTENDANCE_STATUS = {
    present: { label: "正常", tag: "tag-success" },
    late: { label: "迟到", tag: "tag-warning" },
    early_leave: { label: "早退", tag: "tag-warning" },
    absent: { label: "缺勤", tag: "tag-danger" },
    partial: { label: "未完成", tag: "tag-cyan" },
};

const attendanceVisible = ref(false);
const attendanceLoading = ref(false);
const attendanceError = ref("");
const attendanceMonth = ref(currentMonth());
const attendanceEmployee = ref(null);
const attendanceData = ref(null);

function roleLabel(role) {
    return ROLE_LABELS[role] || role;
}

function roleTagClass(role) {
    return role === "employee" ? "tag-cyan" : "tag-violet";
}

function statusTagClass(status) {
    return status === "active" ? "tag-success" : "tag-danger";
}

function statusLabel(status) {
    return status === "active" ? "在职" : "停用";
}

function canEdit(employee) {
    return isAdmin.value || employee.role === "employee";
}

function isAttendanceSubject(employee) {
    return employee.role !== "general_admin";
}

function currentMonth() {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

function attendanceStatusLabel(status) {
    if (!status) return "休息";
    return ATTENDANCE_STATUS[status]?.label || status;
}

function attendanceStatusTag(status) {
    return ATTENDANCE_STATUS[status]?.tag || "tag-cyan";
}

function shortDate(value) {
    return value ? value.slice(5) : "—";
}

function shortTime(value) {
    return value ? value.slice(11, 16) : "—";
}

function formatHours(minutes) {
    return minutes ? `${(minutes / 60).toFixed(1)}h` : "0.0h";
}

async function openAttendanceDrawer(employee) {
    attendanceEmployee.value = employee;
    attendanceMonth.value = currentMonth();
    attendanceData.value = null;
    attendanceError.value = "";
    attendanceVisible.value = true;
    await loadAttendance();
}

async function loadAttendance() {
    if (!attendanceEmployee.value) return;
    attendanceLoading.value = true;
    attendanceError.value = "";
    try {
        attendanceData.value = await fetchEmployeeAttendance(
            attendanceEmployee.value.id,
            attendanceMonth.value
        );
    } catch (error) {
        attendanceData.value = null;
        attendanceError.value = error.message;
    } finally {
        attendanceLoading.value = false;
    }
}

async function loadEmployees() {
    loading.value = true;
    loadError.value = "";
    departmentsStore.invalidate();
    try {
        employees.value = await listEmployees();
    } catch (error) {
        employees.value = [];
        loadError.value = error.message;
    } finally {
        loading.value = false;
    }
}

function resetForm() {
    form.employee_no = "";
    form.username = "";
    form.name = "";
    form.role = "employee";
    form.status = "active";
    form.password = "";
    form.department_id = isAdmin.value
        ? null
        : auth.user?.department_id ?? null;
}

async function ensureDepartments() {
    try {
        await departmentsStore.ensureLoaded();
        return true;
    } catch (error) {
        ElMessage.error(error.message);
        return false;
    }
}

async function openCreateDialog() {
    if (!(await ensureDepartments())) return;
    editingId.value = null;
    resetForm();
    dialogVisible.value = true;
    formRef.value?.clearValidate();
}

async function openEditDialog(employee) {
    if (!(await ensureDepartments())) return;
    editingId.value = employee.id;
    form.employee_no = employee.employee_no;
    form.username = employee.username;
    form.name = employee.name;
    form.role = employee.role;
    form.status = employee.status;
    form.department_id = employee.department_id ?? null;
    form.password = "";
    dialogVisible.value = true;
    formRef.value?.clearValidate();
}

function onRoleChange() {
    if (form.role === "general_admin") {
        form.department_id = null;
    } else if (!isAdmin.value) {
        form.department_id = auth.user?.department_id ?? null;
    }
}

async function submitForm() {
    const valid = await formRef.value?.validate().catch(() => false);
    if (!valid) return;

    const payload = {
        employee_no: form.employee_no.trim(),
        username: form.username.trim(),
        name: form.name.trim(),
        role: form.role,
        status: form.status,
        department_id:
            form.role === "general_admin" || !form.department_id
                ? null
                : Number(form.department_id),
    };

    submitting.value = true;
    try {
        if (editingId.value) {
            await updateEmployee(editingId.value, payload);
            ElMessage.success("员工信息已更新");
        } else {
            await createEmployee({ ...payload, password: form.password });
            ElMessage.success("员工已创建");
        }
        dialogVisible.value = false;
        departmentsStore.invalidate();
        await loadEmployees();
    } catch (error) {
        ElMessage.error(error.message);
    } finally {
        submitting.value = false;
    }
}

async function confirmDelete(employee) {
    try {
        await ElMessageBox.confirm(
            `确定删除员工「${employee.name}」吗？`,
            "删除确认",
            {
                type: "warning",
                confirmButtonText: "删除",
                cancelButtonText: "取消",
            }
        );
    } catch (error) {
        return;
    }

    try {
        await deleteEmployee(employee.id);
        ElMessage.success("员工已删除");
        departmentsStore.invalidate();
        await loadEmployees();
    } catch (error) {
        ElMessage.error(error.message);
    }
}

onMounted(() => {
    loadEmployees();
    window.addEventListener("app:refresh", loadEmployees);
});

onBeforeUnmount(() => {
    window.removeEventListener("app:refresh", loadEmployees);
});
</script>

<template>
    <section class="panel page-enter">
        <div class="panel-header">
            <div>
                <h3>员工档案</h3>
                <p class="panel-sub">{{ panelSub }}</p>
            </div>
            <button class="btn btn-ghost" type="button" @click="openCreateDialog">
                + 新建员工
            </button>
        </div>

        <div class="table-scroll">
            <el-table
                v-loading="loading"
                :data="employees"
                :empty-text="emptyText"
                class="employee-table"
            >
                <el-table-column prop="employee_no" label="工号" min-width="120" />
                <el-table-column prop="name" label="姓名" min-width="110" />
                <el-table-column label="部门" min-width="130">
                    <template #default="{ row }">
                        {{ row.department_name || "—" }}
                    </template>
                </el-table-column>
                <el-table-column label="角色" min-width="120">
                    <template #default="{ row }">
                        <span class="tag" :class="roleTagClass(row.role)">
                            {{ roleLabel(row.role) }}
                        </span>
                    </template>
                </el-table-column>
                <el-table-column label="状态" min-width="100">
                    <template #default="{ row }">
                        <span class="tag" :class="statusTagClass(row.status)">
                            {{ statusLabel(row.status) }}
                        </span>
                    </template>
                </el-table-column>
                <el-table-column label="操作" min-width="170" fixed="right">
                    <template #default="{ row }">
                        <div class="row-actions">
                            <button
                                v-if="canViewAttendance && isAttendanceSubject(row)"
                                class="btn btn-ghost btn-sm"
                                type="button"
                                @click="openAttendanceDrawer(row)"
                            >
                                个人考勤
                            </button>
                            <button
                                v-if="canEdit(row)"
                                class="btn btn-ghost btn-sm"
                                type="button"
                                @click="openEditDialog(row)"
                            >
                                编辑
                            </button>
                            <button
                                v-if="isAdmin"
                                class="btn btn-ghost btn-sm btn-danger"
                                type="button"
                                @click="confirmDelete(row)"
                            >
                                删除
                            </button>
                        </div>
                    </template>
                </el-table-column>
            </el-table>
        </div>

        <div class="panel-footer">
            <button class="btn btn-ghost btn-sm" type="button" @click="loadEmployees">
                刷新
            </button>
        </div>
    </section>

    <el-dialog
        v-model="dialogVisible"
        :title="dialogTitle"
        width="620px"
        class="employee-dialog"
        align-center
    >
        <el-form
            ref="formRef"
            :model="form"
            :rules="rules"
            label-position="top"
            @submit.prevent="submitForm"
        >
            <div class="form-grid">
                <el-form-item label="工号" prop="employee_no">
                    <el-input v-model="form.employee_no" maxlength="50" />
                </el-form-item>
                <el-form-item label="用户名" prop="username">
                    <el-input v-model="form.username" maxlength="50" />
                </el-form-item>
                <el-form-item label="姓名" prop="name">
                    <el-input v-model="form.name" maxlength="50" />
                </el-form-item>
                <el-form-item label="所属部门">
                    <el-select
                        v-model="form.department_id"
                        :disabled="departmentDisabled"
                        placeholder="不分配"
                        clearable
                    >
                        <el-option
                            v-for="department in departmentOptions"
                            :key="department.id"
                            :label="department.name"
                            :value="department.id"
                        />
                    </el-select>
                </el-form-item>
                <el-form-item label="角色">
                    <el-select v-model="form.role" @change="onRoleChange">
                        <el-option
                            v-for="option in roleOptions"
                            :key="option.value"
                            :label="option.label"
                            :value="option.value"
                        />
                    </el-select>
                </el-form-item>
                <el-form-item label="状态">
                    <el-select v-model="form.status">
                        <el-option label="在职" value="active" />
                        <el-option label="停用" value="inactive" />
                    </el-select>
                </el-form-item>
                <el-form-item
                    v-if="!editingId"
                    label="初始密码"
                    prop="password"
                    class="form-field-wide"
                >
                    <el-input
                        v-model="form.password"
                        type="password"
                        show-password
                        maxlength="128"
                        placeholder="至少 6 位"
                    />
                </el-form-item>
            </div>
        </el-form>

        <template #footer>
            <button
                class="btn btn-primary"
                type="button"
                :disabled="submitting"
                @click="submitForm"
            >
                <span>{{ editingId ? "保存修改" : "创建员工" }}</span>
                <span class="btn-shine"></span>
            </button>
            <button class="btn btn-ghost" type="button" @click="dialogVisible = false">
                取消
            </button>
        </template>
    </el-dialog>

    <el-drawer
        v-model="attendanceVisible"
        :title="`个人考勤 · ${attendanceEmployee?.name || ''}`"
        size="640px"
    >
        <div class="drawer-header">
            <el-date-picker
                v-model="attendanceMonth"
                type="month"
                value-format="YYYY-MM"
                :clearable="false"
                class="attendance-month"
                @change="loadAttendance"
            />
            <span class="status-pill">{{ attendanceEmployee?.employee_no || "—" }}</span>
        </div>

        <div class="hero-grid attendance-metrics">
            <article class="metric-card glass accent-cyan">
                <div class="metric-label"><span class="status-dot"></span>出勤率</div>
                <h3>{{ attendanceData ? `${attendanceData.summary.attendance_rate}%` : "—" }}</h3>
            </article>
            <article class="metric-card glass accent-violet">
                <div class="metric-label"><span class="status-dot"></span>出勤天数</div>
                <h3>{{ attendanceData ? attendanceData.summary.attended_days : "—" }}</h3>
            </article>
            <article class="metric-card glass accent-pink">
                <div class="metric-label"><span class="status-dot"></span>迟到 / 缺勤</div>
                <h3 v-if="attendanceData">
                    {{ attendanceData.summary.late_count }} / {{ attendanceData.summary.absent_days }}
                </h3>
                <h3 v-else>—</h3>
            </article>
        </div>

        <el-table
            v-loading="attendanceLoading"
            :data="attendanceData?.records || []"
            :empty-text="attendanceError || '暂无考勤记录'"
            class="attendance-drawer-table"
        >
            <el-table-column label="日期" min-width="100">
                <template #default="{ row }">{{ shortDate(row.work_date) }}</template>
            </el-table-column>
            <el-table-column label="上班" min-width="90">
                <template #default="{ row }">{{ shortTime(row.sign_in_at) }}</template>
            </el-table-column>
            <el-table-column label="下班" min-width="90">
                <template #default="{ row }">{{ shortTime(row.sign_out_at) }}</template>
            </el-table-column>
            <el-table-column label="状态" min-width="100">
                <template #default="{ row }">
                    <span class="tag" :class="attendanceStatusTag(row.status)">
                        {{ attendanceStatusLabel(row.status) }}
                    </span>
                </template>
            </el-table-column>
            <el-table-column label="工时" min-width="90">
                <template #default="{ row }">{{ formatHours(row.working_minutes) }}</template>
            </el-table-column>
        </el-table>
    </el-drawer>
</template>

<style scoped>
.table-scroll {
    width: 100%;
}

.drawer-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 16px;
}

.attendance-month {
    max-width: 180px;
}

.attendance-metrics {
    margin-bottom: 16px;
}

@media (max-width: 720px) {
    .table-scroll {
        overflow-x: auto;
    }

    .table-scroll :deep(.employee-table) {
        min-width: 780px;
    }
}
</style>
