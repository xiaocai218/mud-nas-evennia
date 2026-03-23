<script setup lang="ts">
import { ref } from "vue";

const emit = defineEmits<{
  submit: [payload: { username: string; password: string }];
}>();

defineProps<{
  loading: boolean;
  errorText: string;
}>();

const username = ref("");
const password = ref("");
</script>

<template>
  <div class="auth-shell">
    <div class="auth-card">
      <div class="auth-logo">九州群修</div>
      <h1>H5 登录</h1>
      <p>当前阶段已接入真实账号登录和角色选择。</p>
      <div class="auth-form">
        <input v-model="username" class="auth-input" placeholder="输入账号" />
        <input v-model="password" class="auth-input" type="password" placeholder="输入密码" />
        <p v-if="errorText" class="auth-error">{{ errorText }}</p>
        <button
          class="primary-button auth-button"
          :disabled="loading || !username || !password"
          @click="emit('submit', { username, password })"
        >
          {{ loading ? "登录中..." : "登录" }}
        </button>
      </div>
    </div>
  </div>
</template>
