# Pack G 测试说明文档

> **版本：** v1.0 · 2026-03-25
> **适用范围：** SagittaDB 后端测试套件

---

## 一、快速运行

### 1.1 在 Docker 容器内运行（推荐）

```bash
# 安装测试依赖（容器内）
docker exec sagittadb-backend-1 sh -c "pip install pytest pytest-asyncio pytest-cov httpx -q"

# 运行全部单元测试
docker exec sagittadb-backend-1 sh -c "cd /app && python -m pytest tests/unit/ -v"

# 运行带覆盖率报告的单元测试
docker exec sagittadb-backend-1 sh -c "cd /app && python -m pytest tests/unit/ --cov=app --cov-report=term-missing -q"
```

### 1.2 本地运行（需配置环境变量）

```bash
cd backend

# 配置测试环境变量
export DATABASE_URL="postgresql+asyncpg://archery:archery123@localhost:5432/archery_test"
export REDIS_URL="redis://localhost:6379/0"
export SECRET_KEY="test-secret-key-for-local-dev"

# 安装依赖
pip install -e ".[dev]"

# 运行单元测试
pytest tests/unit/ -v --cov=app --cov-report=term-missing

# 运行集成测试（需 PostgreSQL + Redis 运行中）
pytest tests/integration/ -v

# 运行所有测试
pytest tests/unit/ tests/integration/ -v --cov=app --cov-report=html
```

---

## 二、测试文件结构

```
backend/tests/
├── conftest.py                    # 公共 fixtures（测试 DB、测试 Client、auth_headers）
├── unit/
│   ├── test_auth.py               # 密码哈希、JWT、字段加密、Schema 校验（20 个）
│   ├── test_masking.py            # 数据脱敏规则、sqlglot 解析（17 个）
│   ├── test_engine_registry.py    # 引擎注册表
│   ├── test_mysql_engine.py       # MySQL 引擎方法
│   ├── test_mongo_engine.py       # MongoDB 引擎方法
│   ├── test_ldap_auth.py          # LDAP 认证服务（5 个）
│   ├── test_oauth_auth.py         # OAuth2 服务（8 个）
│   ├── test_rollback.py           # SQL 回滚辅助（24 个）
│   ├── test_notify.py             # 通知服务 mock HTTP（14 个）
│   ├── test_system_config.py      # 系统配置服务（15 个）
│   └── test_workflow_service.py   # 工单服务（11 个）
├── integration/
│   ├── test_health.py             # 健康检查（3 个）
│   ├── test_auth_api.py           # 认证 API 完整流程（14 个）
│   ├── test_instance_api.py       # 实例 CRUD（8 个）
│   └── test_workflow_api.py       # 工单 API（9 个）
└── perf/
    └── locustfile.py              # Locust 性能测试场景
```

**总计：152 个单元测试，34 个集成测试（含健康检查）**

---

## 三、单元测试详情

### 3.1 test_auth.py — 认证核心

| 测试类 | 覆盖点 |
|--------|--------|
| `TestPasswordHashing` | bcrypt + SHA-256 哈希/验证，空密码，错误密码 |
| `TestJWT` | access/refresh token 生成、解码、类型验证、过期 |
| `TestFieldEncryption` | Fernet 加解密往返、空字符串、兼容旧明文 |
| `TestUserCreateSchema` | 用户名长度/字符校验、密码复杂度验证 |

### 3.2 test_masking.py — 数据脱敏

| 测试类 | 覆盖点 |
|--------|--------|
| `TestExtractSelectColumns` | 简单 SELECT、别名、表前缀、PgSQL 方言、ClickHouse、无效 SQL |
| `TestExtractTableRefs` | FROM 子句、显式 Schema、JOIN、子查询 |
| `TestDataMaskingService` | 手机号/邮箱/身份证/自定义脱敏，无匹配规则，PgSQL 脱敏 |

### 3.3 test_rollback.py — SQL 回滚辅助

| 测试类 | 覆盖点 |
|--------|--------|
| `TestGetRollbackGuide` | 6 种数据库类型的回滚策略说明 |
| `TestGenerateReverseSQL` | INSERT→DELETE、DELETE、UPDATE、DDL、无效 SQL、PgSQL 方言 |
| `TestGenerateMy2sqlCommand` | 命令格式、时间范围参数、数据库过滤、返回结构 |
| `TestGetPgWalQuery` | pg_logical 函数、slot_name 注入、steps 结构 |

### 3.4 test_notify.py — 通知服务

| 测试类 | 覆盖点 |
|--------|--------|
| `TestDingTalkSend` | 发送成功、签名生成、错误响应异常 |
| `TestWecomSend` | 发送成功、错误响应异常 |
| `TestFeishuSend` | 发送成功 |
| `TestNotifyWorkflow` | 渠道均未启用、启用渠道发送、单渠道失败不影响其他 |
| `TestStatusConstants` | 状态文案完整性校验 |

### 3.5 test_system_config.py — 系统配置

| 测试类 | 覆盖点 |
|--------|--------|
| `TestConfigDefinitions` | 结构完整性、敏感字段命名规范、分组存在性、无重复 key |
| `TestGetValue` | 默认值回退、明文读取、加密字段解密、未知 key 空字符串 |
| `TestUpdateBatch` | 跳过未知 key、跳过空敏感字段、跳过掩码值、更新/新建记录、加密存储、变更摘要 |

### 3.6 test_workflow_service.py — 工单服务

| 测试类 | 覆盖点 |
|--------|--------|
| `TestWorkflowStatus` | 枚举值正确性、唯一性、整数比较（替代 1.x 字符串状态） |
| `TestFmtWorkflow` | 格式化输出字段完整性、instance_name 传递 |
| `TestCheckSql` | SELECT/DDL 检查结果、实例不存在异常 |
| `TestPendingForMe` | 返回类型为 (total, list) 元组 |

---

## 四、集成测试详情

### 4.1 test_auth_api.py

| 场景 | 预期结果 |
|------|----------|
| 正确凭证登录 | 200，返回 access_token + refresh_token |
| 错误密码 | 401 |
| 不存在用户 | 401 |
| 缺少字段 | 422 |
| 使用 access_token 访问 /me | 200，返回用户信息 |
| 使用 refresh_token 刷新 | 200，返回新 token |
| access_token 作为 refresh_token 使用 | 401（token 类型错误） |
| 无 token 访问 /me | 401 |
| 畸形 token | 401 |
| 正常登出 | 200 |

### 4.2 test_instance_api.py

| 场景 | 预期结果 |
|------|----------|
| 未认证创建实例 | 401 |
| 管理员创建实例 | 200/201 |
| 缺少必填字段 | 422 |
| 按 ID 查询实例 | 200 |
| 查询不存在实例 | 404 |
| 删除实例 | 200/204 |
| 密码不明文出现在响应中 | 断言通过（P0 安全修复验证） |

### 4.3 test_workflow_api.py

| 场景 | 预期结果 |
|------|----------|
| 未认证获取列表 | 401 |
| 分页/状态筛选 | 200 |
| 缺少必填字段提交工单 | 422 |
| 完整工单提交流程 | 200/201 或 400（实例无法连接） |
| 查询工单详情 | 200 |
| 查询不存在工单 | 404 |

---

## 五、性能测试（Locust）

### 5.1 安装与启动

```bash
pip install locust

# 交互式 Web UI（推荐首次使用）
locust -f tests/perf/locustfile.py \
  --host http://localhost:8000

# 无头压测（CI/脚本化）
locust -f tests/perf/locustfile.py \
  --host http://localhost:8000 \
  --headless \
  -u 50 \        # 50 个并发用户
  -r 10 \        # 每秒新增 10 个用户
  --run-time 60s \
  --csv reports/perf
```

### 5.2 测试场景

| 用户类 | 权重 | 场景 | 等待时间 |
|--------|------|------|----------|
| `AuthUser` | 30% | 登录 + /me 查询 + Token 刷新 | 0.5s ~ 2s |
| `APIUser` | 70% | 工单列表 + 实例列表 + 监控 Dashboard | 1s ~ 3s |

### 5.3 性能基准参考（单机 Docker Compose）

| 指标 | 目标值 |
|------|--------|
| 登录接口 P99 响应时间 | < 500ms |
| 工单列表 P99 响应时间 | < 1000ms |
| 并发 50 用户时错误率 | < 1% |

---

## 六、安全扫描（GitHub Actions）

### 6.1 自动触发条件

- **Bandit + pip-audit**：push 到 main/develop，PR 到 main
- **Trivy 容器扫描**：push 到 main（仅主分支）
- **CodeQL**：定时每周一 + PR

### 6.2 手动运行 Bandit

```bash
cd backend
pip install bandit[toml]
bandit -r app/ -x app/tests --severity-level medium --confidence-level medium
```

### 6.3 手动运行 pip-audit

```bash
pip install pip-audit
pip-audit --desc on
```

### 6.4 CI 通过标准

| 检查项 | 通过标准 |
|--------|----------|
| Bandit HIGH 级别 | 0 个 |
| Bandit MEDIUM 级别 | 仅警告，不阻断 |
| pip-audit 漏洞 | 仅警告，不阻断 |
| Trivy CRITICAL | 上传 SARIF 到 GitHub Security，不阻断 |

---

## 七、已知限制与后续计划

| 项目 | 当前状态 | 后续改进方向 |
|------|----------|-------------|
| 单元测试覆盖率 | 37.2%（目标 ≥ 60%） | Pack H 阶段增加 services/workflow、user、masking_rule 覆盖 |
| 集成测试隔离 | 使用共享测试 DB，无事务隔离 | 改为每个测试独立事务自动回滚 |
| 性能测试结果 | 尚未在 CI 中自动运行 | Pack H 阶段集成到 CI，设置性能回归门限 |
| E2E 浏览器测试 | 未实现 | 可选：Playwright 测试登录、工单提交全流程 |
