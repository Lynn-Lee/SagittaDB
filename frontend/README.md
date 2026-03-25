# Frontend — React 前端

## 技术栈

- React 18 + TypeScript + Vite
- Ant Design 5（含 Design Token 定制）
- Zustand（全局状态）+ TanStack Query（服务端状态）
- Monaco Editor（SQL 编辑器）
- Recharts（图表）
- React Router v6

## 开发环境启动

```bash
# 安装依赖
npm install

# 启动开发服务器（含 API 代理到 localhost:8000）
npm run dev

# 类型检查
npm run typecheck

# Lint
npm run lint

# 构建生产版本
npm run build
```

## 目录说明

```
src/
├── styles/          全局样式 + CSS 设计 Token
├── main.tsx         应用入口，Ant Design Token 配置
├── App.tsx          路由定义
├── store/           Zustand 全局状态（auth、ui 等）
├── api/             Axios 请求客户端 + 各模块 API 函数
├── types/           TypeScript 类型定义
├── utils/           工具函数（时间、格式化、Prometheus step 等）
├── components/
│   ├── common/      通用组件（AuthGuard、ErrorBoundary 等）
│   ├── layout/      布局组件（MainLayout、Header、Sider）
│   ├── editor/      SQL 编辑器（Monaco 封装）
│   └── monitor/     可观测中心组件（指标卡、趋势图等）
└── pages/           页面组件（按路由模块划分）
    ├── auth/        登录、2FA
    ├── dashboard/   Dashboard
    ├── workflow/    SQL 工单
    ├── query/       在线查询
    ├── monitor/     可观测中心
    ├── instance/    实例管理
    ├── system/      系统管理
    └── audit/       审计日志
```

## UI 设计规范

参考设计文档第十章，核心原则：

- **字体**：系统字体栈（Mac→SF Pro，Win→Segoe UI），零包体积，JetBrains Mono 仅用于代码编辑器
- **主色**：`#1558A8`，仅用于主按钮、链接、选中态
- **背景**：页面底色 `#F5F5F7`，卡片 `#FFFFFF`
- **层级**：无阴影，用背景色 + 边框区分层次
- **圆角**：按钮 8px，卡片 12px，Modal 16px
- **间距**：8px 基础网格

所有 Ant Design 5 Token 已在 `src/main.tsx` 中统一配置。

## Sprint 进度

| Sprint | 模块 | 状态 |
|---|---|---|
| Sprint 0 | 骨架、路由、布局、登录页 | ✅ 完成 |
| Sprint 1 | 认证流程、实例管理页面 | ⏳ 待开始 |
| Sprint 2 | 在线查询（Monaco + 结果表格）| ⏳ 待开始 |
| Sprint 3 | SQL 工单（提交/审核/执行/WebSocket）| ⏳ 待开始 |
| Sprint 4 | 运维工具页面 | ⏳ 待开始 |
| Sprint 5 | 可观测中心（Recharts 趋势图）| ⏳ 待开始 |
| Sprint 6 | 联调测试 | ⏳ 待开始 |
