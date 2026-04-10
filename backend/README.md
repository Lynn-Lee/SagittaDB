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

## 整体进度（v1.0-GA 全部完成）

| 模块 | 状态 |
|---|---|
| Sprint 0 — 项目骨架 | ✅ 完成 |
| Sprint 1 — 认证、用户、实例管理 | ✅ 完成 |
| Sprint 2 — 引擎层、在线查询、查询权限 | ✅ 完成 |
| Pack A — SQL 工单全流程 + 运维工具 | ✅ 完成 |
| Pack B — 可观测中心 + 迁移脚本 | ✅ 完成 |
| Pack C — 系统配置、审计日志、资源组、数据库注册 | ✅ 完成 |
| Pack D — 数据脱敏、数据字典、工单模板、AI Text2SQL | ✅ 完成 |
| Pack E — 多引擎补全、数据归档、SQL 回滚、通知服务 | 🔧 完成（85%）|
| Pack F — 第三方登录（LDAP/钉钉/飞书/企微/CAS） | ✅ 完成 |
| Pack G — 全链路测试、性能测试、安全扫描 | ✅ 完成 |
| Pack H — Helm Chart、CI/CD、生产环境配置 | ✅ 完成 |
| Security Hardening — 安全加固 | ✅ 完成 |
| 多级审批流 | ✅ 完成 |

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
