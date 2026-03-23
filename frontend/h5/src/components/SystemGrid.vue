<script setup lang="ts">
import type { FeatureEntry } from "@/types";

defineProps<{
  items: FeatureEntry[];
}>();
</script>

<template>
  <div class="system-grid">
    <button v-for="entry in items" :key="entry.id" class="system-card">
      <span class="system-icon">▢</span>
      <span class="system-label">{{ entry.label }}</span>
      <span v-if="entry.badge" class="system-badge">{{ entry.badge }}</span>
    </button>
  </div>
</template>
