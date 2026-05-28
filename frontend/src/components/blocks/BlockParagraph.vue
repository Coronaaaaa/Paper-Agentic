<template>
  <p class="block-paragraph">
    <template v-for="(seg, i) in segments" :key="i">
      <span v-if="seg.type === 'text'">{{ seg.text }}</span>
      <CitationBadge
        v-else-if="seg.type === 'citation'"
        :source-id="seg.sourceId"
        :index="seg.index"
        @hover="(sourceId, event) => emit('citation-hover', sourceId, event)"
        @leave="emit('citation-leave')"
        @click="(sourceId) => emit('citation-click', sourceId)"
      />
    </template>
  </p>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { BlockParagraph as BlockParagraphType } from '../../types/content'
import CitationBadge from '../CitationBadge.vue'

const props = defineProps<{
  block: BlockParagraphType
  /** 当前消息的全部来源列表，用于解析 citation index */
  sources: Array<{ id: string }>
}>()

const emit = defineEmits<{
  (e: 'citation-hover', sourceId: string, event: MouseEvent): void
  (e: 'citation-leave'): void
  (e: 'citation-click', sourceId: string): void
}>()

/** 将段落文本按 citation 标记拆分为文本段 + 引用标记 */
const segments = computed(() => {
  if (!props.block.citations || props.block.citations.length === 0) {
    return [{ type: 'text' as const, text: props.block.text }]
  }

  // 简化实现：在段落末尾附加所有引用标记
  const result: Array<{ type: 'text'; text: string } | { type: 'citation'; sourceId: string; index: number }> = [
    { type: 'text' as const, text: props.block.text + ' ' },
  ]

  props.block.citations.forEach((cit) => {
    const sourceIndex = props.sources.findIndex((s) => s.id === cit.sourceId)
    if (sourceIndex >= 0) {
      result.push({
        type: 'citation' as const,
        sourceId: cit.sourceId,
        index: sourceIndex,
      })
    }
  })

  return result
})
</script>

<style scoped>
.block-paragraph {
  margin: 0 0 14px 0;
  font-size: var(--font-size-body);
  line-height: 1.75;
  color: var(--color-text-primary);
  word-break: break-word;
}

.block-paragraph:last-child {
  margin-bottom: 0;
}
</style>
