<script setup>
defineProps({
    title: { type: String, required: true },
    subtitle: { type: String, default: "" },
});
</script>

<template>
    <section class="panel page-enter">
        <div class="panel-header">
            <h3>{{ title }}</h3>
            <span v-if="subtitle" class="panel-sub">{{ subtitle }}</span>
        </div>
        <slot />
    </section>
</template>
