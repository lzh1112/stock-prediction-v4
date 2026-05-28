# 多模态新闻驱动型股价预测系统 V4.0

基于 LLM 特征提取 + 多模态机器学习的股价预测系统。通过"影子模式"与实时股市对比，验证模型有效性。

## 快速启动

```bash
# 1. 环境准备
cp .env.example .env          # 编辑填入配置
docker compose -f ops/docker-compose.yml up -d postgres redis

# 2. 后端
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# 3. Celery Worker (新终端)
celery -A app.tasks worker --loglevel=info

# 4. 前端原型 (新终端)
cd frontend/streamlit_app
streamlit run main.py
```

## 架构文档

详见 [DESIGN.md](./DESIGN.md)

## 目录结构

```
2212/
├── backend/          # FastAPI 后端服务
├── frontend/         # Streamlit 原型 + React 前端
├── models/           # ML 训练脚本
├── ops/              # Docker Compose + 监控配置
├── scripts/          # 运维与校验脚本
└── docs/             # ADR 与补充文档
```
