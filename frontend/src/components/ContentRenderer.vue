<!-- 块级内容渲染器 —— 将 JSON blocks 转为结构化 DOM -->
<template>
  <div class="content-renderer">
    <template v-for="(block, index) in blocks" :key="index">
      <!-- 段落 -->
      <BlockParagraph
        v-if="block.type === 'paragraph'"
        :block="block"
        :sources="resolvedSources"
        @citation-hover="(sourceId, event) => emit('citation-hover', sourceId, event)"
        @citation-leave="emit('citation-leave')"
        @citation-click="(sourceId) => emit('citation-click', sourceId)"
      />

      <!-- 标题 -->
      <BlockHeading
        v-else-if="block.type === 'heading'"
        :block="block"
      />

      <!-- 列表 -->
      <BlockList
        v-else-if="block.type === 'list'"
        :block="block"
      />

      <!-- 引用段落 -->
      <BlockCitation
        v-else-if="block.type === 'citation_block'"
        :block="block"
        @citation-hover="(sourceId, event) => emit('citation-hover', sourceId, event)"
        @citation-leave="emit('citation-leave')"
        @citation-click="(sourceId) => emit('citation-click', sourceId)"
      />

      <!-- 表格 -->
      <BlockTable
        v-else-if="block.type === 'table'"
        :block="block"
      />

      <!-- 代码块 -->
      <BlockCode
        v-else-if="block.type === 'code'"
        :block="block"
      />

      <!-- 分隔线 -->
      <hr v-else-if="block.type === 'divider'" class="content-divider" />
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ContentBlock } from '../types/content'
import type { SourceCard } from '../types/source'
import BlockParagraph from './blocks/BlockParagraph.vue'
import BlockHeading from './blocks/BlockHeading.vue'
import BlockList from './blocks/BlockList.vue'
import BlockCitation from './blocks/BlockCitation.vue'
import BlockTable from './blocks/BlockTable.vue'
import BlockCode from './blocks/BlockCode.vue'

const props = defineProps<{
  blocks: ContentBlock[]
  sources: SourceCard[]
}>()

const emit = defineEmits<{
  (e: 'citation-hover', sourceId: string, event: MouseEvent): void
  (e: 'citation-leave'): void
  (e: 'citation-click', sourceId: string): void
}>()

/** 确保 sources 有 id 字段供 BlockParagraph 匹配 */
const resolvedSources = computed(() =>
  props.sources.map((s) => ({ id: s.id }))
)
</script>

<style scoped>
.content-renderer {
  width: 100%;
}

.content-divider {
  margin: 16px 0;
  border: none;
  border-top: 1px solid var(--color-border-subtle);
}
</style>
