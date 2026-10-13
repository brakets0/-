<script setup>
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";

import {
    createShift,
    deleteShift,
    listShifts,
    updateShift,
} from "@/api/shifts";
import { useAuthStore } from "@/stores/auth";
import { useDepartmentsStore } from "@/stores/departments";

const auth = useAuthStore();
const departmentsStore = useDepartmentsStore();

const shifts = ref([]);
const loading = ref(false);
const loadError = ref("");

const dialogVisible = ref(false);
const submitting = ref(false);
const editingId = ref(null);
const formRef = ref(null);

const WEEKDAYS = [
    { value: 1, label: "周一" },
    { value: 2, label: "周二" },
    { value: 3, label: "周三" },
    { value: 4, label: "周四" },
    { value: 5, label: "周五" },
    { value: 6, label: "周六" },
    { value: 7, label: "周日" },
];

const form = reactive({
    department_id: null,
    effective_from: "",
    work_start: "09:00",
    work_end: "18:00",
    break_start: null,
    break_end: null,
    workdays: [1, 2, 3, 4, 5],
});

const isAdmin = computed(() => auth.role === "general_admin");
const panelSub = computed(() =>
    isAdmin.value ? "部门默认班次与午休设置" : "仅本部门班次设置"
);
const dialogTitle = computed(() => (editingId.value ? "编辑班次" : "新建班次"));
const emptyText = computed(() => loadError.value || "暂无班次");

const departmentOptions = computed(() => {
    if (isAdmin.value) return departmentsStore.items;
    return departmentsStore.items.filter(
        (department) => department.id === auth.user?.department_id
    );
});

const departmentDisabled = computed(() => !isAdmin.value);

const rules = {
    department_id: [{ required: true, message: "请选择所属部门", trigger: "change" }],
    effective_from: [{ required: true, message: "请选择生效日期", trigger: "change" }],
    work_start: [{ required: true, message: "请选择上班时间", trigger: "change" }],
    work_end: [{ required: true, message: "请选择下班时间", trigger: "change" }],
    workdays: [
        {
            validator: (rule, value, callback) => {
                if (!value || !value.length) {
                    callback(new Error("请至少选择一天工作日"));
                    return;
                }
                callback();
            },
            trigger: "change",
        },
    ],
};

function weekdayLabel(value) {
    if (!value) return "—";
    return value
        .split(",")
        .map((day) => `周${"一二三四五六日"[Number(day) - 1] || day}`)
        .join(" · ");
}

function breakLabel(shift) {
    if (!shift.break_start || !shift.break_end) return "无午休";
    return `${shift.break_start.slice(0, 5)} - ${shift.break_end.slice(0, 5)}`;
}

function shortTime(value) {
    return value ? value.slice(0, 5) : "—";
}

async function loadShifts() {
    loading.value = true;
    loadError.value = "";
    departmentsStore.invalidate();
    try {
        shifts.value = await listShifts();
    } catch (error) {
        shifts.value = [];
        loadError.value = error.message;
    } finally {
        loading.value = false;
    }
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
    form.department_id = isAdmin.value
        ? null
        : auth.user?.department_id ?? null;
    form.effective_from = "";
    form.work_start = "09:00";
    form.work_end = "18:00";
    form.break_start = null;
    form.break_end = null;
    form.workdays = [1, 2, 3, 4, 5];
    dialogVisible.value = true;
    formRef.value?.clearValidate();
}

async function openEditDialog(shift) {
    if (!(await ensureDepartments())) return;
    editingId.value = shift.id;
    form.department_id = shift.department_id;
    form.effective_from = shift.effective_from;
    form.work_start = shortTime(shift.work_start);
    form.work_end = shortTime(shift.work_end);
    form.break_start = shift.break_start ? shortTime(shift.break_start) : null;
    form.break_end = shift.break_end ? shortTime(shift.break_end) : null;
    form.workdays = shift.workdays
        .split(",")
        .filter(Boolean)
        .map(Number)
        .sort((a, b) => a - b);
    dialogVisible.value = true;
    formRef.value?.clearValidate();
}

async function submitForm() {
    const valid = await formRef.value?.validate().catch(() => false);
    if (!valid) return;

    const payload = {
        department_id: Number(form.department_id),
        effective_from: form.effective_from,
        work_start: form.work_start,
        work_end: form.work_end,
        break_start: form.break_start || null,
        break_end: form.break_end || null,
        workdays: [...form.workdays].sort((a, b) => a - b).join(","),
    };

    submitting.value = true;
    try {
        if (editingId.value) {
            await updateShift(editingId.value, payload);
            ElMessage.success("班次已更新");
        } else {
            await createShift(payload);
            ElMessage.success("班次已创建");
        }
        dialogVisible.value = false;
        departmentsStore.invalidate();
        await loadShifts();
    } catch (error) {
        ElMessage.error(error.message);
    } finally {
        submitting.value = false;
    }
}

async function confirmDelete(shift) {
    try {
        await ElMessageBox.confirm("确定删除该班次吗？", "删除确认", {
            type: "warning",
            confirmButtonText: "删除",
            cancelButtonText: "取消",
        });
    } catch (error) {
        return;
    }

    try {
        await deleteShift(shift.id);
        ElMessage.success("班次已删除");
        departmentsStore.invalidate();
        await loadShifts();
    } catch (error) {
        ElMessage.error(error.message);
    }
}

onMounted(() => {
    loadShifts();
    window.addEventListener("app:refresh", loadShifts);
});

onBeforeUnmount(() => {
    window.removeEventListener("app:refresh", loadShifts);
});
</script>

<template>
    <section class="panel page-enter">
        <div class="panel-header">
            <div>
                <h3>班次管理</h3>
                <p class="panel-sub">{{ panelSub }}</p>
            </div>
            <button class="btn btn-ghost" type="button" @click="openCreateDialog">
                + 新建班次
            </button>
        </div>

        <div class="table-scroll">
            <el-table
                v-loading="loading"
                :data="shifts"
                :empty-text="emptyText"
                class="shift-table"
            >
                <el-table-column label="部门" min-width="130">
                    <template #default="{ row }">
                        {{ row.department_name || "—" }}
                    </template>
                </el-table-column>
                <el-table-column prop="effective_from" label="生效日期" min-width="130" />
                <el-table-column label="上班" min-width="90">
                    <template #default="{ row }">{{ shortTime(row.work_start) }}</template>
                </el-table-column>
                <el-table-column label="下班" min-width="90">
                    <template #default="{ row }">{{ shortTime(row.work_end) }}</template>
                </el-table-column>
                <el-table-column label="午休" min-width="140">
                    <template #default="{ row }">{{ breakLabel(row) }}</template>
                </el-table-column>
                <el-table-column label="工作日" min-width="220">
                    <template #default="{ row }">{{ weekdayLabel(row.workdays) }}</template>
                </el-table-column>
                <el-table-column label="操作" min-width="150" fixed="right">
                    <template #default="{ row }">
                        <div class="row-actions">
                            <button
                                class="btn btn-ghost btn-sm"
                                type="button"
                                @click="openEditDialog(row)"
                            >
                                编辑
                            </button>
                            <button
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
            <button class="btn btn-ghost btn-sm" type="button" @click="loadShifts">
                刷新
            </button>
        </div>
    </section>

    <el-dialog
        v-model="dialogVisible"
        :title="dialogTitle"
        width="660px"
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
                <el-form-item label="所属部门" prop="department_id">
                    <el-select
                        v-model="form.department_id"
                        :disabled="departmentDisabled"
                        placeholder="请选择部门"
                    >
                        <el-option
                            v-for="department in departmentOptions"
                            :key="department.id"
                            :label="department.name"
                            :value="department.id"
                        />
                    </el-select>
                </el-form-item>
                <el-form-item label="生效日期" prop="effective_from">
                    <el-date-picker
                        v-model="form.effective_from"
                        type="date"
                        value-format="YYYY-MM-DD"
                        placeholder="选择日期"
                    />
                </el-form-item>
                <el-form-item label="上班时间" prop="work_start">
                    <el-time-picker
                        v-model="form.work_start"
                        value-format="HH:mm"
                        format="HH:mm"
                        placeholder="09:00"
                    />
                </el-form-item>
                <el-form-item label="下班时间" prop="work_end">
                    <el-time-picker
                        v-model="form.work_end"
                        value-format="HH:mm"
                        format="HH:mm"
                        placeholder="18:00"
                    />
                </el-form-item>
                <el-form-item label="午休开始">
                    <el-time-picker
                        v-model="form.break_start"
                        value-format="HH:mm"
                        format="HH:mm"
                        placeholder="可留空"
                        clearable
                    />
                </el-form-item>
                <el-form-item label="午休结束">
                    <el-time-picker
                        v-model="form.break_end"
                        value-format="HH:mm"
                        format="HH:mm"
                        placeholder="可留空"
                        clearable
                    />
                </el-form-item>
                <el-form-item
                    label="工作日"
                    prop="workdays"
                    class="form-field-wide"
                >
                    <el-checkbox-group v-model="form.workdays">
                        <el-checkbox
                            v-for="day in WEEKDAYS"
                            :key="day.value"
                            :value="day.value"
                            :label="day.label"
                        />
                    </el-checkbox-group>
                </el-form-item>
            </div>
        </el-form>

        <template #footer>
            <button class="btn btn-ghost" type="button" @click="dialogVisible = false">
                取消
            </button>
            <button
                class="btn btn-primary"
                type="button"
                :disabled="submitting"
                @click="submitForm"
            >
                <span>{{ editingId ? "保存修改" : "创建班次" }}</span>
                <span class="btn-shine"></span>
            </button>
        </template>
    </el-dialog>
</template>

<style scoped>
.table-scroll {
    width: 100%;
}

@media (max-width: 720px) {
    .table-scroll {
        overflow-x: auto;
    }

    .table-scroll :deep(.shift-table) {
        min-width: 900px;
    }
}
</style>
