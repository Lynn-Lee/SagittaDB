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

## 权限 UI 口径（v2-lite）

前端当前遵循以下实现规则：

- 菜单显示由权限码驱动，不再维护“角色 -> 菜单”的第二套真相
- 路由进入由 `PermissionGuard` 做页面级兜底
- 查询页在收到 403 时，会调用 `/query/access-check/` 展示权限拒绝层级和原因

当前首发范围：

- 查询权限申请仅支持库级 / 表级
- 审批流配置仅支持 `指定用户 / 直属上级 / 任意审批员`
- `developer` 默认不显示监控、运维工具、系统管理、审计日志

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
- **主色**：`#165DFF`（Space Tech Blue），用于主按钮、链接、选中态
- **深色背景**：`#0F172A`（Tech Charcoal），用于 Header 等深色区域
- **层级**：无阴影，用背景色 + 边框区分层次
- **圆角**：按钮 6px，卡片 6px，Modal 8px
- **间距**：8px 基础网格

所有 Ant Design 5 Token 已在 `src/main.tsx` 中统一配置。

## 整体进度（v1.0-GA 基线 + v2-lite 权限收敛）

| 模块 | 状态 |
|---|---|
| Sprint 0 — 骨架、路由、布局、登录页 | ✅ 完成 |
| Sprint 1 — 认证流程、实例管理页面 | ✅ 完成 |
| Sprint 2 — 在线查询（Monaco + 结果表格）| ✅ 完成 |
| Sprint 3 — SQL 工单（提交/审核/执行/WebSocket）| ✅ 完成 |
| Sprint 4 — 运维工具页面 | ✅ 完成 |
| Sprint 5 — 可观测中心（Recharts 趋势图）| ✅ 完成 |
| Sprint 6 — 联调测试、品牌升级 | ✅ 完成 |
| 权限前端收敛 | ✅ 完成（菜单权限码化、页面级 PermissionGuard、查询权限排查展示） |
