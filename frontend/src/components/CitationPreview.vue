<!-- 引用悬停预览卡片 -->
<template>
  <Teleport to="body">
    <div
      v-if="visible && source"
      class="cite-preview"
      :style="positionStyle"
      @mouseenter="emit('preview-enter')"
      @mouseleave="emit('preview-leave')"
    >
      <div class="cite-preview-header">
        <span class="cite-preview-title">{{ source.title }}</span>
        <span v-if="source.import_time" class="cite-preview-time">{{ formatTime(source.import_time) }}</span>
      </div>
      <div v-if="source.page || source.section" class="cite-preview-meta">
        <span v-if="source.page">第 {{ source.page }} 页</span>
        <span v-if="source.section">· {{ source.section }}</span>
      </div>
      <div class="cite-preview-divider"></div>
      <div class="cite-preview-excerpt">{{ source.content || '暂无摘要' }}</div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { SourceCard } from '../types/source'

const props = defineProps<{
  visible: boolean
  source: SourceCard | null
  x: number
  y: number
}>()

const emit = defineEmits<{
  (e: 'preview-enter'): void
  (e: 'preview-leave'): void
}>()

const positionStyle = computed(() => ({
  left: `${props.x + 12}px`,
  top: `${props.y - 12}px`,
  transform: 'translateY(-100%)',
}))

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
.cite-preview {
  position: fixed;
  z-index: 1000;
  width: 320px;
  max-height: 200px;
  background: var(--color-surface-card);
  border: 1px solid var(--color-border-subtle);
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  padding: 14px 16px;
  overflow: hidden;
  pointer-events: auto;
}

.cite-preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.cite-preview-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 200px;
}

.cite-preview-time {
  font-size: 11px;
  color: var(--color-text-muted);
  flex-shrink: 0;
  margin-left: 8px;
}

.cite-preview-meta {
  font-size: 11px;
  color: var(--color-text-secondary);
  margin-bottom: 8px;
}

.cite-preview-divider {
  height: 1px;
  background: var(--color-border-subtle);
  margin-bottom: 8px;
}

.cite-preview-excerpt {
  font-size: 12px;
  color: var(--color-text-secondary);
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
