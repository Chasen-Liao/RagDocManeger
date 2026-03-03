# RagDocMan

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-00a393.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Development-orange.svg)](https://github.com/RagDocMan)

**语言:** 中文 | [English](README_EN.md)

---

RagDocMan 是一个基于高级 RAG（检索增强生成）技术的智能知识库管理系统。它允许用户通过自然语言对话来管理文档库，实现"所说即所得"的操作体验。

![RAG 增强架构](images/RAG增强如何实现.png)

## 特性

- **自然语言交互** - 通过对话即可完成知识库创建、文档上传、智能检索等操作
- **高级 RAG 技术栈** - 混合检索、重排序、查询改写等多阶段检索增强
- **多模型支持** - 支持 OpenAI、Anthropic、DeepSeek、硅基流动等多个 LLM 服务商
- **隐私保护** - 支持本地模型部署，数据完全可控
- **流式响应** - 支持 SSE 流式输出，提升用户体验

## 技术栈

### 核心框架

| 类别 | 技术 |
|------|------|
| Web 框架 | FastAPI |
| ORM | SQLAlchemy |
| 数据库 | SQLite / PostgreSQL |
| 向量数据库 | ChromaDB |
| 向量检索 | FAISS |
| 关键词检索 | rank-bm25 |
| 重排序 | sentence-transformers (CrossEncoder) |
| 文档解析 | python-docx, pypdf, markdown, unstructured |
| LLM 框架 | LangChain |

### 测试与工具

- **测试框架**: pytest, pytest-asyncio, pytest-cov
- **日志**: Python logging with rotation
- **中间件**: CORS, Error Handling, Request Logging

---

## 系统架构

```mermaid
graph TB
    subgraph Client["客户端"]
        UI[Web UI / Mobile]
    end

    subgraph API["API 层"]
        KB[知识库 API]
        Doc[文档 API]
        Search[搜索 API]
        RAG[RAG API]
        Config[配置 API]
    end

    subgraph Core["核心服务层"]
        KB_Svc[知识库服务]
        Doc_Svc[文档服务]
        Search_Svc[搜索服务]
    end

    subgraph RAG["RAG 引擎"]
        DP[文档处理器]
        CS[分块策略]
        HY[混合检索]
        RR[重排序]
        QR[查询改写]
        IR[意图识别]
    end

    subgraph Store["存储层"]
        SQL[(SQLite/PostgreSQL)]
        VS[ChromaDB]
        BM25[BM25 Index]
        Cache[(缓存)]
    end

    subgraph Models["模型层"]
        LLM[LLM Provider]
        EMB[Embedding Provider]
        RER[Reranker Provider]
    end

    UI --> KB
    UI --> Doc
    UI --> Search
    UI --> RAG

    KB --> KB_Svc
    Doc --> Doc_Svc
    Search --> Search_Svc
    RAG --> Search_Svc

    KB_Svc --> SQL
    Doc_Svc --> DP
    Search_Svc --> HY

    DP --> CS
    CS --> VS
    CS --> BM25
    HY --> RR
    HY --> QR
    QR --> IR
    Search_Svc --> Cache

    VS --> EMB
    RR --> RER
    LLM <-.-> RAG
```

---

## RAG 工作流程

```mermaid
flowchart TD
    A[用户查询] --> B{意图识别}
    B -->|管理操作| C[执行管理操作]
    B -->|查询操作| D[查询改写]

    D --> E[HyDE 扩展]
    E --> F[查询扩展]

    F --> G[混合检索]
    G --> H[BM25 关键词检索]
    G --> I[向量相似度检索]

    H --> J[RRF 融合]
    I --> J

    J --> K[Cross-Encoder 重排序]
    K --> L{Top-K 筛选}
    L -->|结果不足| M[子问题分解]
    M --> G
    L -->|结果足够| N[构建上下文]

    N --> O{是否配置 LLM}
    O -->|是| P[LLM 生成答案]
    O -->|否| Q[返回上下文结果]

    P --> R[流式返回答案 + 来源]
    Q --> R
    C --> S[返回操作结果]
```

---

## 项目结构

```
RagDocMan/
├── api/                          # FastAPI 路由
│   ├── knowledge_base_routes.py  # 知识库 CRUD
│   ├── document_routes.py        # 文档管理
│   ├── search_routes.py          # 搜索接口
│   ├── rag_routes.py             # RAG 生成
│   └── config_routes.py          # 配置管理
├── core/                         # 核心模块
│   ├── llm_provider.py           # LLM 集成
│   ├── embedding_provider.py     # 嵌入模型
│   ├── reranker_provider.py      # 重排序模型
│   ├── vector_store.py           # ChromaDB 集成
│   ├── batch_processor.py        # 批处理
│   ├── cache.py                  # 缓存机制
│   └── faiss_optimizer.py        # FAISS 优化
├── models/                       # 数据模型
│   ├── orm.py                    # SQLAlchemy 模型
│   └── schemas.py                # Pydantic 模型
├── rag/                          # RAG 核心
│   ├── document_processor.py     # 文档解析
│   ├── chunking_strategy.py      # 文本分块
│   ├── retriever.py              # 混合检索
│   ├── reranker.py               # 结果重排序
│   ├── query_rewriter.py         # 查询改写
│   └── intent_recognizer.py      # 意图识别
├── services/                     # 业务逻辑
│   ├── knowledge_base_service.py
│   ├── document_service.py
│   └── search_service.py
├── tests/                        # 测试
├── main.py                       # 应用入口
├── config.py                     # 配置管理
├── database.py                   # 数据库配置
├── logger.py                     # 日志配置
├── middleware.py                 # 中间件
└── requirements.txt              # 依赖
```

---

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+ (前端开发)
- 8GB+ RAM（本地模型需要更多）

### 安装

```bash
# 1. 克隆仓库
git clone https://github.com/yourusername/RagDocMan.git
cd RagDocMan

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 复制环境配置
cp .env.example .env

# 5. 编辑 .env 填入 API Key（详见配置章节）
```

### 运行

```bash
# 启动服务器
python main.py

# 或使用 uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

服务启动后访问：

- Swagger API 文档: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>

---

## API 端点

### Agent 对话（推荐）

- `POST /api/v1/agent/chat` - Agent 对话（非流式）
- `POST /api/v1/agent/chat/stream` - Agent 流式对话（SSE）
- `GET /api/v1/agent/sessions/{session_id}/history` - 获取会话历史
- `DELETE /api/v1/agent/sessions/{session_id}` - 清除会话历史

### 知识库管理

- `POST /api/knowledge-bases` - 创建知识库
- `GET /api/knowledge-bases` - 列出所有知识库
- `GET /api/knowledge-bases/{kb_id}` - 获取知识库详情
- `PUT /api/knowledge-bases/{kb_id}` - 更新知识库
- `DELETE /api/knowledge-bases/{kb_id}` - 删除知识库

### 文档管理

- `POST /api/knowledge-bases/{kb_id}/documents` - 上传文档
- `GET /api/knowledge-bases/{kb_id}/documents` - 列出文档
- `DELETE /api/knowledge-bases/{kb_id}/documents/{doc_id}` - 删除文档

### 搜索

- `POST /api/search` - 基础混合搜索
- `POST /api/search/with-rewrite` - 带查询改写的搜索

### 配置

- `GET /api/config` - 获取当前配置
- `PUT /api/config` - 更新配置

---

## API 响应格式

所有 API 接口使用统一的响应格式：

### 成功响应

```json
{
  "success": true,
  "data": { ... },
  "message": null
}
```

### 错误响应

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "INVALID_REQUEST",
    "message": "详细错误描述"
  }
}
```

### 分页响应

```json
{
  "success": true,
  "data": [...],
  "meta": {
    "total": 100,
    "page": 1,
    "limit": 20,
    "pages": 5
  }
}
```

---

## 配置

配置通过 `.env` 文件管理：

```bash
# 应用程序
APP_NAME=RagDocMan
APP_VERSION=1.0.0
DEBUG=false
LOG_LEVEL=INFO

# 数据库
DATABASE_URL=sqlite:///./ragdocman.db

# 向量存储
CHROMA_DB_PATH=./chroma_data

# LLM 配置
LLM_PROVIDER=siliconflow
LLM_API_KEY=your_api_key
LLM_MODEL=Qwen/Qwen2-7B-Instruct

# 嵌入配置
EMBEDDING_PROVIDER=siliconflow
EMBEDDING_API_KEY=your_api_key
EMBEDDING_MODEL=BAAI/bge-m3

# 重排序配置
RERANKER_PROVIDER=siliconflow
RERANKER_API_KEY=your_api_key
RERANKER_MODEL=BAAI/bge-reranker-base

# 处理参数
CHUNK_SIZE=1024
CHUNK_OVERLAP=128
RETRIEVAL_TOP_K=10
RERANKING_TOP_K=5
MAX_FILE_SIZE_MB=100
```

### 模型推荐

#### LLM 模型

| 服务商 | 模型 | 特点 |
| :--- | :--- | :--- |
| **硅基流动** | Qwen2.5、Llama3、Gemma2 | 主推，国内访问快 |
| Anthropic | Claude-3-Opus/Sonnet/Haiku | 长上下文 |
| DeepSeek | deepseek-chat/coder | 国产性价比高 |
| OpenAI | GPT-4, GPT-4-Turbo | API 稳定 |

#### 嵌入模型

| 服务商 | 推荐模型 | 维度 |
| :--- | :--- | :--- |
| **硅基流动** | BAAI/bge-m3 | 1024 |
| **硅基流动** | BAAI/bge-large-zh-v1.5 | 1024 |
| Jina AI | jina-embeddings-v2-base-zh | 768 |

强烈建议硅基流动！➡️ [硅基流动](https://cloud.siliconflow.cn/i/dbb2IJTv)

`注册立马送16元！！！所有高端模型可用！！！`
---

## 一句话操作示例

### 知识库管理

```plaintext
"创建一个叫'产品文档'的知识库" → 自动创建独立向量空间 ✅
"把技术文档库合并到产品库" → 智能去重合并 ❌
"删除 3 个月没用的测试库" → 自动识别并清理 ❌ -- 还未实现
```

### 文档操作

```plaintext
"把这 10 份 PDF 加到法务库" → 批量上传 + 自动分类 -- 目前要手动上传
"更新合同模板到最新版本" → 版本检测 + 增量更新 
"删掉所有过期的内部文档" → 时间范围智能筛选删除
```

### 智能检索

```plaintext
"上周开会提到的那个客户方案在哪？" → 时间 + 语义联合定位
"对比一下新旧两版的技术差异" → 多文档对比分析
"找出所有涉及合规风险的段落" → 跨库主题检索
```

---

## 开发规范

### 代码风格

- **Python**: PEP 8 + Black 格式化 + mypy 类型检查
- **TypeScript**: 严格模式 + ESLint + Prettier

### 提交规范

遵循 Conventional Commits：

- `feat`: 新功能
- `fix`: Bug 修复
- `refactor`: 代码重构
- `docs`: 文档更新
- `test`: 测试相关
- `chore`: 构建/工具配置

### 测试覆盖率

- 最低要求：80%
- 测试类型：单元测试、集成测试、E2E 测试

---

## 许可证

MIT License

---

## 贡献

欢迎提交 Issue 和 Pull Request！

---

## 状态

🚧 开发中
v0.2.1 -- 2026/03/03

### 更新日志

#### v0.2.1 (2026-03-03)
- ✅ 新增 Agent 对话功能，支持自然语言交互
- ✅ 实现对话历史存储（内存+数据库双层架构）
- ✅ 支持会话管理和历史记录恢复
- ✅ 统一使用 Agent API 替代原 RAG API
- ✅ 优化流式响应体验
- 🔧 修复模块导入问题

### 作者
Chasen