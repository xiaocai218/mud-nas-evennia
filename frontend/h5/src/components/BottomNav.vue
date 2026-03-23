<script setup lang="ts">
import type { BottomNavKey } from "@/types";

const props = defineProps<{
  active: BottomNavKey;
}>();

const emit = defineEmits<{
  select: [key: BottomNavKey];
}>();

const items: Array<{ key: BottomNavKey; label: string }> = [
  { key: "battle", label: "战况" },
  { key: "map", label: "地图" },
  { key: "secret", label: "秘境" },
  { key: "tower", label: "千层塔" },
  { key: "more", label: "更多" },
];
</script>

<template>
  <nav class="bottom-nav">
    <button
      v-for="item in items"
      :key="item.key"
      class="bottom-nav-item"
      :class="{ active: props.active === item.key }"
      @click="emit('select', item.key)"
    >
      <span class="bottom-nav-icon">◌</span>
      <span>{{ item.label }}</span>
    </button>
  </nav>
</template>
