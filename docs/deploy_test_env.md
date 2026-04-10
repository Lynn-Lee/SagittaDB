# SagittaDB 测试环境部署文档

> **文档版本：** v1.1 · 2026-04-08
> **适用版本：** SagittaDB v1.0-GA
> **部署方式：** Docker Compose（开发 / 测试）
> **目标读者：** 开发人员、测试人员、技术负责人

---

## 一、环境要求

### 1.1 硬件最低配置

| 资源 | 最低要求 | 推荐配置 |
|---|---|---|
| CPU | 2 核 | 4 核 |
| 内存 | 4 GB | 8 GB |
| 磁盘 | 20 GB | 50 GB |
| 网络 | 可访问互联网（拉取镜像） | — |

### 1.2 软件依赖

| 软件 | 最低版本 | 说明 |
|---|---|---|
| Docker | 24.0+ | `docker --version` 确认 |
| Docker Compose | V2（2.20+） | `docker compose version` 确认（注意是 `compose` 不是 `compose-plugin`） |
| Git | 2.x+ | 拉取代码 |

> **macOS 用户：** 安装 Docker Desktop（已内置 Compose V2）
>
> **Linux 用户：**
> ```bash
> curl -fsSL https://get.docker.com | sh
> sudo usermod -aG docker $USER   # 免 sudo 运行 docker
> newgrp docker
> ```

---

## 二、快速部署（10 分钟）

### 步骤 1：克隆代码

```bash
git clone https://github.com/Lynn-Lee/SagittaDB.git
cd SagittaDB
```

### 步骤 2：配置环境变量

```bash
cp .env.example .env
```

测试环境使用默认值即可，无需修改 `.env`。如需自定义，参考第三节。

### 步骤 3：启动所有服务

```bash
docker compose up -d
```

首次启动会拉取镜像并构建，约需 3~5 分钟。

### 步骤 4：执行数据库迁移

```bash
docker compose exec backend alembic upgrade head
```

### 步骤 5：初始化系统

```bash
curl -X POST http://localhost:8000/api/v1/system/init/
```

输出 `{"status": 0}` 表示成功，默认管理员账号：**admin / Admin@2024!**

### 步骤 6：验证服务

```bash
docker compose ps
```

确认所有服务状态为 `Up`（postgres、redis 为 `healthy`）。

访问以下地址验证：

| 服务 | 地址 | 说明 |
|---|---|---|
| 前端平台 | http://localhost | 登录页 |
| API 文档 | http://localhost:8000/docs | Swagger UI |
| Celery 监控 | http://localhost:5555 | Flower 面板 |
| Prometheus | http://localhost:9090 | 指标查询 |
| Grafana | http://localhost:3000 | 仪表板（admin/admin） |

---

## 三、环境变量详解

测试环境 `.env` 文件说明（位于项目根目录）：

```bash
# ── 数据库 ──────────────────────────────────────────
# 测试环境使用 Docker 内部网络名 postgres
DATABASE_URL=postgresql+asyncpg://sagitta:sagitta123@postgres:5432/sagittadb
DATABASE_URL_SYNC=postgresql+psycopg2://sagitta:sagitta123@postgres:5432/sagittadb

# ── Redis ────────────────────────────────────────────
REDIS_URL=redis://:redis123@redis:6379/0
REDIS_PASSWORD=redis123

# ── 安全（测试环境可保持默认）───────────────────────
SECRET_KEY=CHANGE_ME_IN_PRODUCTION_USE_RANDOM_32_CHARS
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# ── 应用环境 ─────────────────────────────────────────
APP_ENV=development
DEBUG=true
LOG_LEVEL=INFO

# ── 可观测 ───────────────────────────────────────────
PROMETHEUS_URL=http://prometheus:9090
ALERTMANAGER_URL=http://alertmanager:9093
GRAFANA_URL=http://localhost:3000

# ── AI 功能（可选，测试时留空）──────────────────────
AI_PROVIDER=none
AI_API_KEY=

# ── PostgreSQL 初始化（Docker 内部使用）─────────────
POSTGRES_DB=sagittadb
POSTGRES_USER=sagitta
POSTGRES_PASSWORD=sagitta123
```

---

## 四、服务架构说明

测试环境启动的容器列表：

```
sagittadb-postgres-1      # PostgreSQL 16 元数据库
sagittadb-redis-1         # Redis 7 缓存/消息队列
sagittadb-backend-1       # FastAPI 后端（热重载模式）
sagittadb-celery_worker-1 # Celery Worker（异步任务）
sagittadb-celery_beat-1   # Celery Beat（定时任务）
sagittadb-flower-1        # Flower 任务监控
sagittadb-frontend-1      # Nginx + React 前端
sagittadb-prometheus-1    # Prometheus 指标采集
sagittadb-alertmanager-1  # 告警管理
sagittadb-grafana-1       # Grafana 可视化
```

**端口映射：**

| 容器端口 | 宿主机端口 | 服务 |
|---|---|---|
| 80 | 80 | 前端（Nginx） |
| 8000 | 8000 | 后端 API |
| 5432 | 5432 | PostgreSQL |
| 6379 | 6379 | Redis |
| 5555 | 5555 | Flower |
| 9090 | 9090 | Prometheus |
| 9093 | 9093 | Alertmanager |
| 3000 | 3000 | Grafana |

---

## 五、常用运维命令

### 5.1 查看日志

```bash
# 所有服务日志
docker compose logs -f

# 指定服务日志
docker compose logs -f backend
docker compose logs -f celery_worker
docker compose logs -f frontend
```

### 5.2 重启服务

```bash
# 重启单个服务（代码热重载已开启，通常不需要）
docker compose restart backend

# 重启全部服务
docker compose restart
```

### 5.3 停止与清理

```bash
# 停止服务（保留数据卷）
docker compose down

# 停止服务并清除数据卷（完全重置）⚠️ 数据不可恢复
docker compose down -v
```

### 5.4 进入容器调试

```bash
# 进入后端容器
docker compose exec backend bash

# 在后端容器执行 Python 命令
docker compose exec backend python -c "from app.core.config import settings; print(settings.DATABASE_URL)"

# 连接 PostgreSQL
docker compose exec postgres psql -U sagitta -d sagittadb

# 连接 Redis
docker compose exec redis redis-cli -a redis123
```

### 5.5 数据库操作

```bash
# 查看 Alembic 迁移状态
docker compose exec backend alembic current

# 执行新迁移
docker compose exec backend alembic upgrade head

# 查看所有表
docker compose exec postgres psql -U sagitta -d sagittadb -c "\dt"

# 重置 admin 密码（忘记密码时）
NEW_HASH=$(docker compose exec backend python -c "from app.core.security import hash_password; print(hash_password('Admin@2024!'))" | tail -1)
docker compose exec postgres psql -U sagitta -d sagittadb -c "UPDATE sql_users SET password='$NEW_HASH' WHERE username='admin';"
```

---

## 六、前端开发模式（热更新）

如需修改前端代码并实时预览，使用 Vite 开发服务器替代容器前端：

```bash
# 终端 1：启动后端依赖（不含前端容器）
docker compose up -d postgres redis backend celery_worker

# 终端 2：启动前端开发服务器
cd frontend
npm install
npm run dev
# 访问 http://localhost:5173
```

> Vite 配置中 API 代理已指向 `http://localhost:8000`，无需额外配置。

---

## 七、运行测试套件

### 7.1 单元测试

```bash
# 进入 backend 目录（宿主机）
cd backend
pip install -e ".[dev]"

# 运行全部单元测试
pytest tests/unit/ -v

# 运行含覆盖率报告
pytest tests/unit/ --cov=app --cov-report=term-missing
```

### 7.2 集成测试

集成测试需要连接 PostgreSQL，使用 `sagittadb_test` 库（由 conftest 自动创建）：

```bash
# 创建测试库（首次）
docker compose exec postgres psql -U sagitta -c "CREATE DATABASE sagittadb_test;"

# 运行集成测试（需设置正确的 DATABASE_URL）
export DATABASE_URL=postgresql+asyncpg://sagitta:sagitta123@localhost:5432/sagittadb
export REDIS_URL=redis://:redis123@localhost:6379/0
export SECRET_KEY=test-secret-key-for-ci-only
export FERNET_KEY=dGhpcy1pcy1hLXRlc3Qta2V5LWZvci1jaS1vbmx5IQ==

pytest tests/integration/ -v
```

### 7.3 性能测试（可选）

```bash
pip install locust
locust -f tests/perf/locustfile.py --host http://localhost:8000
# 浏览器访问 http://localhost:8089，设置并发用户数后开始测试
```

---

## 八、Grafana Dashboard 导入

1. 访问 http://localhost:3000，使用 `admin / admin` 登录
2. 左侧菜单 → Dashboards → Import
3. 上传 `deploy/grafana/` 目录下的 JSON 文件（可逐个导入）
4. 数据源选择 `Prometheus`，保存

---

## 九、常见问题

### Q1：端口被占用

```bash
# 检查占用 80 端口的进程
lsof -i :80
# 或修改 docker-compose.yml 中的端口映射，如改为 8080:80
```

### Q2：backend 容器启动失败

```bash
# 查看错误日志
docker compose logs backend --tail=50

# 常见原因：数据库连接失败（postgres 未就绪）
# 解决：等待 postgres healthy 后重启 backend
docker compose restart backend
```

### Q3：alembic upgrade head 报错

```bash
# 常见：数据库版本不一致
docker compose exec backend alembic history
# 若需重置：（⚠️ 仅测试环境）
docker compose exec postgres psql -U sagitta -d sagittadb -c "DROP TABLE IF EXISTS alembic_version;"
docker compose exec backend alembic upgrade head
```

### Q4：Celery Worker 显示 unhealthy

Celery Worker 无 HTTP 健康检查接口，`unhealthy` 是已知问题（功能正常）。通过 Flower 面板确认 Worker 是否在线即可。

### Q5：前端页面空白或 404

```bash
# 检查 frontend 容器日志
docker compose logs frontend

# 确认 nginx.conf 正确挂载
docker compose exec frontend cat /etc/nginx/conf.d/default.conf
```

---

## 十、测试数据准备建议

测试环境首次部署后，建议按以下顺序准备测试数据：

1. **创建测试用户**：`admin` + 至少 1 个普通用户（含 sql_submit 权限）
2. **创建资源组**：添加成员，配置通知 Webhook（可用测试用 Webhook）
3. **注册测试实例**：可指向本地 MySQL / PostgreSQL（或 Docker 内另起的实例）
4. **注册数据库**：对测试实例执行"从引擎同步"
5. **配置数据脱敏规则**：选一个 email/phone 字段配置规则
6. **提交测试工单**：走完提交→审批→执行完整流程

---

*SagittaDB 矢准数据 · 测试环境部署文档 v1.0 · 2026-03-26*
