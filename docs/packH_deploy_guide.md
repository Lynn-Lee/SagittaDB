# Pack H 部署说明文档

> **版本：** v1.0 · 2026-03-25
> **适用范围：** SagittaDB 生产环境部署

---

## 一、快速部署（Docker Compose 生产模式）

适用于单机或小规模 VPS 部署。

```bash
# 1. 复制并修改生产环境变量
cp .env.example .env
# 修改以下必填项：
#   SECRET_KEY      — 随机 32+ 字符字符串
#   FERNET_KEY      — 用 python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 生成
#   POSTGRES_PASSWORD / REDIS_PASSWORD — 改为强密码

# 2. 以生产模式启动（合并 override 文件）
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 3. 执行数据库迁移
docker compose exec backend alembic upgrade head

# 4. 验证服务状态
docker compose ps
curl http://localhost:8000/health
```

主要区别（对比开发模式）：
- 不挂载本地代码目录，使用镜像内置代码
- uvicorn 使用 4 个 worker 进程，不开 `--reload`
- 所有容器设置 CPU/Memory 资源限制

---

## 二、Kubernetes 部署（Helm Chart）

### 2.1 前置条件

```bash
# 安装 Helm
brew install helm  # macOS
# 或: curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# 添加 Bitnami 仓库（PostgreSQL/Redis 子 chart）
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
```

### 2.2 本地开发/测试（内置 PostgreSQL + Redis）

```bash
cd deploy/helm/sagittadb

# 安装依赖 chart
helm dependency update

# 安装到 default namespace
helm upgrade --install sagittadb . \
  --set app.secretKey="$(openssl rand -hex 32)" \
  --set app.fernetKey="$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')" \
  --namespace sagittadb \
  --create-namespace

# 查看状态
kubectl get pods -n sagittadb
helm status sagittadb -n sagittadb
```

### 2.3 Staging 环境

```bash
helm upgrade --install sagittadb . \
  -f values-staging.yaml \
  --set app.secretKey="$SECRET_KEY" \
  --set app.fernetKey="$FERNET_KEY" \
  --namespace sagittadb-staging \
  --create-namespace
```

### 2.4 生产环境（外部 RDS + ElastiCache）

```bash
helm upgrade --install sagittadb . \
  -f values-prod.yaml \
  --set app.secretKey="$SECRET_KEY" \
  --set app.fernetKey="$FERNET_KEY" \
  --set externalDatabase.host="$RDS_HOST" \
  --set externalDatabase.password="$DB_PASSWORD" \
  --set externalRedis.host="$REDIS_HOST" \
  --set externalRedis.password="$REDIS_PASSWORD" \
  --namespace sagittadb \
  --create-namespace \
  --atomic \
  --timeout 10m
```

**生产注意事项：**
- 使用 [Sealed Secrets](https://github.com/bitnami-labs/sealed-secrets) 或 [External Secrets Operator](https://external-secrets.io/) 管理密钥，不要在命令行明文传递
- `values-prod.yaml` 已配置 HPA（backend: 3~12 副本，worker: 3~20 副本）
- Celery Beat 副本固定为 1，防止定时任务重复触发
- initContainer 会在每次部署时自动运行 `alembic upgrade head`

### 2.5 Helm Chart 结构

```
deploy/helm/sagittadb/
├── Chart.yaml                    # Chart 元信息 + bitnami 依赖声明
├── values.yaml                   # 默认值（开发/测试）
├── values-staging.yaml           # Staging 环境覆盖
├── values-prod.yaml              # 生产环境覆盖（外部 DB，HPA 开启）
└── templates/
    ├── _helpers.tpl              # 公共模板函数
    ├── configmap.yaml            # 非敏感环境变量
    ├── secret.yaml               # 敏感环境变量（自动拼接 DB/Redis URL）
    ├── serviceaccount.yaml       # ServiceAccount
    ├── pvc.yaml                  # 下载文件持久化存储
    ├── backend-deployment.yaml   # FastAPI（含 alembic initContainer）
    ├── backend-service.yaml      # ClusterIP Service
    ├── worker-deployment.yaml    # Celery Worker + Celery Beat
    ├── flower-deployment.yaml    # Flower 监控（可选）
    ├── frontend-deployment.yaml  # Nginx 前端 + Service
    ├── ingress.yaml              # Ingress（支持 TLS + cert-manager）
    ├── hpa.yaml                  # HPA（backend + worker）
    └── NOTES.txt                 # 部署后提示
```

---

## 三、数据库备份

### 3.1 手动备份

```bash
# Docker Compose 环境
export POSTGRES_HOST=localhost
export POSTGRES_PASSWORD=your_password
./deploy/backup/backup-postgres.sh

# Kubernetes 环境（通过 kubectl exec）
kubectl exec -n sagittadb deploy/sagittadb-backend -- \
  pg_dump -h $DB_HOST -U archery archery | gzip > backup_$(date +%Y%m%d).sql.gz
```

### 3.2 定时备份（Cron）

```bash
# 每天凌晨 2 点备份，保留 7 天，并上传 S3
0 2 * * * POSTGRES_HOST=localhost \
          POSTGRES_PASSWORD=xxx \
          S3_BUCKET=my-sagittadb-backups \
          /opt/sagittadb/deploy/backup/backup-postgres.sh >> /var/log/sagittadb-backup.log 2>&1
```

### 3.3 数据恢复

```bash
# 从本地文件恢复
POSTGRES_HOST=localhost POSTGRES_PASSWORD=xxx \
./deploy/backup/restore-postgres.sh /var/backups/sagittadb/sagittadb_archery_20260101_020000.sql.gz

# 从 S3 恢复
POSTGRES_HOST=localhost POSTGRES_PASSWORD=xxx \
./deploy/backup/restore-postgres.sh s3://my-bucket/sagittadb/db/sagittadb_archery_20260101.sql.gz
```

---

## 四、CI/CD 流水线

`.github/workflows/ci.yml` 包含以下阶段：

| Job | 触发条件 | 说明 |
|-----|---------|------|
| `backend-test` | push/PR | Python 单元测试 + 集成测试（覆盖率 ≥ 35%）|
| `frontend-test` | push/PR | TypeScript 类型检查 + ESLint + Vite build |
| `docker-build` | main push | Docker 镜像构建验证 |
| `docker-publish` | main push | 构建并推送到 GHCR（ghcr.io/org/sagittadb-*）|
| `helm-lint` | push/PR | Helm chart lint（3 套 values）+ template render |
| `security` | main push/PR/weekly | Bandit SAST + pip-audit + Trivy + CodeQL |

### 镜像标签策略

每次 push main：
- `ghcr.io/your-org/sagittadb-backend:latest`
- `ghcr.io/your-org/sagittadb-backend:<git-sha>`（7 位）
- `ghcr.io/your-org/sagittadb-frontend:latest`
- `ghcr.io/your-org/sagittadb-frontend:<git-sha>`

### 配置 GITHUB_TOKEN 权限

仓库 Settings → Actions → General → Workflow permissions：
勾选 "Read and write permissions"，或在 `docker-publish` job 中已声明 `packages: write`。

---

## 五、生成强密钥

```bash
# SECRET_KEY（Django/FastAPI JWT 签名密钥）
openssl rand -hex 32

# FERNET_KEY（Fernet 对称加密，字段加密用）
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## 六、多环境环境变量对比

| 变量 | 开发 | Staging | 生产 |
|------|------|---------|------|
| `APP_ENV` | development | staging | production |
| `DEBUG` | true | false | false |
| `LOG_LEVEL` | DEBUG | DEBUG | WARNING |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 60 | 60 | 30 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | 7 | 7 | 3 |
| PostgreSQL | 容器内 | 容器内 | RDS（托管）|
| Redis | 容器内 | 容器内 | ElastiCache（托管）|
