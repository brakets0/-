<script setup>
import { computed } from "vue";

const props = defineProps({
    name: { type: String, required: true },
    size: { type: Number, default: 18 },
});

const ICONS = {
    dashboard:
        '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
    attendance:
        '<circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15 14"/>',
    requests:
        '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><path d="M9 13h6"/><path d="M9 17h4"/>',
    employees:
        '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    departments:
        '<path d="M3 9l1.5-4a2 2 0 0 1 2-1H15l5 4v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M8 21v-7a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v7"/><path d="M3 9h18"/>',
    shifts:
        '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>',
    reports:
        '<line x1="12" y1="20" x2="12" y2="10"/><line x1="18" y1="20" x2="18" y2="4"/><line x1="6" y1="20" x2="6" y2="16"/><line x1="2" y1="20" x2="22" y2="20"/>',
    refresh:
        '<polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>',
    logout:
        '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>',
};

const markup = computed(() => {
    const body = ICONS[props.name] || "";
    return `<svg viewBox="0 0 24 24" width="${props.size}" height="${props.size}" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${body}</svg>`;
});
</script>

<template>
    <span class="nav-icon" aria-hidden="true" v-html="markup"></span>
</template>
