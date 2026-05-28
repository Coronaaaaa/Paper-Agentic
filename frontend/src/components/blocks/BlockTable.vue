<template>
  <div class="block-table-wrapper">
    <table class="block-table">
      <thead>
        <tr>
          <th v-for="(h, i) in block.headers" :key="i">{{ h }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, ri) in block.rows" :key="ri">
          <td v-for="(cell, ci) in row" :key="ci">{{ cell }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import type { BlockTable as BlockTableType } from '../../types/content'

defineProps<{
  block: BlockTableType
}>()
</script>

<style scoped>
.block-table-wrapper {
  margin: 0 0 14px 0;
  overflow-x: auto;
  border: 1px solid var(--color-border-subtle);
  border-radius: 8px;
}

.block-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.block-table th,
.block-table td {
  padding: 10px 14px;
  text-align: left;
  border-bottom: 1px solid var(--color-border-subtle);
}

.block-table th {
  background: var(--color-surface-muted);
  font-weight: 600;
  color: var(--color-text-primary);
}

.block-table td {
  color: var(--color-text-secondary);
}

.block-table tr:last-child td {
  border-bottom: none;
}
</style>
