// 模型管理 API 客户端

import { buildApiUrl, ApiClientError } from './api-client'
import type { ModelInfo, ModelConfig } from '../types/model'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(buildApiUrl(path), init)
  const body = await res.json().catch(() => ({}))
  if (!res.ok) {
    const detail = body.detail && typeof body.detail === 'object' ? body.detail.message : undefined
    throw new ApiClientError(body.message || detail || `HTTP ${res.status}`, res.status)
  }
  return body as T
}

/** 从后端获取可用模型列表 */
export async function fetchModels(config: ModelConfig): Promise<ModelInfo[]> {
  const result = await request<{ models: ModelInfo[] }>('/api/v1/models', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      api_key: config.apiKey,
      api_url: config.apiUrl,
    }),
  })
  return result.models
}
