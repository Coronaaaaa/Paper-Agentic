<template>
  <component :is="block.ordered ? 'ol' : 'ul'" class="block-list">
    <li v-for="(item, i) in block.items" :key="i" class="block-list-item">
      {{ item }}
    </li>
  </component>
</template>

<script setup lang="ts">
import type { BlockList as BlockListType } from '../../types/content'

defineProps<{
  block: BlockListType
}>()
</script>

<style scoped>
.block-list {
  margin: 0 0 14px 0;
  padding-left: 20px;
  color: var(--color-text-primary);
  line-height: 1.75;
}

.block-list-item {
  font-size: var(--font-size-body);
  margin-bottom: 4px;
}
</style>
