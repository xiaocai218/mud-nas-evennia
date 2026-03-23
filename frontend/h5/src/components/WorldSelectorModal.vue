<script setup lang="ts">
import { computed, ref } from "vue";

import type { WorldCard } from "@/types";
import ModalPanel from "./ModalPanel.vue";
import SectionTabs from "./SectionTabs.vue";

const props = defineProps<{
  cards: WorldCard[];
}>();

const emit = defineEmits<{
  close: [];
}>();

const activeTab = ref("大世界");

const visibleCards = computed(() =>
  props.cards.filter((card) => {
    if (activeTab.value === "秘境") {
      return card.tag === "秘境";
    }
    if (activeTab.value === "活动") {
      return card.tag === "活动";
    }
    return card.tag === "大世界";
  }),
);
</script>

<template>
  <ModalPanel title="世界入口" @close="emit('close')">
    <SectionTabs :tabs="['大世界', '秘境', '活动']" :active="activeTab" @select="activeTab = $event" />
    <div class="search-box">搜索地图...</div>
    <div class="world-card-list">
      <div v-for="card in visibleCards" :key="card.id" class="world-card" :class="{ active: card.active }">
        <div class="world-card-title-row">
          <strong>{{ card.name }}</strong>
          <span>{{ card.realm }}</span>
        </div>
        <div class="world-card-meta">
          <span class="world-chip">{{ card.region }}</span>
        </div>
      </div>
    </div>
  </ModalPanel>
</template>
