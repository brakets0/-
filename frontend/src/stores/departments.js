import { defineStore } from "pinia";
import { ref } from "vue";

import { listDepartments } from "@/api/departments";

export const useDepartmentsStore = defineStore("departments", () => {
    const items = ref([]);
    const loading = ref(false);
    const loaded = ref(false);

    // 员工/部门/班次页面新增或修改数据后调用，保证下拉与统计不会读到旧值。
    function invalidate() {
        loaded.value = false;
    }

    async function ensureLoaded({ force = false } = {}) {
        if (loaded.value && !force) return items.value;
        if (loading.value) return items.value;

        loading.value = true;
        try {
            items.value = await listDepartments();
            loaded.value = true;
        } finally {
            loading.value = false;
        }
        return items.value;
    }

    return { items, loading, loaded, invalidate, ensureLoaded };
});
