<template>
  <section class="source-panel" v-if="sources.length > 0">
    <div class="source-panel-header">
      <span class="source-panel-title">引用来源</span>
      <span class="source-panel-count">{{ sources.length }} 篇</span>
    </div>
    <div class="source-panel-grid">
      <button
        v-for="source in sources"
        :key="source.id"
        class="source-panel-card"
        type="button"
        @click="emit('open-source', source)"
      >
        <div class="source-card-title">{{ source.title }}</div>
        <div class="source-card-meta">
          <span v-if="source.page">第 {{ source.page }} 页</span>
          <span v-if="source.import_time" class="source-card-time">{{ formatTime(source.import_time) }}</span>
        </div>
        <div v-if="source.content" class="source-card-excerpt">
          "{{ source.content.slice(0, 80) }}{{ source.content.length > 80 ? '...' : '' }}"
        </div>
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { SourceCard } from '../types/source'

defineProps<{
  sources: SourceCard[]
}>()

const emit = defineEmits<{
  (e: 'open-source', source: SourceCard): void
}>()

function formatTime(iso: string): string {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  } catch {
    return ''
  }
}
</script>

<style scoped>
.source-panel {
  margin-top: 8px;
  padding: 14px 16px;
  background: var(--color-surface-card);
  border: 1px solid var(--color-border-subtle);
  border-radius: 12px;
}

.source-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.source-panel-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.source-panel-count {
  font-size: 11px;
  color: var(--color-text-muted);
}

.source-panel-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 8px;
}

.source-panel-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  background: var(--color-surface-base);
  border: 1px solid var(--color-border-subtle);
  border-radius: 10px;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.source-panel-card:hover {
  border-color: rgba(0, 102, 204, 0.3);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.source-card-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.source-card-meta {
  display: flex;
  gap: 8px;
  font-size: 11px;
  color: var(--color-text-muted);
}

.source-card-excerpt {
  font-size: 11px;
  color: var(--color-text-secondary);
  line-height: 1.5;
  font-style: italic;
}
</style>
