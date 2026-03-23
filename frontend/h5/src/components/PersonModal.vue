<script setup lang="ts">
import { computed, ref } from "vue";

import type { EntityCard } from "@/types";
import ModalPanel from "./ModalPanel.vue";
import SectionTabs from "./SectionTabs.vue";

const props = defineProps<{
  entity: EntityCard;
}>();

const emit = defineEmits<{
  close: [];
}>();

const tabs = computed(() => {
  if (props.entity.type === "npc") {
    return ["信息", "描述"];
  }
  return ["信息", "属性"];
});

const activeTab = ref("信息");
</script>

<template>
  <ModalPanel :title="entity.name" @close="emit('close')">
    <div class="person-head">
      <div class="person-avatar">{{ entity.type === "npc" ? "NPC" : "玩家" }}</div>
      <div class="person-meta">
        <div class="person-line">
          <span class="person-chip" :class="entity.type">{{ entity.tag }}</span>
          <strong>{{ entity.title }} {{ entity.name }}</strong>
        </div>
        <p class="person-sub">性别：{{ entity.gender || "未知" }} · 境界：{{ entity.realm || "未定" }}</p>
      </div>
    </div>
    <SectionTabs :tabs="tabs" :active="activeTab" @select="activeTab = $event" />
    <div v-if="activeTab === '信息'" class="info-grid">
      <div v-for="stat in entity.stats || []" :key="stat.label" class="metric-card">
        <span class="metric-label">{{ stat.label }}</span>
        <span class="metric-value">{{ stat.value }}</span>
      </div>
    </div>
    <div v-else class="description-card">
      {{ entity.desc || "暂无描述。" }}
    </div>
    <div class="modal-actions">
      <button v-for="action in entity.actions || []" :key="action" class="secondary-button">
        {{ action }}
      </button>
    </div>
  </ModalPanel>
</template>
