# 数据库管理平台 2.0

基于 Archery v1.14.0 重构，企业内部版（为 SaaS 预留接口，不实现 SaaS 功能）。

## 技术栈

| 层次 | 技术 |
|---|---|
| 后端 | FastAPI + SQLAlchemy 2.0 async + Celery 5 + PostgreSQL 16 |
| 前端 | React 18 + TypeScript + Vite + Ant Design 5 |
| 引擎层 | EngineProtocol + sqlglot（替代 goInception 解析） |
| 可观测 | Prometheus + Alertmanager + Grafana |
| 部署 | Docker Compose（开发）/ K8s + Helm（生产） |

## 快速启动（开发环境）

```bash
# 1. 复制环境变量
cp .env.example .env
# 按需修改 .env 中的配置

# 2. 启动所有服务
docker compose up -d

# 3. 执行数据库迁移
docker compose exec backend alembic upgrade head

# 4. 访问
# 前端：http://localhost
# 后端 API 文档：http://localhost:8000/docs
# Grafana：http://localhost:3000
# Flower（Celery 监控）：http://localhost:5555
```

## 目录结构

```
archery2.0/
├── backend/        # FastAPI 后端
├── frontend/       # React 前端
├── deploy/         # 部署配置（Docker Compose / Helm）
└── docs/           # 项目文档
```

## 开发指南

- 后端开发：[backend/README.md](backend/README.md)
- 前端开发：[frontend/README.md](frontend/README.md)
- 部署说明：[deploy/README.md](deploy/README.md)

## Sprint 进度

| Sprint | 内容 | 状态 |
|---|---|---|
| Sprint 0 | 基础设施 + 骨架 | 🔄 进行中 |
| Sprint 1 | 认证与实例管理 | ⏳ 待开始 |
| Sprint 2 | 引擎层 + 在线查询 | ⏳ 待开始 |
| Sprint 3 | SQL 工单核心 | ⏳ 待开始 |
| Sprint 4 | 运维工具 | ⏳ 待开始 |
| Sprint 5 | 可观测中心 | ⏳ 待开始 |
| Sprint 6 | 收尾与发布 | ⏳ 待开始 |
