# SagittaDB 矢准数据

> **矢向数据，精准管控**
> 企业级多引擎数据库管控平台 · 基于 Archery v1.14.0 深度重构 · v1.0-GA

---

## 产品简介

SagittaDB 通过统一的 Web 界面，帮助 DBA 和研发团队安全、高效地完成 SQL 审核上线、在线查询、慢日志分析、数据库监控等全流程数据库管理工作。

- **安全**：修复原 Archery 5 个 P0 安全漏洞，Token 黑名单 fail-close，所有敏感字段 Fernet/AES 加密存储
- **全面**：支持 11 种数据库引擎（MySQL / PgSQL / Oracle / MongoDB / Redis / ClickHouse 等）
- **高效**：AI Text2SQL + 工单模板 + 多级自定义审批流，全异步 Celery 执行不阻塞
- **可观测**：内建 Prometheus + Grafana 监控，全流程操作审计

## 技术栈

| 层次 | 技术 |
|---|---|
| 后端 | FastAPI + SQLAlchemy 2.0 async + Celery 5 + PostgreSQL 16 |
| 前端 | React 18 + TypeScript + Vite + Ant Design 5 |
| SQL 解析 | sqlglot（替代 goInception，支持 20+ 方言） |
| AI | Anthropic Claude API（Text2SQL） |
| 可观测 | Prometheus + Alertmanager + Grafana |
| 部署 | Docker Compose（开发/测试）/ K8s + Helm（生产预留）|

## 快速启动

```bash
# 1. 复制并配置环境变量
cp .env.example .env

# 2. 启动全部服务
docker compose up -d

# 3. 执行数据库迁移
docker compose exec backend alembic upgrade head

# 4. 访问
# 前端：       http://localhost
# 后端 API：   http://localhost:8000/docs
# Grafana：    http://localhost:3000
# Flower：     http://localhost:5555
```

## 目录结构

```
SagittaDB/
├── backend/        # FastAPI 后端（engines / routers / services / models）
├── frontend/       # React 前端（pages / components / store / api）
├── deploy/         # 部署配置（Nginx / Prometheus / Grafana）
├── docs/           # 项目文档
│   ├── sagittadb_prd.md       # 产品需求文档（PRD v2.0）
│   └── sagittadb_progress.md  # 开发进度文档
└── docker-compose.yml
```

## 开发进度

| 阶段 | 内容 | 状态 |
|---|---|---|
| Sprint 0 | 项目骨架、基础设施 | ✅ 100% |
| Sprint 1 | 认证、用户、实例管理 | ✅ 100% |
| Sprint 2 | 引擎层、在线查询、查询权限 | ✅ 100% |
| Pack A | SQL 工单全流程 + 运维工具 | ✅ 100% |
| Pack B | 可观测中心 + 迁移脚本 | ✅ 100% |
| Pack C | 系统配置、审计日志、资源组、数据库注册 | ✅ 100% |
| Pack D | 数据脱敏、数据字典、工单模板、AI Text2SQL | ✅ 100% |
| Pack E | 多引擎补全、数据归档、SQL 回滚、通知服务 | 🔧 85% |
| 品牌升级 | SagittaDB 品牌 UI 全面更新 | ✅ 100% |
| Pack F | 第三方登录（LDAP/钉钉/飞书/企微/CAS） | ✅ 100% |
| Pack G | 全链路测试、性能测试、安全扫描 | ✅ 100% |
| Pack H | Helm Chart、CI/CD、生产环境配置 | ✅ 100% |
| Security Hardening | Token 黑名单 fail-close、SECRET_KEY 强制校验、AI 路由注册 | ✅ 100% |
| 多级审批流 | 管理员自定义审批节点 + 前端管理页面 | ✅ 100% |
| 数据库权限管控 | is_active 启停控制、普通用户不可见禁用库、管理员标灰"已禁用" | ✅ 100% |
| Bug 修复 | MySQL DictCursor 修复、PG 表缺失修复、前端下拉框截断修复 | ✅ 100% |

**总体完成度：100%（v1.0-GA）**

详细进度请见 [docs/sagittadb_progress.md](docs/sagittadb_progress.md)
产品需求文档请见 [docs/sagittadb_prd.md](docs/sagittadb_prd.md)

## 开发指南

- 后端：[backend/README.md](backend/README.md)
- 前端：[frontend/README.md](frontend/README.md)
- 部署：[deploy/README.md](deploy/README.md)

---

*SagittaDB 矢准数据 · Full Engine Compatibility, End-to-End Observability*
