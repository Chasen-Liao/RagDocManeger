# RagDocMan 启动指南

## 快速开始

在 `RagDocMan` 目录下，使用以下命令启动应用：

```bash
# 推荐方式 1：使用 simple_main.py
python simple_main.py

# 推荐方式 2：使用 uvicorn
uvicorn main:app --reload

# 推荐方式 3：使用 run.py
python run.py
```

应用将在 `http://localhost:8000` 启动。

## 访问 API

启动后，你可以访问：

- **API 文档（Swagger UI）**: http://localhost:8000/docs
- **API 文档（ReDoc）**: http://localhost:8000/redoc
- **健康检查**: http://localhost:8000/health
- **根端点**: http://localhost:8000/

## 问题排查

### 问题 1：ModuleNotFoundError: No module named 'RagDocMan'

**原因**：Python 导入路径问题

**解决方案**：
- 确保在 `RagDocMan` 目录下运行命令
- 使用 `python simple_main.py` 或 `uvicorn main:app --reload`

### 问题 2：TypeError: DocumentService.__init__() missing required positional arguments

**原因**：服务依赖注入问题

**解决方案**：
- 已修复，使用最新的 API 路由文件
- 确保所有文件都已更新

### 问题 3：数据库连接错误

**原因**：`.env` 文件配置不正确或数据库不存在

**解决方案**：
```bash
# 检查 .env 文件是否存在
ls -la .env

# 如果不存在，创建一个
cp .env.example .env

# 编辑 .env 文件，确保数据库路径正确
```

## 环境配置

确保 `.env` 文件在 `RagDocMan` 目录下，包含必要的配置：

```
# 应用程序
APP_NAME=RagDocMan
APP_VERSION=1.0.0
DEBUG=true
LOG_LEVEL=INFO
HOST=127.0.0.1
PORT=8000

# 数据库
DATABASE_URL=sqlite:///./ragdocman.db

# 向量存储
CHROMA_DB_PATH=./chroma_db

# LLM 配置（可选）
LLM_PROVIDER=siliconflow
LLM_API_KEY=your_api_key

# 嵌入配置（可选）
EMBEDDING_PROVIDER=siliconflow
EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5

# 重排序配置（可选）
RERANKER_PROVIDER=siliconflow
RERANKER_MODEL=BAAI/bge-reranker-base

# 处理参数
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
RETRIEVAL_TOP_K=10
RERANKING_TOP_K=5
MAX_FILE_SIZE_MB=50
```

## 项目结构

```
RagDocMan/
├── __init__.py
├── main.py                    # FastAPI 应用主文件
├── simple_main.py             # 简化启动脚本
├── run.py                     # 启动脚本
├── config.py                  # 配置管理
├── database.py                # 数据库设置
├── logger.py                  # 日志配置
├── middleware.py              # 中间件
├── exceptions.py              # 异常定义
├── .env                       # 环境变量
├── .env.example               # 环境变量示例
├── requirements.txt           # 依赖列表
├── api/                       # API 路由
│   ├── __init__.py
│   ├── knowledge_base_routes.py
│   ├── document_routes.py
│   ├── search_routes.py
│   └── config_routes.py
├── services/                  # 业务逻辑服务
│   ├── __init__.py
│   ├── knowledge_base_service.py
│   ├── document_service.py
│   └── search_service.py
├── models/                    # 数据模型
│   ├── __init__.py
│   ├── orm.py
│   └── schemas.py
├── core/                      # 核心模块
│   ├── __init__.py
│   ├── vector_store.py
│   ├── llm_provider.py
│   ├── embedding_provider.py
│   ├── reranker_provider.py
│   ├── cache.py
│   ├── batch_processor.py
│   └── faiss_optimizer.py
├── rag/                       # RAG 组件
│   ├── __init__.py
│   ├── document_processor.py
│   ├── chunking_strategy.py
│   ├── retriever.py
│   ├── reranker.py
│   ├── query_rewriter.py
│   └── intent_recognizer.py
└── tests/                     # 测试文件
    ├── __init__.py
    └── test_*.py
```

## 安装依赖

```bash
# 安装所有依赖
pip install -r requirements.txt

# 或者手动安装主要依赖
pip install fastapi uvicorn sqlalchemy chromadb pydantic python-dotenv
```

## 常见命令

```bash
# 启动应用
python simple_main.py

# 运行测试
pytest tests/ -v

# 生成覆盖率报告
pytest tests/ --cov=. --cov-report=html

# 检查代码质量
flake8 .

# 格式化代码
black .
```

## 下一步

1. 启动应用：`python simple_main.py`
2. 访问 API 文档：http://localhost:8000/docs
3. 创建知识库：POST /api/knowledge-bases
4. 上传文档：POST /api/knowledge-bases/{kb_id}/documents
5. 执行搜索：POST /api/search

## 获取帮助

如果遇到问题，请检查：
1. 日志文件：`logs/ragdocman.log`
2. 数据库文件：`ragdocman.db`
3. 向量存储目录：`chroma_db/`
4. 环境变量：`.env` 文件
