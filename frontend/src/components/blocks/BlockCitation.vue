<!-- 引用段落：左边框 + 末尾小圆点标记 -->
<template>
  <div class="block-citation">
    <p class="block-citation-text">
      {{ block.text }}
      <span
        v-for="(sourceId, i) in block.sourceIds"
        :key="sourceId"
        class="block-citation-dot"
        :data-source-id="sourceId"
        @mouseenter="emit('citation-hover', sourceId, $event)"
        @mouseleave="emit('citation-leave')"
        @click="emit('citation-click', sourceId)"
      >{{ i < block.sourceIds.length - 1 ? '· ' : '·' }}</span>
    </p>
  </div>
</template>

<script setup lang="ts">
import type { BlockCitationText } from '../../types/content'

defineProps<{
  block: BlockCitationText
}>()

const emit = defineEmits<{
  (e: 'citation-hover', sourceId: string, event: MouseEvent): void
  (e: 'citation-leave'): void
  (e: 'citation-click', sourceId: string): void
}>()
</script>

<style scoped>
.block-citation {
  position: relative;
  padding-left: 12px;
  margin: 0 0 14px 0;
  border-left: 3px solid rgba(0, 102, 204, 0.3);
}

.block-citation-text {
  font-size: var(--font-size-body);
  line-height: 1.75;
  color: var(--color-text-primary);
  margin: 0;
}

.block-citation-dot {
  display: inline;
  color: var(--color-text-muted);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: color 0.15s ease;
  user-select: none;
}

.block-citation-dot:hover {
  color: var(--color-accent);
}
</style>
