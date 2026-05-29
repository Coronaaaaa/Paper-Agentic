# 前端测试

本目录存放前端单元测试和组件测试。

## 目录结构

```
test_frontend/
├── components/       # 组件测试
├── stores/           # Pinia store 测试
├── services/         # API 服务测试
├── composables/      # 组合式函数测试
└── README.md
```

## 运行方式

```bash
cd frontend
pnpm test
```

## 测试框架

- Vitest（单元测试）
- Vue Test Utils（组件测试）
