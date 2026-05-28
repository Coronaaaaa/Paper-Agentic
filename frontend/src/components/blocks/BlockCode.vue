<template>
  <div class="block-code-wrapper">
    <div class="block-code-header">
      <span class="block-code-lang">{{ block.language || 'code' }}</span>
    </div>
    <pre class="block-code-pre"><code>{{ block.code }}</code></pre>
  </div>
</template>

<script setup lang="ts">
import type { BlockCode as BlockCodeType } from '../../types/content'

defineProps<{
  block: BlockCodeType
}>()
</script>

<style scoped>
.block-code-wrapper {
  margin: 0 0 14px 0;
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid var(--color-border-subtle);
}

.block-code-header {
  display: flex;
  align-items: center;
  padding: 6px 14px;
  background: var(--color-surface-muted);
  border-bottom: 1px solid var(--color-border-subtle);
}

.block-code-lang {
  font-size: 11px;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.block-code-pre {
  margin: 0;
  padding: 14px 16px;
  overflow-x: auto;
  font-size: 13px;
  line-height: 1.6;
  font-family: "Cascadia Code", "Fira Code", "JetBrains Mono", Consolas, monospace;
}

.block-code-pre code {
  color: var(--color-text-primary);
  white-space: pre;
}
</style>
