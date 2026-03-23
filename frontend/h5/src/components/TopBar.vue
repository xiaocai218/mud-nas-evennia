<script setup lang="ts">
import type { ResourcePill } from "@/types";

defineProps<{
  resources: ResourcePill[];
}>();
</script>

<template>
  <header class="topbar">
    <div class="avatar-block">
      <div class="avatar-logo">修</div>
    </div>
    <div class="resource-row">
      <div v-for="item in resources" :key="item.label" class="pill">
        <span class="pill-icon">{{ item.icon }}</span>
        <span class="pill-value">{{ item.value }}</span>
      </div>
    </div>
    <div class="quick-actions">
      <button v-for="action in ['签', '邮', '设', '刷']" :key="action" class="icon-button">
        {{ action }}
      </button>
    </div>
  </header>
</template>
