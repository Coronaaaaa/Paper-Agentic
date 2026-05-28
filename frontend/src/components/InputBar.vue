<template>
  <div class="input-bar">
    <!-- 文献选择指示条 -->
    <div v-if="selectedPaperCount > 0 || dragActive" class="input-context-bar">
      <span v-if="selectedPaperCount > 0" class="paper-count">
        已选择 {{ selectedPaperCount }} 篇文献
        <button class="paper-clear-btn" type="button" @click="emit('clear-papers')">×</button>
      </span>
      <span v-if="dragActive" class="drop-hint">释放以上传 PDF</span>
    </div>

    <!-- 输入框区域 -->
    <div
      class="input-wrapper"
      :class="{ 'input-wrapper--drag': dragActive }"
      @dragover.prevent="dragActive = true"
      @dragleave.prevent="dragActive = false"
      @drop.prevent="handleDrop"
    >
      <textarea
        ref="textareaRef"
        v-model="text"
        class="input-textarea"
        :placeholder="placeholder"
        :disabled="isBusy"
        :rows="1"
        @input="autoResize"
        @keydown="handleKeydown"
      />

      <!-- 发送按钮 -->
      <button
        class="send-btn"
        :class="{ 'send-btn--active': canSend, 'send-btn--busy': isBusy }"
        type="button"
        :disabled="!canSend && !isBusy"
        @click="handleSend"
        :aria-label="isBusy ? '处理中' : '发送'"
      >
        <svg v-if="!isBusy" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="12" y1="19" x2="12" y2="5" />
          <polyline points="5 12 12 5 19 12" />
        </svg>
        <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="6" y="6" width="12" height="12" rx="1" />
        </svg>
      </button>
    </div>

    <!-- 底部工具栏 -->
    <div class="input-toolbar">
      <div class="input-toolbar-left">
        <!-- 上传 PDF -->
        <button
          class="toolbar-btn"
          type="button"
          @click="triggerUpload"
          aria-label="上传 PDF"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="12" y1="18" x2="12" y2="12" />
            <line x1="9" y1="15" x2="15" y2="15" />
          </svg>
        </button>
        <input
          ref="fileInputRef"
          type="file"
          accept=".pdf"
          class="hidden-input"
          @change="handleFileSelect"
        >

        <!-- 文献选择按钮 -->
        <button
          class="toolbar-btn"
          type="button"
          @click="emit('toggle-papers')"
          aria-label="选择文献"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M4 19.5A2.5 2.5 0 016.5 17H20" />
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z" />
          </svg>
        </button>
      </div>

      <div class="input-toolbar-right">
        <span class="char-count">{{ text.length }} / 5000</span>

        <!-- 模型选择器 -->
        <ModelSelector
          :open="modelPanelOpen"
          @toggle="emit('toggle-model')"
          @close="emit('close-model')"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import ModelSelector from './ModelSelector.vue'

const props = defineProps<{
  isBusy: boolean
  modelPanelOpen: boolean
  selectedPaperCount: number
}>()

const emit = defineEmits<{
  (e: 'send', text: string): void
  (e: 'upload-pdf', file: File): void
  (e: 'toggle-papers'): void
  (e: 'clear-papers'): void
  (e: 'toggle-model'): void
  (e: 'close-model'): void
}>()

const text = ref('')
const textareaRef = ref<HTMLTextAreaElement>()
const fileInputRef = ref<HTMLInputElement>()
const dragActive = ref(false)

const placeholder = '输入你的问题，或直接从 WPS 中选中文字提问'
const canSend = computed(() => text.value.trim().length > 0 && !props.isBusy)

function autoResize() {
  nextTick(() => {
    const el = textareaRef.value
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 150)}px`
  })
}

function handleKeydown(e: KeyboardEvent) {
  const nativeEvent = e as KeyboardEvent & { isComposing?: boolean; keyCode?: number }
  if (nativeEvent.isComposing || nativeEvent.keyCode === 229) return
  if (e.key !== 'Enter' || e.shiftKey) return
  e.preventDefault()
  handleSend()
}

function handleSend() {
  if (!canSend.value) return
  const content = text.value.trim()
  text.value = ''
  emit('send', content)
}

function triggerUpload() {
  fileInputRef.value?.click()
}

function handleFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) {
    emit('upload-pdf', file)
    input.value = ''
  }
}

function handleDrop(e: DragEvent) {
  dragActive.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file && file.name.endsWith('.pdf')) {
    emit('upload-pdf', file)
  }
}
</script>

<style scoped>
.input-bar {
  flex-shrink: 0;
}

.input-context-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4px 12px;
  font-size: 12px;
  color: var(--color-text-secondary);
}

.paper-count {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 10px;
  background: var(--color-surface-muted);
  border-radius: 6px;
}

.paper-clear-btn {
  font-size: 14px;
  color: var(--color-text-muted);
  cursor: pointer;
  line-height: 1;
}

.drop-hint {
  color: var(--color-accent);
  font-weight: 500;
}

.input-wrapper {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 8px 12px;
  background: var(--color-surface-card);
  border: 1px solid var(--color-border-strong);
  border-radius: 14px;
  transition: border-color 0.15s ease;
}

.input-wrapper:focus-within {
  border-color: var(--color-accent);
}

.input-wrapper--drag {
  border-color: var(--color-accent);
  background: rgba(0, 102, 204, 0.03);
}

.input-textarea {
  flex: 1;
  border: none;
  outline: none;
  resize: none;
  font-size: var(--font-size-body);
  line-height: 1.6;
  color: var(--color-text-primary);
  background: transparent;
  font-family: inherit;
  max-height: 150px;
}

.input-textarea::placeholder {
  color: var(--color-text-muted);
}

.send-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  border-radius: 10px;
  background: var(--color-surface-muted);
  color: var(--color-text-muted);
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}

.send-btn--active {
  background: var(--color-accent);
  color: #fff;
}

.send-btn--busy {
  background: var(--color-surface-muted);
  color: var(--color-text-muted);
  cursor: default;
}

.send-btn--active:hover {
  opacity: 0.9;
}

.input-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 12px 8px;
}

.input-toolbar-left {
  display: flex;
  align-items: center;
  gap: 2px;
}

.toolbar-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 6px;
  color: var(--color-text-muted);
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}

.toolbar-btn:hover {
  background: var(--color-surface-muted);
  color: var(--color-text-secondary);
}

.hidden-input {
  display: none;
}

.input-toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.char-count {
  font-size: 11px;
  color: var(--color-text-muted);
}
</style>
