/** 模型配置 */
export interface ModelConfig {
  /** API 密钥 */
  apiKey: string
  /** API 基础 URL */
  apiUrl: string
  /** 当前选择的模型名称 */
  selectedModel: string
  /** 是否开启思考模式 */
  thinkingEnabled: boolean
}

/** 后端返回的模型列表项 */
export interface ModelInfo {
  /** 模型 ID */
  id: string
  /** 模型显示名称 */
  name: string
  /** 模型所属提供商 */
  provider?: string
  /** 是否支持思考模式 */
  supportThinking?: boolean
}
