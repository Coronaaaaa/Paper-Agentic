<template>
  <div class="ai-message">
    <!-- 思考过程（可折叠） -->
    <ThinkingSection
      v-if="message.thinking"
      :thinking="message.thinking"
      :time-ms="message.thinkingTimeMs"
      :is-streaming="isStreaming"
    />

    <!-- 结构化内容 -->
    <ContentRenderer
      v-if="message.blocks.length > 0"
      :blocks="message.blocks"
      :sources="message.sources"
      @citation-hover="(sourceId, event) => emit('citation-hover', sourceId, event)"
      @citation-leave="emit('citation-leave')"
      @citation-click="(sourceId) => emit('citation-click', sourceId)"
    />
  </div>
</template>

<script setup lang="ts">
import type { AssistantMessage } from '../stores/conversation'
import ThinkingSection from './ThinkingSection.vue'
import ContentRenderer from './ContentRenderer.vue'

defineProps<{
  message: AssistantMessage
  isStreaming?: boolean
}>()

const emit = defineEmits<{
  (e: 'citation-hover', sourceId: string, event: MouseEvent): void
  (e: 'citation-leave'): void
  (e: 'citation-click', sourceId: string): void
}>()
</script>

<style scoped>
.ai-message {
  margin: 12px 0;
  max-width: 100%;
}
</style>
