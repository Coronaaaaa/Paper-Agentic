<!-- AI 思考过程（可折叠），参考 DeepSeek 风格 -->
<template>
  <div v-if="thinking" class="thinking-section">
    <button class="thinking-toggle" type="button" @click="expanded = !expanded">
      <svg
        class="thinking-arrow"
        :class="{ 'thinking-arrow--expanded': expanded }"
        width="14" height="14"
        viewBox="0 0 24 24" fill="none" stroke="currentColor"
        stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
      >
        <polyline points="9 18 15 12 9 6" />
      </svg>
      <span class="thinking-label">
        已深度思考{{ timeText }}
      </span>
    </button>
    <div v-show="expanded" class="thinking-content">
      {{ thinking }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const props = defineProps<{
  thinking: string
  /** 思考耗时（毫秒） */
  timeMs: number
  /** 是否正在思考中（流式输出时展开） */
  isStreaming?: boolean
}>()

const expanded = ref(props.isStreaming ?? false)

const timeText = computed(() => {
  if (!props.timeMs) return ''
  const seconds = (props.timeMs / 1000).toFixed(1)
  return `（用时 ${seconds}s）`
})
</script>

<style scoped>
.thinking-section {
  margin-bottom: 16px;
}

.thinking-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  background: rgba(0, 0, 0, 0.03);
  border-radius: 8px;
  color: var(--color-text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: background 0.15s ease;
  width: auto;
}

.thinking-toggle:hover {
  background: rgba(0, 0, 0, 0.06);
}

.thinking-arrow {
  flex-shrink: 0;
  transition: transform 0.2s ease;
  color: var(--color-text-muted);
}

.thinking-arrow--expanded {
  transform: rotate(90deg);
}

.thinking-label {
  font-weight: 500;
}

.thinking-content {
  margin-top: 8px;
  padding: 10px 12px;
  background: rgba(0, 0, 0, 0.02);
  border-left: 2px solid var(--color-border-strong);
  border-radius: 0 8px 8px 0;
  font-size: 12.5px;
  color: var(--color-text-secondary);
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
