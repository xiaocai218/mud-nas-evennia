<script setup lang="ts">
import type { EntityCard } from "@/types";

defineProps<{
  entities: EntityCard[];
}>();

const emit = defineEmits<{
  open: [entity: EntityCard];
}>();
</script>

<template>
  <div class="entity-list">
    <button
      v-for="entity in entities"
      :key="entity.id"
      class="entity-card"
      @click="emit('open', entity)"
    >
      <div class="entity-card-left">
        <span v-if="entity.note" class="entity-note">{{ entity.note }}</span>
        <span>{{ entity.name }}</span>
      </div>
      <span class="entity-tag" :class="entity.type">{{ entity.tag }}</span>
    </button>
  </div>
</template>
