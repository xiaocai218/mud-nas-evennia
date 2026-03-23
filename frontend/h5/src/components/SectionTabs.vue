<script setup lang="ts">
defineProps<{
  tabs: string[];
  active: string;
}>();

const emit = defineEmits<{
  select: [key: string];
}>();
</script>

<template>
  <div class="section-tabs">
    <button
      v-for="tab in tabs"
      :key="tab"
      class="section-tab"
      :class="{ active: tab === active }"
      @click="emit('select', tab)"
    >
      {{ tab }}
    </button>
  </div>
</template>
