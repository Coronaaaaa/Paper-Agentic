<!-- DeepSeek 风格的引用小药丸 -->
<template>
  <span
    class="cite-badge"
    :data-source-id="sourceId"
    @mouseenter="emit('hover', sourceId, $event)"
    @mouseleave="emit('leave')"
    @click.prevent="emit('click', sourceId)"
  >
    <span class="cite-spacer">-</span>
    <span class="cite-num">{{ index + 1 }}</span>
  </span>
</template>

<script setup lang="ts">
defineProps<{
  /** 来源 ID */
  sourceId: string
  /** 来源在列表中的序号（0-based） */
  index: number
}>()

const emit = defineEmits<{
  (e: 'hover', sourceId: string, event: MouseEvent): void
  (e: 'leave'): void
  (e: 'click', sourceId: string): void
}>()
</script>

<style scoped>
.cite-badge {
  display: inline-flex;
  position: relative;
  cursor: pointer;
  padding: 2px 4px;
  background: rgba(0, 0, 0, 0.06);
  border-radius: 4px;
  vertical-align: text-bottom;
  transition: background 0.15s ease;
  user-select: none;
}

.cite-badge:hover {
  background: rgba(0, 102, 204, 0.14);
}

.cite-spacer {
  opacity: 0;
  margin: 0 4px;
  font-size: 11px;
}

.cite-num {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  font-size: 11px;
  font-weight: 500;
  color: var(--color-text-secondary);
  line-height: 1;
}
</style>
