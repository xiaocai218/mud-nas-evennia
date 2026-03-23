<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import BottomNav from "@/components/BottomNav.vue";
import CharacterSelectModal from "@/components/CharacterSelectModal.vue";
import EntityList from "@/components/EntityList.vue";
import LoginPanel from "@/components/LoginPanel.vue";
import PersonModal from "@/components/PersonModal.vue";
import RoomMap from "@/components/RoomMap.vue";
import SectionTabs from "@/components/SectionTabs.vue";
import SystemGrid from "@/components/SystemGrid.vue";
import TopBar from "@/components/TopBar.vue";
import WorldSelectorModal from "@/components/WorldSelectorModal.vue";
import { featureEntries, roomEntities, roomMap, topResources, worldCards } from "@/mocks/world";
import { bootstrap, listCharacters, login, selectCharacter } from "@/services/gameClient";
import type { BottomNavKey, CharacterSummary, EntityCard } from "@/types";

const activeNav = ref<BottomNavKey>("map");
const activeMapTab = ref("地图");
const activeBattleTab = ref("综合");
const selectedEntity = ref<EntityCard | null>(null);
const worldSelectorOpen = ref(false);
const authLoading = ref(false);
const authErrorText = ref("");
const characters = ref<CharacterSummary[]>([]);
const activeCharacterId = ref<number | null>(null);
const isAuthenticated = ref(false);
const useMockData = ref(true);

const roomSummary = ref({
  title: "药草铺",
  area: "青云村",
  desc: "空气中弥漫着草药的清香，药婆婆正在整理各种药材。",
  date: "10月29日",
  weather: "西时 阴",
  era: "末法纪元1007年",
});

const battleMessages = [
  "[世界] 成就精英 xumi: 最后一次",
];

const currentContent = computed(() => activeNav.value);
const showCharacterSelect = computed(() => isAuthenticated.value && !activeCharacterId.value && characters.value.length > 0);
const currentResources = computed(() => topResources);

async function refreshCharacterState() {
  try {
    const response = await listCharacters();
    isAuthenticated.value = true;
    useMockData.value = false;
    characters.value = response.payload.characters;
    activeCharacterId.value = response.payload.active_character_id;
    if (activeCharacterId.value) {
      await hydrateFromBootstrap();
    }
  } catch {
    useMockData.value = true;
  }
}

async function hydrateFromBootstrap() {
  try {
    const response = await bootstrap();
    const payload = response.payload as {
      character?: { name?: string; copper?: number };
      position?: { area?: { key?: string }; room?: { key?: string; desc?: string } };
    };
    roomSummary.value = {
      ...roomSummary.value,
      title: payload.position?.room?.key || roomSummary.value.title,
      area: payload.position?.area?.key || roomSummary.value.area,
      desc: payload.position?.room?.desc || roomSummary.value.desc,
    };
  } catch {
    useMockData.value = true;
  }
}

async function handleLogin(payload: { username: string; password: string }) {
  authLoading.value = true;
  authErrorText.value = "";
  try {
    const response = await login(payload.username, payload.password);
    isAuthenticated.value = true;
    useMockData.value = false;
    characters.value = response.payload.characters;
    activeCharacterId.value = response.payload.active_character_id;
    if (activeCharacterId.value) {
      await hydrateFromBootstrap();
    }
  } catch (error) {
    const message =
      typeof error === "object" && error && "error" in error
        ? (error as { error?: { message?: string } }).error?.message
        : "";
    authErrorText.value = message || "登录失败，当前仍可继续查看 mock 页面。";
    useMockData.value = true;
  } finally {
    authLoading.value = false;
  }
}

async function handleSelectCharacter(characterId: number) {
  authLoading.value = true;
  authErrorText.value = "";
  try {
    const response = await selectCharacter(characterId);
    activeCharacterId.value = response.payload.active_character_id;
    await hydrateFromBootstrap();
  } catch (error) {
    const message =
      typeof error === "object" && error && "error" in error
        ? (error as { error?: { message?: string } }).error?.message
        : "";
    authErrorText.value = message || "角色激活失败。";
  } finally {
    authLoading.value = false;
  }
}

onMounted(() => {
  void refreshCharacterState();
});
</script>

<template>
  <div class="app-shell">
    <TopBar :resources="currentResources" />

    <main class="page-shell">
      <template v-if="currentContent === 'map'">
        <SectionTabs :tabs="['地图', '房间']" :active="activeMapTab" @select="activeMapTab = $event" />

        <section class="room-summary-card">
          <div class="room-title-row">
            <div>
              <h1>{{ roomSummary.title }}</h1>
              <p>{{ roomSummary.desc }}</p>
            </div>
            <strong>{{ roomSummary.area }}</strong>
          </div>
        </section>

        <template v-if="activeMapTab === '地图'">
          <RoomMap :columns="roomMap" />
          <button class="floating-skill-button">技</button>
        </template>

        <template v-else>
          <section class="room-meta-bar">
            <span>{{ roomSummary.era }}</span>
            <span>{{ roomSummary.date }}</span>
            <span>{{ roomSummary.weather }}</span>
          </section>
          <EntityList :entities="roomEntities" @open="selectedEntity = $event" />
          <button class="floating-skill-button">技</button>
        </template>
      </template>

      <template v-else-if="currentContent === 'battle'">
        <section class="battle-hero-card">
          <h2>{{ roomSummary.title }}</h2>
          <strong>{{ roomSummary.area }}</strong>
          <p>{{ roomSummary.desc }}</p>
        </section>
        <SectionTabs :tabs="['综合', '世界', '队伍', '宗门']" :active="activeBattleTab" @select="activeBattleTab = $event" />
        <section class="battle-feed-card">
          <div class="battle-online-bar">
            <span>在线 183</span>
            <button class="ghost-icon-button" @click="worldSelectorOpen = true">图</button>
            <button class="ghost-icon-button">线</button>
          </div>
          <div class="message-list">
            <p v-for="message in battleMessages" :key="message">{{ message }}</p>
          </div>
          <div class="chat-compose">
            <div class="chat-input">绑定手机号后才可在聊天频道发言...</div>
            <button class="primary-button small">绑定手机号</button>
          </div>
        </section>
      </template>

      <template v-else-if="currentContent === 'more'">
        <section class="more-summary-card">
          <div>
            <strong>功能总览</strong>
            <p>按当前 H5 视觉规范，系统入口统一收敛到卡片网格。</p>
          </div>
        </section>
        <SystemGrid :items="featureEntries" />
      </template>

      <template v-else-if="currentContent === 'secret'">
        <section class="placeholder-page">
          <h2>秘境入口</h2>
          <p>下一阶段接秘境列表和进入详情弹窗。</p>
          <button class="primary-button" @click="worldSelectorOpen = true">查看秘境列表</button>
        </section>
      </template>

      <template v-else>
        <section class="placeholder-page">
          <h2>千层塔</h2>
          <p>下一阶段接入塔层详情、排行和开始挑战入口。</p>
          <button class="primary-button">开始登塔</button>
        </section>
      </template>
    </main>

    <BottomNav :active="activeNav" @select="activeNav = $event" />

    <LoginPanel
      v-if="!isAuthenticated && useMockData"
      :loading="authLoading"
      :error-text="authErrorText"
      @submit="handleLogin"
    />
    <CharacterSelectModal
      v-if="showCharacterSelect"
      :characters="characters"
      :loading="authLoading"
      @select="handleSelectCharacter"
    />
    <PersonModal v-if="selectedEntity" :entity="selectedEntity" @close="selectedEntity = null" />
    <WorldSelectorModal v-if="worldSelectorOpen" :cards="worldCards" @close="worldSelectorOpen = false" />
  </div>
</template>
