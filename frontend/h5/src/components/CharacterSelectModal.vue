<script setup lang="ts">
import ModalPanel from "./ModalPanel.vue";

defineProps<{
  characters: Array<{ id: number; key: string; realm: string }>;
  loading: boolean;
}>();

const emit = defineEmits<{
  select: [characterId: number];
}>();
</script>

<template>
  <ModalPanel title="选择角色">
    <div class="character-select-list">
      <button
        v-for="character in characters"
        :key="character.id"
        class="character-select-card"
        :disabled="loading"
        @click="emit('select', character.id)"
      >
        <strong>{{ character.key }}</strong>
        <span>{{ character.realm }}</span>
      </button>
    </div>
  </ModalPanel>
</template>
