<template>
  <header class="topbar">
    <router-link to="/settings" class="topbar-btn" aria-label="设置与历史">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
        <line x1="3" y1="6" x2="21" y2="6" />
        <line x1="3" y1="12" x2="21" y2="12" />
        <line x1="3" y1="18" x2="21" y2="18" />
      </svg>
    </router-link>

    <span class="topbar-title">AIForScience</span>

    <div class="topbar-right">
      <button class="topbar-btn" type="button" aria-label="新建对话" @click="emit('new-chat')">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="16" />
          <line x1="8" y1="12" x2="16" y2="12" />
        </svg>
      </button>
    </div>
  </header>
</template>

<script setup lang="ts">
const emit = defineEmits<{
  (e: 'new-chat'): void
}>()
</script>

<style scoped>
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 44px;
  padding: 0 12px;
  background: var(--color-surface-card);
  border-bottom: 1px solid var(--color-border-subtle);
  flex-shrink: 0;
}

.topbar-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
  user-select: none;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 4px;
}

.topbar-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
  text-decoration: none;
}

.topbar-btn:hover {
  background: var(--color-surface-muted);
  color: var(--color-text-primary);
}
</style>
