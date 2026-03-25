# SagittaDB 矢准数据 — 项目开发进度文档

> **项目路径：** `/Users/lynn/SynologyDrive/SynologyDrive/Code/SagittaDB`
> **重构基准：** Archery v1.14.0
> **文档版本：** v1.2 · 2026-03-25
> **状态说明：** ✅ 已完成并验证 · 🔧 已开发待测试 · 📋 待开发

---

## 一、项目概览

| 项目 | 内容 |
|---|---|
| 产品名称 | SagittaDB 矢准数据 |
| 品牌标语 | 矢向数据，精准管控 |
| 技术栈（后端） | FastAPI + SQLAlchemy 2.0 async + Celery 5 + PostgreSQL 16 |
| 技术栈（前端） | React 18 + TypeScript + Vite + Ant Design 5 |
| 引擎层 | EngineBase Protocol + sqlglot（替代 goInception 解析） |
| 可观测中心 | Prometheus + Alertmanager + Grafana |
| SaaS 预留 | 全部模型含 tenant_id，初期固定为 1 |
| 部署方式 | Docker Compose（开发/测试）/ K8s + Helm（生产预留）|

---

## 二、整体进度总览

| 阶段 | 内容 | 状态 | 完成度 |
|---|---|---|---|
| Sprint 0 | 项目骨架、基础设施 | ✅ | 100% |
| Sprint 1 | 认证、用户、实例管理 | ✅ | 100% |
| Sprint 2 | 引擎层、在线查询、查询权限 | ✅ | 100% |
| Pack A (S3+S4) | SQL 工单全流程 + 运维工具 | ✅ | 100% |
| Pack B (S5+S6) | 可观测中心 + 迁移脚本 | ✅ | 100% |
| Pack C1 | 系统配置、审计日志、资源组、个人设置 | ✅ | 100% |
| Pack C2 | 实例数据库注册管理 | ✅ | 100% |
| Pack D | 数据脱敏、数据字典、工单模板、AI Text2SQL | ✅ | 100% |
| Pack E | 多引擎补全、数据归档、SQL 回滚辅助、通知服务 | 🔧 | 85% |
| Pack F | 第三方登录（LDAP/钉钉/飞书/企微/OIDC） | 📋 | 0% |
| Pack G | 全链路测试、性能测试、安全扫描 | 📋 | 0% |
| 品牌升级 | SagittaDB 品牌 UI 全面更新 | ✅ | 100% |

**总体完成度：约 78%**

---

## 三、已完成功能详情

### Sprint 0 — 项目骨架 ✅

- FastAPI 应用结构（routers / services / models / engines / schemas）
- SQLAlchemy 2.0 async ORM + Alembic 迁移框架
- Celery 5 + Redis 异步任务队列
- React 18 + TypeScript + Vite + Ant Design 5 前端脚手架
- Docker Compose 多服务编排（backend / frontend / postgres / redis / celery / prometheus / grafana）
- Nginx 反向代理配置（含 WebSocket 支持）

### Sprint 1 — 认证与实例管理 ✅

**认证模块**
- JWT 双 Token（access + refresh）认证，自动刷新
- bcrypt + SHA-256 预处理密码哈希（规避 72 字节限制）
- TOTP 双因素认证（2FA 开启/关闭/验证）
- 密码修改接口

**用户权限**
- 用户 CRUD（创建/编辑/禁用/授权）
- 15 种细粒度权限码（sql_submit / sql_review / instance_manage 等）
- 超级管理员（is_superuser）跳过权限检查

**实例管理**
- 11 种数据库类型支持（MySQL/PgSQL/Oracle/MongoDB/Redis/ClickHouse/ES/MSSQL/Cassandra/Doris/TiDB）
- 实例 CRUD + 测试连接
- Fernet 对称加密存储密码字段
- SSH 隧道配置（跳板机连接）
- 实例数据库注册（Pack C2）：手动添加 + 从引擎自动同步，各数据库类型字段名称适配（Oracle=Schema，Redis=数据库编号）

**资源组管理**
- 资源组 CRUD
- 成员穿梭框管理（Transfer 组件）
- 钉钉/飞书 Webhook 配置

### Sprint 2 — 在线查询 ✅

- Monaco Editor 代码编辑器（SQL 语法高亮 + 自动补全）
- 在线查询执行（SELECT 限制，禁止 DDL/DML）
- 行数限制（默认 1000）
- 查询权限申请/审批流程
- 数据脱敏（sqlglot 解析所有方言，替代 goInception）：
  - 7 种内置规则（邮箱/手机号/银行卡/身份证/姓名/地址/自定义正则）
  - 按实例/数据库/表/列精确匹配
  - 实时预览脱敏效果

### Pack A — SQL 工单全流程 ✅

**工单核心**
- 工单提交（支持从工单模板快速套用）
- 9 种工单状态：待审核→审核通过→执行中→执行成功/异常/已取消
- AuditV2 审批流（支持多级审批）
- Celery 异步执行，WebSocket 实时进度推送
- SQL 预检查（sqlglot 解析，无需 goInception）

**工单模板（Pack D）**
- 模板 CRUD（公开/私有），使用次数统计
- 点击"使用"自动跳转提交页并填充 SQL

**AI Text2SQL（Pack D）**
- 调用 Anthropic Claude API
- 自动识别实例数据库类型生成对应方言 SQL
- 系统配置中配置 API Key

**运维工具**
- 会话管理（processlist / kill）
- 慢日志分析
- SQL 优化建议（sqlglot 规则）
- 数据字典（三级浏览：实例→数据库→表→字段结构）

### Pack B — 可观测中心 ✅

- Dashboard 统计（工单总数/执行成功/异常/各状态分布，自定义统计天数）
- 监控配置管理（Prometheus Exporter 配置）
- Prometheus + Grafana 集成
- Alertmanager 告警管理
- Prometheus SD（服务发现）端点

### Pack C1 — 系统管理 ✅

**系统配置**
- 7 个配置组：基础设置/邮件通知/钉钉通知/企业微信通知/飞书通知/LDAP 认证/AI 功能
- 敏感字段 Fernet 加密存储
- 各渠道连通性测试（邮件发送测试已验证）
- 配置保存后正确回填（包含敏感字段"已保存"提示）

**审计日志**
- 记录登录（成功/失败）、工单提交、工单审批、配置修改
- 敏感配置变更记录具体字段名（不记录值）
- 支持按操作类型/模块/时间范围筛选

**个人设置**
- 修改密码（当前密码验证）
- 2FA 设置向导

### Pack D — 数据安全与效率工具 ✅

| 功能 | 状态 |
|---|---|
| 数据脱敏规则管理页面（实时预览） | ✅ |
| 数据字典（三级浏览：实例→库→表→字段） | ✅ |
| 工单模板（公开/私有，使用次数统计） | ✅ |
| AI Text2SQL（Claude API，多方言适配） | ✅ |

### Pack E — 引擎补全与高级工具 🔧

**多引擎实现**
| 引擎 | 状态 | 说明 |
|---|---|---|
| MySQL | ✅ | 完整实现 |
| PostgreSQL | ✅ | 完整实现 |
| Oracle | ✅ | 骨架已有，需真实环境验证 |
| MongoDB | ✅ | 完整实现（含 processlist / metrics） |
| Redis | ✅ | 白名单安全控制，16 数据库，INFO 指标 |
| ClickHouse | ✅ | clickhouse-connect HTTP 协议 |
| Elasticsearch | 🔧 | 骨架已有 |
| MSSQL | 🔧 | 骨架已有 |
| Cassandra | 🔧 | 骨架已有 |
| Doris | 🔧 | 骨架已有 |

**数据归档**
- 全数据库支持矩阵（不支持的返回明确提示）
- purge 模式：分批删除，各数据库语法适配
- dest 模式：跨实例迁移（INSERT + DELETE）
- dry_run 预估影响行数（默认开启）
- 前端三步引导（配置→估算→确认执行）

**SQL 回滚辅助**
- sqlglot 静态逆向 SQL 生成（INSERT↔DELETE↔UPDATE）
- MySQL/TiDB：my2sql 命令生成器
- PostgreSQL：WAL 查询语句生成
- 各数据库回滚方案说明文档

**通知服务**
- 钉钉/企微/飞书三渠道并发通知
- 已接入工单提交和审批节点
- 签名验证（钉钉 HMAC-SHA256）

### 品牌升级 ✅

- 产品名：`数据库管理平台 2.0` → `SagittaDB 矢准数据`
- 主色：`#1558A8` → `#165DFF`（Space Tech Blue）
- 深色背景：`#0A2540` → `#0F172A`（Tech Charcoal）
- 字体：系统字体栈 → Inter + Noto Sans SC + JetBrains Mono
- Logo：六边形矢标 SVG（明暗双版）
- 登录页：深色 Hero 风格（背景光晕 + 网格纹理 + 磨砂玻璃卡片）
- 第三方登录入口：LDAP/OIDC/钉钉/飞书/企微（跳转预留，待后端接入）
- Favicon 更新

---

## 四、待开发功能（Pack F+）

### Pack F — 第三方登录集成 📋

| 功能 | 优先级 | 工作量 | 说明 |
|---|---|---|---|
| LDAP 登录 | P0 | 2天 | 企业内网必备，python-ldap 接入 |
| 钉钉扫码登录 | P1 | 2天 | 需在钉钉开放平台注册应用 |
| 飞书 OAuth 登录 | P1 | 2天 | 需注册飞书应用 |
| 企业微信登录 | P2 | 2天 | 需企业微信管理员配置 |
| OIDC 通用 SSO | P2 | 2天 | 对接 Keycloak/Okta/Azure AD |

### Pack G — 质量保障 📋

| 功能 | 优先级 | 说明 |
|---|---|---|
| 单元测试（pytest） | P0 | 覆盖 core/services 层，目标覆盖率 ≥ 70% |
| 接口集成测试 | P0 | 主流程 E2E 测试 |
| 性能测试（Locust） | P1 | 并发查询 / 工单执行压测 |
| 安全扫描（Bandit/Trivy） | P1 | SAST + 容器镜像扫描 |
| Archery 1.x 数据迁移工具 | P2 | 迁移脚本已有骨架，需完整测试 |

### Pack H — 生产就绪 📋

| 功能 | 优先级 | 说明 |
|---|---|---|
| Helm Chart | P0 | K8s 生产部署配置 |
| CI/CD 流水线 | P0 | GitHub Actions / GitLab CI |
| 多环境配置管理 | P1 | dev/staging/prod 环境隔离 |
| 备份策略文档 | P1 | PostgreSQL 定时备份 |
| SaaS 多租户激活 | P2 | tenant_id 已预留，激活需额外开发 |

---

## 五、已知问题与技术债

| 问题 | 严重级别 | 说明 |
|---|---|---|
| Celery Worker 健康检查 unhealthy | 低 | 无 HTTP 健康检查端点，功能正常但状态显示异常 |
| Oracle/MSSQL/Cassandra/ES 引擎未全量验证 | 中 | 骨架已实现，需真实环境测试 |
| Alembic 迁移文件需手动执行 | 低 | 新建表均有对应 SQL 脚本，需补充 CI 自动执行 |
| totp_secret 字段已扩展至 500 | 已修复 | 原 100 字节不足，已通过 ALTER TABLE 修复 |
| 第三方登录按钮点击无实际跳转 | 中 | 前端入口已预留，后端 OAuth 待 Pack F 实现 |

---

## 六、Hotfix 记录摘要

| 编号 | 修复内容 |
|---|---|
| hotfix1~5 | docker-compose 位置、Alpine 镜像、structlog→logging、语法错误、alembic 同步 |
| hotfix6~10 | exceptions 关键字参数、user.py PG INSERT ON CONFLICT、security.py bcrypt 直调、registry instanceof 移除 |
| hotfix11~15 | frontend Dockerfile 两阶段构建、tsconfig strict 关闭、App.tsx 路由修复、MainLayout 布局重构、AuthGuard 修复 |
| hotfix16~19 | 工单状态语义、docker-compose frontend 挂载方式、WorkflowList 状态选项 |
| packC1_hotfix | totp_secret 扩展、审计日志写入、资源组 Transfer 穿梭框 |
| packC1_hotfix2 | system_config update_batch 返回 change_summary、表单回填 useEffect 修复 |
| packC2_hotfix | instance.py TunnelService import 修复 |
| packD_hotfix | WorkflowSubmit Modal 未 import、MainLayout/App 菜单路由未更新 |
| packD_hotfix2 | WorkflowSubmit extra prop AI 按钮插入修复 |
| packE_request_import | workflow.py router 缺少 Request import |
| brand_hotfix1~2 | LoginPage login 方法不存在、/auth/me/ token 时序问题 |
| brand_hotfix_password | bcrypt 哈希算法 hexdigest→base64 修正 |

---

## 七、关键技术决策记录

| 决策 | 内容 |
|---|---|
| 密码哈希 | bcrypt 直接调用 + SHA-256 + base64 预处理（规避 72 字节限制） |
| 字段加密 | Fernet 对称加密（cryptography 库） |
| SQL 解析 | sqlglot 替代 goInception（支持 20+ 方言，零外部进程依赖） |
| 工单状态 | 整数枚举 0-8（0=待审核，6=成功，7=异常，8=取消） |
| 数据库注册 | instance_database 表解耦实例连接与数据库名，Oracle=Schema，Redis=数字索引 |
| 归档实现 | 纯 Python 通过引擎层执行，不依赖 pt-archiver，各数据库分批语法独立适配 |
| Binlog 回滚 | 重定位为"SQL 回滚辅助"，my2sql 做命令生成器而非直接执行 |
| 品牌主色 | #165DFF（Space Tech Blue，ARCO Design 标准色） |

---

*文档最后更新：2026-03-25 · SagittaDB v1.0-beta*
