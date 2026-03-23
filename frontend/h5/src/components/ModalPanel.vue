<script setup lang="ts">
defineProps<{
  title: string;
}>();

const emit = defineEmits<{
  close: [];
}>();
</script>

<template>
  <div class="modal-backdrop" @click.self="emit('close')">
    <div class="modal-panel">
      <div class="modal-header">
        <h3>{{ title }}</h3>
        <button class="modal-close" @click="emit('close')">×</button>
      </div>
      <div class="modal-body">
        <slot />
      </div>
    </div>
  </div>
</template>
