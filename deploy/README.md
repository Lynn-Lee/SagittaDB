# Deploy — 部署配置

## 快速启动（开发 / 私有化部署）

```bash
# 1. 进入项目根目录
cd /path/to/archery2.0

# 2. 复制并配置环境变量
cp .env.example .env
# 修改 .env 中的密码等敏感配置

# 3. 启动所有服务
docker compose -f deploy/docker-compose.yml up -d

# 4. 执行数据库初始化迁移
docker compose -f deploy/docker-compose.yml exec backend alembic upgrade head

# 5. 访问
#   前端：        http://localhost
#   后端 API 文档：http://localhost:8000/docs
#   Grafana：     http://localhost:3000  (admin/admin)
#   Flower：      http://localhost:5555
#   Prometheus：  http://localhost:9090
```

## 服务说明

| 服务 | 端口 | 说明 |
|---|---|---|
| frontend | 80 | Nginx 静态文件 + API 反代 |
| backend | 8000 | FastAPI 应用 |
| celery_worker | - | SQL 执行、通知异步任务 |
| celery_beat | - | 定时任务调度 |
| flower | 5555 | Celery 任务监控 |
| postgres | 5432 | PostgreSQL 16 元数据库 |
| redis | 6379 | Redis 7 缓存/消息队列 |
| prometheus | 9090 | 指标采集存储 |
| alertmanager | 9093 | 告警路由 |
| grafana | 3000 | 可视化面板 |

## Prometheus 服务发现

平台提供 HTTP SD 端点，Prometheus 自动发现数据库实例：

```yaml
# deploy/prometheus/prometheus.yml 已配置
scrape_configs:
  - job_name: archery_db_monitor
    http_sd_configs:
      - url: http://backend:8000/internal/prometheus/sd-targets
        refresh_interval: 30s
```

DBA 在平台页面添加实例采集配置后，无需重启 Prometheus，30 秒内自动生效。

## K8s 部署（生产）

```bash
# 使用 Helm
helm install archery ./deploy/helm/archery \
  --namespace archery \
  --create-namespace \
  --values deploy/helm/archery/values.yaml \
  --set backend.env.SECRET_KEY=your-secret-key
```

## 目录结构

```
deploy/
├── docker-compose.yml      开发/私有化部署
├── nginx.conf              Nginx 反代配置
├── prometheus/
│   ├── prometheus.yml      Prometheus 采集配置
│   ├── alertmanager.yml    告警路由配置
│   └── rules/
│       └── db_alerts.yml   10 条默认告警规则
├── grafana/
│   └── provisioning/       Grafana 预置 Dashboard（Sprint 5）
└── helm/
    └── archery/            K8s Helm Chart
```
