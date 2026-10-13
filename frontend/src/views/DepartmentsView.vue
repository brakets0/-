<script setup>
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";

import {
    createDepartment,
    deleteDepartment,
    updateDepartment,
} from "@/api/departments";
import { listEmployees } from "@/api/employees";
import { useAuthStore } from "@/stores/auth";
import { useDepartmentsStore } from "@/stores/departments";

const auth = useAuthStore();
const departmentsStore = useDepartmentsStore();

const departments = ref([]);
const managers = ref([]);
const loading = ref(false);
const loadError = ref("");

const dialogVisible = ref(false);
const submitting = ref(false);
const editingId = ref(null);
const formRef = ref(null);
const form = reactive({ name: "", manager_user_id: null });

const assignVisible = ref(false);
const assignSubmitting = ref(false);
const assignTarget = ref(null);
const assignManagerId = ref(null);

const isAdmin = computed(() => auth.role === "general_admin");
const dialogTitle = computed(() => (editingId.value ? "编辑部门" : "新建部门"));
const emptyText = computed(() => loadError.value || "暂无部门");

const managerOptions = computed(() =>
    managers.value.map((manager) => ({
        value: manager.id,
        label: `${manager.name}（${manager.department_name || "未分配"}）`,
    }))
);

const rules = {
    name: [{ required: true, message: "请输入部门名称", trigger: "blur" }],
};

async function loadManagers() {
    try {
        const employees = await listEmployees();
        managers.value = employees.filter(
            (employee) => employee.role === "department_manager"
        );
    } catch (error) {
        managers.value = [];
        ElMessage.error(error.message);
    }
}

async function loadDepartments() {
    loading.value = true;
    loadError.value = "";
    try {
        departments.value = await departmentsStore.ensureLoaded({ force: true });
    } catch (error) {
        departments.value = [];
        loadError.value = error.message;
    } finally {
        loading.value = false;
    }
}

function managerLabel(department) {
    return department.manager_name || "未指定";
}

async function openCreateDialog() {
    editingId.value = null;
    form.name = "";
    form.manager_user_id = null;
    await loadManagers();
    dialogVisible.value = true;
    formRef.value?.clearValidate();
}

async function openEditDialog(department) {
    editingId.value = department.id;
    form.name = department.name;
    form.manager_user_id = department.manager_user_id ?? null;
    await loadManagers();
    dialogVisible.value = true;
    formRef.value?.clearValidate();
}

async function submitForm() {
    const valid = await formRef.value?.validate().catch(() => false);
    if (!valid) return;

    const payload = {
        name: form.name.trim(),
        manager_user_id: form.manager_user_id ? Number(form.manager_user_id) : null,
    };

    submitting.value = true;
    try {
        if (editingId.value) {
            await updateDepartment(editingId.value, payload);
            ElMessage.success("部门已更新");
        } else {
            await createDepartment(payload);
            ElMessage.success("部门已创建");
        }
        dialogVisible.value = false;
        departmentsStore.invalidate();
        await Promise.all([loadDepartments(), loadManagers()]);
    } catch (error) {
        ElMessage.error(error.message);
    } finally {
        submitting.value = false;
    }
}

async function openAssignDialog(department) {
    assignTarget.value = department;
    assignManagerId.value = department.manager_user_id ?? null;
    await loadManagers();
    assignVisible.value = true;
}

async function submitAssign() {
    if (!assignTarget.value) return;

    assignSubmitting.value = true;
    try {
        await updateDepartment(assignTarget.value.id, {
            manager_user_id: assignManagerId.value
                ? Number(assignManagerId.value)
                : null,
        });
        ElMessage.success("管理员已指派");
        assignVisible.value = false;
        departmentsStore.invalidate();
        await Promise.all([loadDepartments(), loadManagers()]);
    } catch (error) {
        ElMessage.error(error.message);
    } finally {
        assignSubmitting.value = false;
    }
}

async function confirmDelete(department) {
    try {
        await ElMessageBox.confirm(
            `确定删除部门「${department.name}」吗？`,
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
        await deleteDepartment(department.id);
        ElMessage.success("部门已删除");
        departmentsStore.invalidate();
        await loadDepartments();
    } catch (error) {
        ElMessage.error(error.message);
    }
}

async function reload() {
    await Promise.all([loadDepartments(), loadManagers()]);
}

onMounted(() => {
    reload();
    window.addEventListener("app:refresh", reload);
});

onBeforeUnmount(() => {
    window.removeEventListener("app:refresh", reload);
});
</script>

<template>
    <section class="panel page-enter">
        <div class="panel-header">
            <div>
                <h3>部门概览</h3>
                <p class="panel-sub">部门规模、负责人与默认班次数</p>
            </div>
            <button
                v-if="isAdmin"
                class="btn btn-ghost"
                type="button"
                @click="openCreateDialog"
            >
                + 新建部门
            </button>
        </div>

        <div class="table-scroll">
            <el-table
                v-loading="loading"
                :data="departments"
                :empty-text="emptyText"
                class="department-table"
            >
                <el-table-column prop="name" label="部门" min-width="140" />
                <el-table-column label="人数" min-width="90">
                    <template #default="{ row }">
                        {{ row.employee_count ?? 0 }}
                    </template>
                </el-table-column>
                <el-table-column label="负责人" min-width="130">
                    <template #default="{ row }">
                        {{ managerLabel(row) }}
                    </template>
                </el-table-column>
                <el-table-column label="班次数" min-width="90">
                    <template #default="{ row }">
                        {{ row.shift_count ?? 0 }}
                    </template>
                </el-table-column>
                <el-table-column v-if="isAdmin" label="操作" min-width="240" fixed="right">
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
                                class="btn btn-ghost btn-sm"
                                type="button"
                                @click="openAssignDialog(row)"
                            >
                                指派管理员
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
            <button class="btn btn-ghost btn-sm" type="button" @click="reload">
                刷新
            </button>
        </div>
    </section>

    <el-dialog
        v-model="dialogVisible"
        :title="dialogTitle"
        width="560px"
        align-center
    >
        <el-form
            ref="formRef"
            :model="form"
            :rules="rules"
            label-position="top"
            @submit.prevent="submitForm"
        >
            <el-form-item label="部门名称" prop="name">
                <el-input v-model="form.name" maxlength="50" />
            </el-form-item>
            <el-form-item label="部门管理员">
                <el-select
                    v-model="form.manager_user_id"
                    placeholder="未指定"
                    clearable
                    class="full-width"
                >
                    <el-option
                        v-for="option in managerOptions"
                        :key="option.value"
                        :label="option.label"
                        :value="option.value"
                    />
                </el-select>
            </el-form-item>
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
                <span>{{ editingId ? "保存修改" : "创建部门" }}</span>
                <span class="btn-shine"></span>
            </button>
        </template>
    </el-dialog>

    <el-dialog
        v-model="assignVisible"
        :title="assignTarget ? `指派管理员 · ${assignTarget.name}` : '指派管理员'"
        width="520px"
        align-center
    >
        <el-form label-position="top" @submit.prevent="submitAssign">
            <el-form-item label="管理员账号">
                <el-select
                    v-model="assignManagerId"
                    placeholder="取消指派"
                    clearable
                    class="full-width"
                >
                    <el-option
                        v-for="option in managerOptions"
                        :key="option.value"
                        :label="option.label"
                        :value="option.value"
                    />
                </el-select>
            </el-form-item>
        </el-form>

        <template #footer>
            <button class="btn btn-ghost" type="button" @click="assignVisible = false">
                取消
            </button>
            <button
                class="btn btn-primary"
                type="button"
                :disabled="assignSubmitting"
                @click="submitAssign"
            >
                <span>保存指派</span>
                <span class="btn-shine"></span>
            </button>
        </template>
    </el-dialog>
</template>

<style scoped>
.table-scroll {
    width: 100%;
}

.full-width {
    width: 100%;
}

@media (max-width: 720px) {
    .table-scroll {
        overflow-x: auto;
    }

    .table-scroll :deep(.department-table) {
        min-width: 700px;
    }
}
</style>
