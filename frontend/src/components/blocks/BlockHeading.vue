<template>
  <component :is="tag" class="block-heading" :class="`block-heading--h${block.level}`">
    {{ block.text }}
  </component>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { BlockHeading as BlockHeadingType } from '../../types/content'

const props = defineProps<{
  block: BlockHeadingType
}>()

const tag = computed(() => `h${Math.min(props.block.level + 1, 6)}` as const)
</script>

<style scoped>
.block-heading {
  margin: 24px 0 10px 0;
  color: var(--color-text-primary);
  line-height: 1.4;
}

.block-heading:first-child {
  margin-top: 0;
}

.block-heading--h1 {
  font-size: 20px;
  font-weight: 700;
}

.block-heading--h2 {
  font-size: 18px;
  font-weight: 600;
}

.block-heading--h3 {
  font-size: 16px;
  font-weight: 600;
}

.block-heading--h4 {
  font-size: 15px;
  font-weight: 500;
}
</style>
