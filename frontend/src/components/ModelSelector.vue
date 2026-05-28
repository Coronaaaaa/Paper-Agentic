<!-- 模型选择器面板 -->
<template>
  <div class="model-selector">
    <button class="model-trigger" type="button" @click="emit('toggle')">
      <span class="model-name">{{ settings.selectedModel || '选择模型' }}</span>
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor"
        stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="6 9 12 15 18 9" />
      </svg>
    </button>

    <!-- 下拉面板 -->
    <Teleport to="body">
      <div v-if="open" class="model-overlay" @click="emit('close')">
        <div class="model-panel" @click.stop>
          <div class="model-panel-header">
            <h3>API 配置</h3>
            <button class="model-close-btn" type="button" @click="emit('close')">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>

          <div class="model-field">
            <label class="model-label">API Key</label>
            <input
              v-model="localKey"
              type="password"
              class="model-input"
              placeholder="sk-..."
              autocomplete="off"
            >
          </div>

          <div class="model-field">
            <label class="model-label">API URL</label>
            <input
              v-model="localUrl"
              type="text"
              class="model-input"
              placeholder="https://api.deepseek.com/v1"
            >
          </div>

          <button
            class="model-fetch-btn"
            type="button"
            :disabled="!canFetch"
            @click="fetchModels"
          >
            {{ fetching ? '获取中...' : '获取模型列表' }}
          </button>

          <div v-if="models.length > 0" class="model-list">
            <div class="model-list-label">可用模型</div>
            <label
              v-for="m in models"
              :key="m.id"
              class="model-option"
              :class="{ 'model-option--active': localModel === m.id }"
            >
              <input
                type="radio"
                :value="m.id"
                v-model="localModel"
                class="model-radio"
              >
              <span class="model-option-name">{{ m.name || m.id }}</span>
              <span v-if="m.provider" class="model-option-provider">{{ m.provider }}</span>
            </label>
          </div>

          <div class="model-divider"></div>

          <div class="model-thinking-row">
            <span class="model-thinking-label">思考模式</span>
            <button
              class="model-toggle"
              :class="{ 'model-toggle--active': localThinking }"
              type="button"
              @click="localThinking = !localThinking"
            >
              <span class="model-toggle-knob"></span>
            </button>
          </div>

          <div class="model-actions">
            <button class="model-cancel-btn" type="button" @click="emit('close')">取消</button>
            <button class="model-save-btn" type="button" @click="save">确认</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useSettingsStore } from '../stores/settings'
import { fetchModels as apiFetchModels } from '../services/model-api'
import type { ModelInfo } from '../types/model'

const settings = useSettingsStore()

defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  (e: 'toggle'): void
  (e: 'close'): void
  (e: 'save'): void
}>()

const localKey = ref(settings.apiKey)
const localUrl = ref(settings.apiUrl)
const localModel = ref(settings.selectedModel)
const localThinking = ref(settings.thinkingEnabled)

const models = ref<ModelInfo[]>([])
const fetching = ref(false)

const canFetch = computed(() => localKey.value.trim() && localUrl.value.trim() && !fetching.value)

async function fetchModels() {
  if (!canFetch.value) return
  fetching.value = true
  try {
    const result = await apiFetchModels({
      apiKey: localKey.value,
      apiUrl: localUrl.value,
      selectedModel: '',
      thinkingEnabled: false,
    })
    models.value = result
  } catch {
    // 静默，错误由上层通知
  } finally {
    fetching.value = false
  }
}

function save() {
  settings.updateApiConfig(localKey.value, localUrl.value)
  settings.updateModel(localModel.value)
  if (localThinking.value !== settings.thinkingEnabled) {
    settings.toggleThinking()
  }
  emit('save')
  emit('close')
}
</script>

<style scoped>
.model-selector {
  position: relative;
}

.model-trigger {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: background 0.15s ease;
}

.model-trigger:hover {
  background: var(--color-border-subtle);
}

.model-name {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 面板 */
.model-overlay {
  position: fixed;
  inset: 0;
  z-index: 200;
  background: rgba(0, 0, 0, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
}

.model-panel {
  width: 380px;
  max-height: 80vh;
  overflow-y: auto;
  background: var(--color-surface-card);
  border-radius: 14px;
  box-shadow: 0 12px 48px rgba(0, 0, 0, 0.15);
  padding: 20px 24px;
}

.model-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.model-panel-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.model-close-btn {
  padding: 4px;
  border-radius: 6px;
  color: var(--color-text-muted);
  cursor: pointer;
}

.model-close-btn:hover {
  background: var(--color-border-subtle);
  color: var(--color-text-primary);
}

.model-field {
  margin-bottom: 12px;
}

.model-label {
  display: block;
  font-size: 12px;
  font-weight: 500;
  color: var(--color-text-secondary);
  margin-bottom: 4px;
}

.model-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--color-border-strong);
  border-radius: 8px;
  font-size: 13px;
  color: var(--color-text-primary);
  background: var(--color-surface-base);
  outline: none;
  transition: border-color 0.15s ease;
}

.model-input:focus {
  border-color: var(--color-accent);
}

.model-fetch-btn {
  width: 100%;
  padding: 8px;
  margin-bottom: 12px;
  background: var(--color-surface-muted);
  border-radius: 8px;
  font-size: 13px;
  color: var(--color-text-primary);
  cursor: pointer;
  transition: background 0.15s ease;
}

.model-fetch-btn:hover:not(:disabled) {
  background: var(--color-border-subtle);
}

.model-fetch-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.model-list-label {
  font-size: 11px;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}

.model-list {
  max-height: 160px;
  overflow-y: auto;
  margin-bottom: 4px;
}

.model-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.1s ease;
}

.model-option:hover {
  background: var(--color-surface-muted);
}

.model-option--active {
  background: rgba(0, 102, 204, 0.06);
}

.model-radio {
  accent-color: var(--color-accent);
}

.model-option-name {
  font-size: 13px;
  color: var(--color-text-primary);
  flex: 1;
}

.model-option-provider {
  font-size: 11px;
  color: var(--color-text-muted);
}

.model-divider {
  height: 1px;
  background: var(--color-border-subtle);
  margin: 12px 0;
}

.model-thinking-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.model-thinking-label {
  font-size: 13px;
  color: var(--color-text-primary);
}

/* Toggle 开关 */
.model-toggle {
  width: 44px;
  height: 24px;
  border-radius: 12px;
  background: var(--color-border-strong);
  position: relative;
  cursor: pointer;
  transition: background 0.2s ease;
}

.model-toggle--active {
  background: var(--color-accent);
}

.model-toggle-knob {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15);
  transition: left 0.2s ease;
}

.model-toggle--active .model-toggle-knob {
  left: 22px;
}

.model-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.model-cancel-btn {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 13px;
  color: var(--color-text-secondary);
  cursor: pointer;
}

.model-cancel-btn:hover {
  background: var(--color-surface-muted);
}

.model-save-btn {
  padding: 8px 20px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  color: #fff;
  background: var(--color-accent);
  cursor: pointer;
}

.model-save-btn:hover {
  opacity: 0.9;
}
</style>
