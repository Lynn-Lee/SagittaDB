# Backend — FastAPI 后端

## 开发环境启动

```bash
# 安装依赖
pip install -e ".[dev]"

# 执行数据库迁移
alembic upgrade head

# 启动开发服务器（热重载）
uvicorn app.main:app --reload --port 8000

# 启动 Celery Worker
celery -A app.celery_app worker -Q default,execute,notify --loglevel=info

# 启动 Celery Beat（定时任务）
celery -A app.celery_app beat --loglevel=info

# 启动 Flower（Celery 监控）
celery -A app.celery_app flower --port=5555
```

## 数据库迁移

```bash
# 生成新迁移文件（修改 models 后执行）
alembic revision --autogenerate -m "描述变更内容"

# 应用迁移
alembic upgrade head

# 回滚一步
alembic downgrade -1
```

## 目录说明

```
app/
├── core/         配置、数据库、安全、依赖注入、异常、日志
├── models/       SQLAlchemy ORM 模型（含 tenant_id SaaS预留）
├── schemas/      Pydantic 请求/响应 Schema（Sprint 1+ 补充）
├── engines/      数据库引擎层（EngineProtocol + 11 种实现）
├── services/     业务逻辑层（masking、audit、notify 等）
├── routers/      FastAPI 路由（每个模块独立文件）
└── tasks/        Celery 异步任务
```

## Sprint 进度

| Sprint | 模块 | 状态 |
|---|---|---|
| Sprint 0 | 项目骨架、配置、基础模型、引擎协议 | ✅ 完成 |
| Sprint 1 | 认证（JWT/LDAP/OIDC）、用户、实例管理 | ⏳ 待开始 |
| Sprint 2 | 引擎层完整实现、查询权限、数据脱敏 | ⏳ 待开始 |
| Sprint 3 | SQL 工单审批执行流程、WebSocket | ⏳ 待开始 |
| Sprint 4 | 慢日志、会话管理、归档、Binlog | ⏳ 待开始 |
| Sprint 5 | 可观测中心、Prometheus、Grafana SSO | ⏳ 待开始 |
| Sprint 6 | 全链路测试、安全扫描、数据迁移工具 | ⏳ 待开始 |

## 代码规范

```bash
# 格式化
ruff format .

# Lint
ruff check .

# 类型检查
mypy app/

# 运行测试
pytest tests/ -v --cov=app
```
