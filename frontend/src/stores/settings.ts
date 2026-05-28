// 全局设置状态 —— API 配置、模型选择、思考模式

import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import type { ModelConfig } from '../types/model'

const STORAGE_KEY = 'paper-assistant-settings'

function loadFromStorage(): ModelConfig {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      return {
        apiKey: parsed.apiKey || '',
        apiUrl: parsed.apiUrl || 'https://api.deepseek.com/v1',
        selectedModel: parsed.selectedModel || 'deepseek-chat',
        thinkingEnabled: parsed.thinkingEnabled ?? false,
      }
    }
  } catch {
    // 静默降级
  }
  return {
    apiKey: '',
    apiUrl: 'https://api.deepseek.com/v1',
    selectedModel: 'deepseek-chat',
    thinkingEnabled: false,
  }
}

function saveToStorage(config: ModelConfig) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(config))
  } catch {
    // 静默降级
  }
}

export const useSettingsStore = defineStore('settings', () => {
  const initial = loadFromStorage()

  const apiKey = ref(initial.apiKey)
  const apiUrl = ref(initial.apiUrl)
  const selectedModel = ref(initial.selectedModel)
  const thinkingEnabled = ref(initial.thinkingEnabled)

  // 持久化到 localStorage
  watch([apiKey, apiUrl, selectedModel, thinkingEnabled], () => {
    saveToStorage({
      apiKey: apiKey.value,
      apiUrl: apiUrl.value,
      selectedModel: selectedModel.value,
      thinkingEnabled: thinkingEnabled.value,
    })
  }, { deep: true })

  function updateModel(modelName: string) {
    selectedModel.value = modelName
  }

  function toggleThinking() {
    thinkingEnabled.value = !thinkingEnabled.value
  }

  function updateApiConfig(key: string, url: string) {
    apiKey.value = key
    apiUrl.value = url
  }

  const modelConfig = () => ({
    apiKey: apiKey.value,
    apiUrl: apiUrl.value,
    selectedModel: selectedModel.value,
    thinkingEnabled: thinkingEnabled.value,
  })

  return {
    apiKey,
    apiUrl,
    selectedModel,
    thinkingEnabled,
    updateModel,
    toggleThinking,
    updateApiConfig,
    modelConfig,
  }
})
