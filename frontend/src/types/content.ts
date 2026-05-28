// 后端返回的块级内容类型定义
// 用于 ContentRenderer 逐块渲染结构化响应

export interface BlockCitation {
  /** 关联的来源 ID，对应 sources 数组中的项 */
  sourceId: string
}

/** 段落块 */
export interface BlockParagraph {
  type: 'paragraph'
  text: string
  citations?: BlockCitation[]
}

/** 标题块 */
export interface BlockHeading {
  type: 'heading'
  level: 1 | 2 | 3 | 4
  text: string
}

/** 列表块 */
export interface BlockList {
  type: 'list'
  ordered: boolean
  items: string[]
}

/** 引用块 —— 标记引用了某篇论文的段落 */
export interface BlockCitationText {
  type: 'citation_block'
  text: string
  /** 关联的来源 ID 列表，用于底部来源面板展示 */
  sourceIds: string[]
}

/** 表格块 */
export interface BlockTable {
  type: 'table'
  headers: string[]
  rows: string[][]
}

/** 代码块 */
export interface BlockCode {
  type: 'code'
  language: string
  code: string
}

/** 分隔线 */
export interface BlockDivider {
  type: 'divider'
}

export type ContentBlock =
  | BlockParagraph
  | BlockHeading
  | BlockList
  | BlockCitationText
  | BlockTable
  | BlockCode
  | BlockDivider

/** 后端 SSE 响应的 content 字段 */
export interface StructuredContent {
  blocks: ContentBlock[]
}
