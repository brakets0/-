<script setup>
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";

import {
    createBusinessTrip,
    createLeaveRequest,
    deleteBusinessTrip,
    deleteLeaveRequest,
    listBusinessTrips,
    listLeaveRequests,
    reviewBusinessTrip,
    reviewLeaveRequest,
} from "@/api/requests";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();

const rows = ref([]);
const loading = ref(false);
const errorMessage = ref("");
const typeFilter = ref("all");
const statusFilter = ref("all");

const dialogVisible = ref(false);
const submitting = ref(false);
const formRef = ref(null);
const form = reactive({
    type: "leave",
    leave_type: "事假",
    start_date: "",
    end_date: "",
    duration_days: 1,
    reason: "",
});

const STATUS_META = {
    pending: { label: "待审批", tag: "tag-warning" },
    approved: { label: "已通过", tag: "tag-success" },
    rejected: { label: "已驳回", tag: "tag-danger" },
};

const canReview = computed(() => auth.hasPermission("leave.review.department"));
const listSubtitle = computed(() =>
    canReview.value ? "本部门申请与本人员工申请" : "提交与查看本人的请假、外派申请"
);

const rules = {
    start_date: [{ required: true, message: "请选择开始日期", trigger: "change" }],
    end_date: [
        { required: true, message: "请选择结束日期", trigger: "change" },
        {
            validator: (rule, value, callback) => {
                if (value && form.start_date && value < form.start_date) {
                    callback(new Error("结束日期不能早于开始日期"));
                    return;
                }
                callback();
            },
            trigger: "change",
        },
    ],
};

function statusLabel(status) {
    return STATUS_META[status]?.label || status;
}

function statusTag(status) {
    return STATUS_META[status]?.tag || "tag-cyan";
}

function formatRange(row) {
    return `${row.start_date} ~ ${row.end_date}`;
}

async function load() {
    loading.value = true;
    errorMessage.value = "";
    const params = statusFilter.value === "all" ? {} : { status: statusFilter.value };
    try {
        const [leaves, trips] = await Promise.all([
            listLeaveRequests(params),
            listBusinessTrips(params),
        ]);
        const merged = [...leaves, ...trips].sort((a, b) =>
            String(b.created_at).localeCompare(String(a.created_at))
        );
        rows.value =
            typeFilter.value === "all"
                ? merged
                : merged.filter((item) => item.type === typeFilter.value);
    } catch (error) {
        rows.value = [];
        errorMessage.value = error.message;
    } finally {
        loading.value = false;
    }
}

function openDialog() {
    form.type = "leave";
    form.leave_type = "事假";
    form.start_date = "";
    form.end_date = "";
    form.duration_days = 1;
    form.reason = "";
    dialogVisible.value = true;
    formRef.value?.clearValidate();
}

async function submitForm() {
    const valid = await formRef.value?.validate().catch(() => false);
    if (!valid) return;
    const payload = {
        start_date: form.start_date,
        end_date: form.end_date,
        duration_days: Number(form.duration_days),
        reason: form.reason || null,
    };
    submitting.value = true;
    try {
        if (form.type === "leave") {
            await createLeaveRequest({ ...payload, leave_type: form.leave_type });
            ElMessage.success("请假申请已提交");
        } else {
            await createBusinessTrip(payload);
            ElMessage.success("外派申请已提交");
        }
        dialogVisible.value = false;
        await load();
    } catch (error) {
        ElMessage.error(error.message);
    } finally {
        submitting.value = false;
    }
}

async function review(row, status) {
    let note = null;
    if (status === "rejected") {
        try {
            const result = await ElMessageBox.prompt("请填写驳回原因", "驳回申请", {
                confirmButtonText: "确认驳回",
                cancelButtonText: "取消",
                inputPlaceholder: "可留空",
            });
            note = result.value || null;
        } catch (error) {
            return;
        }
    } else {
        try {
            await ElMessageBox.confirm(`通过「${row.employee_name}」的申请？`, "审批确认", {
                confirmButtonText: "通过",
                cancelButtonText: "取消",
            });
        } catch (error) {
            return;
        }
    }

    try {
        const payload = { status, review_note: note };
        if (row.type === "leave") {
            await reviewLeaveRequest(row.id, payload);
        } else {
            await reviewBusinessTrip(row.id, payload);
        }
        ElMessage.success("审批已提交");
        await load();
    } catch (error) {
        ElMessage.error(error.message);
    }
}

async function withdraw(row) {
    try {
        await ElMessageBox.confirm(`撤回「${row.type_label}」申请？`, "撤回确认", {
            confirmButtonText: "撤回",
            cancelButtonText: "取消",
        });
    } catch (error) {
        return;
    }

    try {
        if (row.type === "leave") {
            await deleteLeaveRequest(row.id);
        } else {
            await deleteBusinessTrip(row.id);
        }
        ElMessage.success("申请已撤回");
        await load();
    } catch (error) {
        ElMessage.error(error.message);
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
    <section class="panel page-enter">
        <div class="panel-header">
            <div>
                <h3>申请与审批</h3>
                <p class="panel-sub">{{ listSubtitle }}</p>
            </div>
            <button class="btn btn-ghost" type="button" @click="openDialog">
                + 新建申请
            </button>
        </div>

        <div class="filter-toolbar">
            <el-select v-model="typeFilter" class="filter-field" @change="load">
                <el-option label="全部类型" value="all" />
                <el-option label="请假" value="leave" />
                <el-option label="外派" value="trip" />
            </el-select>
            <el-select v-model="statusFilter" class="filter-field" @change="load">
                <el-option label="全部状态" value="all" />
                <el-option label="待审批" value="pending" />
                <el-option label="已通过" value="approved" />
                <el-option label="已驳回" value="rejected" />
            </el-select>
            <button class="btn btn-ghost" type="button" @click="load">刷新</button>
        </div>

        <div class="table-scroll">
            <el-table
                v-loading="loading"
                :data="rows"
                :empty-text="errorMessage || '暂无申请记录'"
                class="request-table"
            >
                <el-table-column prop="employee_name" label="申请人" min-width="110" />
                <el-table-column label="部门" min-width="120">
                    <template #default="{ row }">{{ row.department_name || "—" }}</template>
                </el-table-column>
                <el-table-column label="类型" min-width="100">
                    <template #default="{ row }">
                        <span class="tag" :class="row.type === 'leave' ? 'tag-cyan' : 'tag-violet'">
                            {{ row.type === "leave" ? row.type_label : "外派" }}
                        </span>
                    </template>
                </el-table-column>
                <el-table-column label="起止日期" min-width="200">
                    <template #default="{ row }">{{ formatRange(row) }}</template>
                </el-table-column>
                <el-table-column label="时长" min-width="90">
                    <template #default="{ row }">{{ row.duration_days }} 天</template>
                </el-table-column>
                <el-table-column label="状态" min-width="110">
                    <template #default="{ row }">
                        <span class="tag" :class="statusTag(row.status)">
                            {{ statusLabel(row.status) }}
                        </span>
                    </template>
                </el-table-column>
                <el-table-column label="事由" min-width="150">
                    <template #default="{ row }">{{ row.reason || "—" }}</template>
                </el-table-column>
                <el-table-column v-if="canReview" label="操作" min-width="180" fixed="right">
                    <template #default="{ row }">
                        <div
                            v-if="row.status === 'pending'"
                            class="row-actions approval-actions"
                        >
                            <button
                                class="btn btn-ghost btn-sm"
                                type="button"
                                @click="review(row, 'approved')"
                            >
                                通过
                            </button>
                            <button
                                class="btn btn-ghost btn-sm btn-danger"
                                type="button"
                                @click="review(row, 'rejected')"
                            >
                                驳回
                            </button>
                            <button
                                v-if="row.employee_id === auth.user?.id"
                                class="btn btn-ghost btn-sm btn-danger"
                                type="button"
                                @click="withdraw(row)"
                            >
                                撤回
                            </button>
                        </div>
                        <span v-else class="table-muted">{{ row.approver_name || "—" }}</span>
                    </template>
                </el-table-column>
                <el-table-column v-else label="操作" width="100" fixed="right">
                    <template #default="{ row }">
                        <button
                            v-if="row.status === 'pending'"
                            class="btn btn-ghost btn-sm btn-danger"
                            type="button"
                            @click="withdraw(row)"
                        >
                            撤回
                        </button>
                        <span v-else class="table-muted">—</span>
                    </template>
                </el-table-column>
            </el-table>
        </div>
    </section>

    <el-dialog v-model="dialogVisible" title="新建申请" width="560px" align-center>
        <el-form
            ref="formRef"
            :model="form"
            :rules="rules"
            label-position="top"
            @submit.prevent="submitForm"
        >
            <el-form-item label="申请类型">
                <el-radio-group v-model="form.type">
                    <el-radio value="leave">请假</el-radio>
                    <el-radio value="trip">外派</el-radio>
                </el-radio-group>
            </el-form-item>
            <el-form-item v-if="form.type === 'leave'" label="请假类型">
                <el-select v-model="form.leave_type" class="full-width">
                    <el-option label="事假" value="事假" />
                    <el-option label="年假" value="年假" />
                    <el-option label="病假" value="病假" />
                    <el-option label="调休" value="调休" />
                </el-select>
            </el-form-item>
            <div class="date-grid">
                <el-form-item label="开始日期" prop="start_date">
                    <el-date-picker
                        v-model="form.start_date"
                        type="date"
                        value-format="YYYY-MM-DD"
                        placeholder="开始日期"
                        class="full-width"
                    />
                </el-form-item>
                <el-form-item label="结束日期" prop="end_date">
                    <el-date-picker
                        v-model="form.end_date"
                        type="date"
                        value-format="YYYY-MM-DD"
                        placeholder="结束日期"
                        class="full-width"
                    />
                </el-form-item>
            </div>
            <el-form-item label="时长（天）">
                <el-input-number v-model="form.duration_days" :min="0.5" :max="30" :step="0.5" />
            </el-form-item>
            <el-form-item label="事由">
                <el-input
                    v-model="form.reason"
                    type="textarea"
                    :rows="3"
                    maxlength="500"
                    placeholder="可留空"
                />
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
                <span>提交申请</span>
                <span class="btn-shine"></span>
            </button>
        </template>
    </el-dialog>
</template>

<style scoped>
.filter-field {
    width: 100%;
    max-width: 200px;
}

.full-width {
    width: 100%;
}

.date-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
}

.request-table :deep(.el-form-item) {
    margin-bottom: 14px;
}

.table-scroll {
    width: 100%;
}

@media (max-width: 720px) {
    .date-grid {
        grid-template-columns: minmax(0, 1fr);
    }

    .table-scroll {
        overflow-x: auto;
    }

    .table-scroll :deep(.request-table) {
        min-width: 960px;
    }
}
</style>
