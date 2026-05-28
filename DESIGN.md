# 多模态新闻驱动型股价预测系统 V4.0 — 系统架构设计文档

> **文档状态**：已完成 | **最后更新**：2026-05-28

---

## 一、项目背景与目标

### 1.1 背景

金融文本（新闻、公告、社交媒体）中包含影响股价的重要信号。传统单机研究脚本难以支撑多人协作、实时交互与长期稳定运行。

### 1.2 核心目标

构建一个集**多模态预测、实时交互、自动化运维**于一体的全栈 AI 系统。通过"影子模式"与实时股市对比，验证模型有效性，并确保系统在生产环境中的高可用性。

### 1.3 非目标（明确边界）

- 不做实盘自动交易（影子模式仅做模拟对比）
- 不做 LLM 全参数微调（LLM 仅作为特征提取器）
- 不追求毫秒级实时预测（T+1 日级别预测即可）

---

## 二、系统技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                     前端交互层                                │
│  原型阶段：Streamlit         生产阶段：React + TypeScript     │
│  职责：搜索 | K线可视化 | 情感热力图 | 预测结果渲染           │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP/WebSocket
┌──────────────────────────▼──────────────────────────────────┐
│                     后端服务层 (FastAPI)                      │
│  职责：RESTful API | WebSocket | 请求协调 | 权限/限流         │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              智能计算与任务队列层 (Celery + Redis)             │
│  职责：异步爬虫 | LLM 特征抽取 | 模型推理 | 定时任务          │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                        数据存储层                              │
│  PostgreSQL + pgvector  │  MinIO/本地FS  │  Redis            │
│  (股价/新闻/特征/向量)   │  (原始文本/日志) │  (队列/缓存)     │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                     运维监控层                                 │
│  Docker Compose | Prometheus | Grafana | Loki + Promtail     │
└─────────────────────────────────────────────────────────────┘
```

### 2.1 技术选型说明

| 组件 | 选型 | 备选/替代 | 选型理由 |
|------|------|-----------|----------|
| 前端(原型) | Streamlit | — | 纯 Python，数据科学家可独立迭代 |
| 前端(生产) | React + TypeScript + Shadcn UI | — | 组件化、类型安全、社区活跃 |
| 后端 | FastAPI | — | 原生异步、自动 OpenAPI 文档、生态完善 |
| 任务队列 | Celery + Redis | — | Python 生态标准方案，成熟稳定 |
| 关系数据库 | PostgreSQL 15+ | — | 支持 pgvector，一站式解决结构化+向量存储 |
| 向量存储 | pgvector | ~~Milvus~~ | 零额外运维，检索量不大时完全够用 |
| 日志收集 | Loki + Promtail | ~~ELK~~ | 轻量（约为 ELK 资源占用的 1/5），与 Grafana 原生集成 |
| 指标监控 | Prometheus + Grafana | — | 行业标准，社区 dashboard 丰富 |
| 容器化 | Docker Compose | K8s(后续) | 单机部署够用，后续可平滑迁移 K8s |
| LLM 推理 | Qwen2.5-7B-Instruct (GPTQ-Int4) | 云端 API fallback | 成本可控，断网可用 |
| 模型优化 | ONNX Runtime | TorchScript | 跨平台、推理快、生态好 |

### 2.2 硬件要求

| 环境 | 最低配置 | 推荐配置 |
|------|----------|----------|
| 开发机 | 16GB RAM, 8GB VRAM | 32GB RAM, 12GB+ VRAM |
| 生产服务器 | 32GB RAM, 12GB VRAM | 64GB RAM, 24GB VRAM |
| LLM 推理 | GPU 支持 bf16 | NVIDIA RTX 3060 12GB+ |

> Qwen2.5-7B-Int4 推理约需 6GB VRAM。若无 GPU，系统自动 fallback 到云端 API（需配置 API Key）。

---

## 三、五阶段执行计划

### 阶段 0：环境初始化与工具链（Week 0，可并行）

**目标**：建立开发规范与 CI 基础，从第 0 天保证代码质量。

| # | 任务 | 产出 |
|---|------|------|
| 0.1 | 初始化 Git 仓库，配置 `.gitignore`, `.env.example` | 仓库就绪 |
| 0.2 | 搭建 Python 虚拟环境，锁定依赖（`pyproject.toml` 或 `requirements.txt`） | 可复现环境 |
| 0.3 | 配置 `ruff`（lint）+ `mypy`（type check）+ `pytest`（test） | 代码质量门禁 |
| 0.4 | 编写 `docker-compose.yml` 骨架（PostgreSQL + Redis） | 本地开发基础设施 |
| 0.5 | 建立项目目录结构（见附录 A） | 统一代码组织 |

---

### 阶段 1A：后端骨架与数据模型（Week 1–2）

**目标**：FastAPI 可启动，数据库表结构就绪，Swagger 文档可访问。

| # | 任务 | 产出 |
|---|------|------|
| 1A.1 | 初始化 FastAPI 项目结构，配置 CORS、异常处理器、日志 | 可启动服务 |
| 1A.2 | 用 SQLAlchemy 定义 ORM 模型（Stock, News, SentimentFeature, Prediction, DailyShadow） | 数据库 schema |
| 1A.3 | 编写 Alembic 迁移脚本，执行 `alembic upgrade head` | 表创建完成 |
| 1A.4 | 实现 CRUD 基础接口：`GET /stocks/{code}`, `GET /news/{stock_code}` | Swagger 可交互 |
| 1A.5 | 编写数据库模型单元测试（pytest + 测试用 PostgreSQL） | CI 可运行 |

**阶段 1A 验收标准**：
- `docker compose up` 后 FastAPI 可访问 `http://localhost:8000/docs`
- Swagger 中可执行基础 CRUD 操作
- `pytest` 全部通过

---

### 阶段 1B：数据获取与清洗管线（Week 2–3）

**目标**：可自动化获取股价与新闻数据，经清洗对齐后写入数据库。

| # | 任务 | 产出 |
|---|------|------|
| 1B.1 | 接入 AkShare 获取 A 股日线数据（OHLCV），失败时 fallback Tushare | 股价数据源 |
| 1B.2 | 实现财经新闻爬虫（东方财富 / 新浪财经），内置去重（基于 URL + 标题 hash） | 新闻数据源 |
| 1B.3 | 编写时间对齐校验脚本："T 日数据仅包含 ≤T 日信息"（无未来函数检测） | 数据质量保证 |
| 1B.4 | 封装为 Celery 定时任务：每个交易日 15:30 自动触发数据更新 | 自动化数据流 |
| 1B.5 | 数据管线单元测试（mock 外部 API） + 对齐脚本集成测试 | 管线可靠性 |

**阶段 1B 验收标准**：
- 至少覆盖 50 只沪深 300 成分股，时间跨度 ≥2 年
- 对齐校验脚本无报错（或准确标记违规样本）
- Celery worker 独立运行，任务状态可在 Flower 面板查看

---

### 阶段 2：LLM 特征工程与异步任务（Week 4–5）

**目标**：稳定、低成本的文本特征提取管线，结构化输出无误。

| # | 任务 | 产出 |
|---|------|------|
| 2.1 | 实现双模态推理路由器：优先本地 Qwen2.5-7B-Int4，超时/不可用时 fallback 云端 API | 推理可靠性 |
| 2.2 | 设计 Prompt 模板（提取 `event_type`, `sentiment_score`, `intensity`, `relevance`） | 特征 schema |
| 2.3 | Celery 任务封装 LLM 调用，增加：结构化输出校验（Pydantic）、指数退避重试（max 3 次）、超时熔断（30s） | 任务鲁棒性 |
| 2.4 | 特征写入 `sentiment_features` 表，建立与 `news` 表的外键关联 | 特征存储 |
| 2.5 | 批量处理验证：提交 1000 条历史新闻，统计成功率、平均延迟、格式错误率 | 管线压测 |

**阶段 2 验收标准**：
- 批量任务成功率 ≥95%，结构化输出格式错误率 <1%
- 单条新闻推理延迟：本地模型 <5s，云端 API <3s
- Flower 面板可实时查看任务执行状态与错误堆栈

---

### 阶段 3：建模、评估与 API 化（Week 6–8）

**目标**：训练好的预测模型封装为高并发 API，推理延迟可控。

| # | 任务 | 产出 |
|---|------|------|
| 3.1 | 特征工程：构造数值特征（技术指标 MA/MACD/RSI）+ 文本特征（情感/强度/事件类型 one-hot） | 特征矩阵 |
| 3.2 | 训练 LightGBM 基线模型 + Transformer 主模型（含时间序列交叉验证） | 模型权重 |
| 3.3 | 消融实验矩阵：逐一移除情感/强度/事件类型特征，度量 AUC 下降 | 特征重要性报告 |
| 3.4 | 时间随机打乱实验：打乱时间序列后重新训练，验证因果性（AUC 应显著下降） | 因果性验证 |
| 3.5 | 模型导出为 ONNX 格式，用 MLflow 记录实验参数/指标/模型文件 | 模型资产管理 |
| 3.6 | 实现 `/predict` 接口：输入股票代码 → 返回涨跌概率 + Top-3 归因因子 + 置信度 | 预测 API |
| 3.7 | 模型热加载：FastAPI 启动时加载 ONNX 模型到内存，支持 `POST /admin/reload-model` | 运维便利 |

**阶段 3 验收标准**：
- `/predict` 接口 P99 延迟 ≤ 300ms（不含 LLM 调用，LLM 特征已预计算）
- 离线 AUC ≥ 0.55（金融预测领域的务实基线），消融实验证实文本特征贡献
- MLflow UI 可查看所有实验记录

---

### 阶段 4：前端交互与实时看板（Week 9–11）

**目标**：构建可视化的"影子模式"交互界面。

| # | 任务 | 产出 |
|---|------|------|
| 4.1 | 使用 Streamlit 快速搭建原型看板（搜索、K 线、新闻列表、预测卡片） | 可交互原型 |
| 4.2 | 实现影子模式自动化：交易日 15:30 自动抓取 → 特征提取 → 推理 → 写入 `daily_shadow` 表 | 每日自动预测 |
| 4.3 | 次日收盘后实时对比：自动拉取真实股价，计算`预测 vs 实际`，前端高亮胜率与偏差 | 模型验证闭环 |
| 4.4 | 若时间允许，启动 React + TypeScript + Shadcn UI 重写（替代 Streamlit 原型） | 生产级前端 |
| 4.5 | 前端集成 ECharts 或 TradingView Lightweight Charts 实现交互式 K 线（含成交量+预测标记） | 专业图表 |

**阶段 4 验收标准**：
- 浏览器可流畅查看历史回测曲线与最近 N 日预测 vs 实际对比
- 影子模式连续运行 ≥5 个交易日无人工干预
- 页面加载时间 <3s（首屏）

---

### 阶段 5：运维、监控与交付（Week 12–14）

**目标**：系统可在生产环境稳定运行，具备完善的监控与告警。

| # | 任务 | 产出 |
|---|------|------|
| 5.1 | 编写 Dockerfile（FastAPI, Celery Worker, Streamlit/React） + 统一 `docker-compose.yml` | 一键部署 |
| 5.2 | Prometheus 采集指标：API 请求量/延迟/错误率、Celery 队列长度、DB 连接池 | 指标采集 |
| 5.3 | Grafana 运维大屏：CPU/内存/GPU 占用率、API P99 延迟、每日预测胜率趋势 | 运维看板 |
| 5.4 | 告警规则：API 错误率 >5%、Celery 积压 >100、预测胜率连续 5 日低于随机 | 自动告警 |
| 5.5 | Loki + Promtail 集中收集日志，Grafana 内按 trace_id 串联请求链路 | 日志查询 |
| 5.6 | 数据库自动备份脚本（每日全量 + WAL 归档），保留最近 7 天 | 数据安全 |
| 5.7 | 输出文档：API 接口文档（Swagger 自动生成）、部署运维手册、故障排查指南 | 知识交付 |

**阶段 5 验收标准**：
- `docker compose up -d` 一键启动全部服务
- 模拟 100 QPS 并发请求持续 5 分钟，API 错误率 <1%
- Grafana 大屏指标实时更新，告警规则可触发

---

## 四、关键实验设计

### 4.1 时间随机打乱实验（验证时序因果性）

将训练集的日期索引随机打乱后重新训练，若模型确实捕捉了时序因果关系（而非统计伪相关），打乱后 AUC 应显著下降。

### 4.2 消融实验矩阵

| 实验编号 | 数值特征 | 情感得分 | 事件强度 | 事件类型 | 预期 AUC |
|----------|----------|----------|----------|----------|----------|
| E0 | ✅ | ❌ | ❌ | ❌ | 基线（纯量价） |
| E1 | ✅ | ✅ | ❌ | ❌ | E0 + 情感增益 |
| E2 | ✅ | ✅ | ✅ | ❌ | E1 + 强度增益 |
| E3 | ✅ | ✅ | ✅ | ✅ | 全特征（预期最优） |

每个实验重复 5 折时间序列交叉验证，报告 AUC 均值 ± 标准差。

---

## 五、数据库核心表设计

```sql
-- 股票基础信息
CREATE TABLE stocks (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) NOT NULL UNIQUE,       -- 如 600519.SH
    name VARCHAR(50) NOT NULL,
    industry VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 日线行情
CREATE TABLE daily_prices (
    id SERIAL PRIMARY KEY,
    stock_id INT REFERENCES stocks(id),
    trade_date DATE NOT NULL,
    open DECIMAL(10,2), high DECIMAL(10,2), low DECIMAL(10,2),
    close DECIMAL(10,2), volume BIGINT,
    UNIQUE(stock_id, trade_date)
);

-- 新闻
CREATE TABLE news (
    id SERIAL PRIMARY KEY,
    stock_id INT REFERENCES stocks(id),
    title TEXT NOT NULL,
    content TEXT,
    source VARCHAR(100),
    url TEXT,
    publish_time TIMESTAMP NOT NULL,
    title_hash VARCHAR(64) UNIQUE,          -- 去重
    fetched_at TIMESTAMP DEFAULT NOW()
);

-- LLM 情感特征
CREATE TABLE sentiment_features (
    id SERIAL PRIMARY KEY,
    news_id INT REFERENCES news(id) UNIQUE,
    event_type VARCHAR(50),                 -- 如 earnings/merger/policy
    sentiment_score DECIMAL(4,3),           -- [-1, 1]
    intensity DECIMAL(4,3),                 -- [0, 1]
    relevance DECIMAL(4,3),                 -- [0, 1] 与目标股票相关度
    raw_llm_response JSONB,                 -- 原始输出（调试用）
    model_version VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 每日影子预测
CREATE TABLE daily_shadow (
    id SERIAL PRIMARY KEY,
    stock_id INT REFERENCES stocks(id),
    predict_date DATE NOT NULL,             -- 预测生成日期
    target_date DATE NOT NULL,              -- 预测的目标交易日
    predicted_prob DECIMAL(5,4),            -- 上涨概率
    predicted_label VARCHAR(4),             -- up/down
    confidence DECIMAL(4,3),
    top_factors JSONB,                      -- [{factor, weight}]
    actual_close DECIMAL(10,2),             -- 实际收盘价（T+1 后回填）
    is_correct BOOLEAN,                     -- 预测是否正确
    model_version VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(stock_id, target_date, model_version)
);
```

---

## 六、风险与应对

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|----------|
| **API 调用成本过高** | 中 | 高 | 动态路由：优先本地 Qwen2.5-7B-Int4，仅高置信度需求走云端。按月设置预算上限 |
| **新闻爬虫被反爬** | 高 | 中 | 多数据源互为备份；降低爬取频率；使用 Playwright 模拟浏览器 |
| **本地 LLM 不可用（无 GPU）** | 中 | 中 | 自动 fallback 云端 API；开发阶段可直接用云端 |
| **系统单点故障** | 中 | 高 | Docker Compose 服务隔离；PostgreSQL 每日自动备份 + WAL 归档 |
| **模型性能衰减** | 高 | 高 | 监控"预测胜率漂移"，连续 5 日低于基线时自动告警；定期重训练 |
| **高并发阻塞** | 中 | 中 | Redis 队列削峰填谷；对 `/predict` 接口实施令牌桶限流 |
| **数据质量问题（未来函数）** | 高 | 极高 | 专门的时间对齐校验脚本 + 集成测试，作为数据管线的强制门禁 |

---

## 七、项目产出清单

- [ ] **后端代码**：FastAPI + Celery 完整微服务源码
- [ ] **前端代码**：Streamlit 原型 + React/TypeScript 生产版
- [ ] **模型资产**：LightGBM + Transformer 权重、ONNX 推理文件、MLflow 实验记录
- [ ] **运维脚本**：Docker Compose 编排、Prometheus 配置、Grafana Dashboard JSON
- [ ] **文档**：API 文档（Swagger 自动生成）、系统架构设计文档（本文件）、部署运维手册

---

## 附录 A：推荐项目目录结构

```
2212/
├── backend/
│   ├── app/
│   │   ├── api/              # 路由层
│   │   │   ├── v1/
│   │   │   │   ├── stocks.py
│   │   │   │   ├── news.py
│   │   │   │   ├── predict.py
│   │   │   │   └── admin.py
│   │   │   └── deps.py       # 依赖注入（DB session, 限流）
│   │   ├── core/
│   │   │   ├── config.py     # Pydantic Settings
│   │   │   ├── security.py   # API Key 验证
│   │   │   └── exceptions.py
│   │   ├── models/           # SQLAlchemy ORM
│   │   │   ├── stock.py
│   │   │   ├── news.py
│   │   │   └── prediction.py
│   │   ├── schemas/          # Pydantic 请求/响应模型
│   │   ├── services/         # 业务逻辑
│   │   │   ├── data_fetcher.py
│   │   │   ├── llm_router.py
│   │   │   └── predictor.py
│   │   ├── tasks/            # Celery 任务
│   │   │   ├── crawler.py
│   │   │   ├── sentiment.py
│   │   │   └── shadow.py
│   │   └── main.py           # FastAPI 入口
│   ├── alembic/              # 数据库迁移
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── streamlit_app/        # 原型
│   │   └── main.py
│   └── react-app/            # 生产版
│       ├── src/
│       └── package.json
├── models/                   # ML 训练脚本
│   ├── train_lightgbm.py
│   ├── train_transformer.py
│   └── export_onnx.py
├── ops/
│   ├── docker-compose.yml
│   ├── prometheus/
│   │   └── prometheus.yml
│   ├── grafana/
│   │   └── dashboards/
│   └── loki/
│       └── loki-config.yml
├── scripts/
│   ├── time_alignment_check.py
│   └── db_backup.sh
├── .env.example
├── .gitignore
├── DESIGN.md                  # 本文件
└── README.md
```

---

## 附录 B：开发环境快速启动

```bash
# 1. 克隆仓库
git clone <repo-url> && cd 2212

# 2. 复制环境变量
cp .env.example .env  # 编辑填入 API Key 等

# 3. 启动基础设施
docker compose -f ops/docker-compose.yml up -d postgres redis

# 4. 安装 Python 依赖
cd backend && pip install -r requirements.txt

# 5. 运行数据库迁移
alembic upgrade head

# 6. 启动后端
uvicorn app.main:app --reload --port 8000

# 7. 启动 Celery Worker（新终端）
celery -A app.tasks worker --loglevel=info

# 8. 启动 Streamlit 原型（新终端）
cd frontend/streamlit_app && streamlit run main.py
```

---

*本文档随项目迭代持续更新。架构决策记录（ADR）请见 `docs/adr/` 目录。*
