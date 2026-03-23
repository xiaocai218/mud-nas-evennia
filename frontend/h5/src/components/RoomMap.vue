<script setup lang="ts">
import type { RoomMapColumn } from "@/types";

defineProps<{
  columns: RoomMapColumn[];
}>();
</script>

<template>
  <div class="room-map">
    <div v-for="(column, columnIndex) in columns" :key="columnIndex" class="room-map-column">
      <button
        v-for="node in column"
        :key="node.id"
        class="room-node"
        :class="{ active: node.active }"
      >
        {{ node.name }}
      </button>
    </div>
  </div>
</template>
