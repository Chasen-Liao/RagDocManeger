# RagDocMan 快速启动指南

## 🚀 5 分钟快速启动

### 1️⃣ 验证环境 (30 秒)
```bash
python health_check.py
```

**预期输出**: `✓ BACKEND IS HEALTHY`

### 2️⃣ 启动服务 (10 秒)
```bash
python run.py
```

**预期输出**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### 3️⃣ 验证服务 (30 秒)
```bash
# 在另一个终端运行
curl http://localhost:8000/health
```

**预期响应**:
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "app_name": "RagDocMan",
    "version": "0.1.2"
  },
  "message": null
}
```

### 4️⃣ 访问 API 文档 (即时)
打开浏览器访问: **http://localhost:8000/docs**

---

## 📊 测试状态

✓ **后端 100% 健康**
- 21/21 核心测试通过
- 所有依赖已安装
- 系统完全可用

---

## 🔗 API 端点

### 知识库管理
- `POST /api/v1/knowledge-bases` - 创建知识库
- `GET /api/v1/knowledge-bases` - 列出知识库
- `GET /api/v1/knowledge-bases/{kb_id}` - 获取详情
- `PUT /api/v1/knowledge-bases/{kb_id}` - 更新
- `DELETE /api/v1/knowledge-bases/{kb_id}` - 删除

### 文档管理
- `POST /api/v1/documents` - 上传文档
- `GET /api/v1/documents` - 列出文档
- `GET /api/v1/documents/{doc_id}` - 获取详情
- `PUT /api/v1/documents/{doc_id}` - 更新
- `DELETE /api/v1/documents/{doc_id}` - 删除

### 搜索和 RAG
- `POST /api/v1/search` - 执行搜索
- `POST /api/v1/rag/generate` - 生成答案
- `POST /api/v1/rag/generate/stream` - 流式生成

### Agent 交互
- `POST /api/v1/agent/chat` - Agent 对话
- `POST /api/v1/agent/chat/stream` - 流式对话
- `DELETE /api/v1/agent/session/{session_id}` - 清除会话

---

## 🧪 运行测试

### 快速测试 (< 1 分钟)
```bash
python -m pytest tests/test_backend_availability.py -v
```

### 完整测试 (< 5 分钟)
```bash
python -m pytest tests/ -v
```

### 特定测试
```bash
# 端到端测试
python -m pytest tests/test_e2e_scenarios.py -v

# 向后兼容性测试
python -m pytest tests/test_backward_compatibility.py -v

# 综合集成测试
python -m pytest tests/test_comprehensive_integration.py -v
```

---

## 📁 项目结构

```
RagDocMan/
├── main.py                          # FastAPI 应用入口
├── run.py                           # 启动脚本
├── config.py                        # 配置管理
├── database.py                      # 数据库连接
├── logger.py                        # 日志系统
├── health_check.py                  # 健康检查脚本
│
├── api/                             # API 路由
│   ├── knowledge_base_routes.py
│   ├── document_routes.py
│   ├── search_routes.py
│   ├── rag_routes.py
│   └── agent_routes.py
│
├── rag/                             # RAG 核心模块
│   ├── conversation_memory.py       # 对话记忆
│   ├── vector_search_optimizer.py   # 向量搜索优化
│   ├── parallel_tool_executor.py    # 并行执行
│   ├── agent_cache.py               # 缓存管理
│   └── agent_manager.py             # Agent 管理
│
├── services/                        # 业务服务
│   ├── knowledge_base_service.py
│   ├── document_service.py
│   └── search_service.py
│
├── models/                          # 数据模型
│   ├── orm.py                       # ORM 模型
│   └── schemas.py                   # Pydantic 模型
│
├── tests/                           # 测试套件
│   ├── test_backend_availability.py
│   ├── test_e2e_scenarios.py
│   ├── test_backward_compatibility.py
│   ├── test_comprehensive_integration.py
│   └── test_performance_optimization.py
│
└── docs/                            # 文档
    ├── BACKEND_AVAILABILITY_REPORT.md
    ├── STARTUP_AND_TEST_GUIDE.md
    └── TEST_RESULTS_SUMMARY.md
```

---

## ⚙️ 配置说明

### 环境变量 (.env)
```env
# 数据库
DATABASE_URL=sqlite:///./ragdocman.db

# LLM 配置
LLM_PROVIDER=siliconflow
LLM_API_KEY=your_api_key
LLM_MODEL=your_model

# 嵌入模型
EMBEDDING_PROVIDER=siliconflow
EMBEDDING_MODEL=your_embedding_model

# 应用配置
DEBUG=False
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000
```

---

## 🐛 故障排除

### 问题: 端口已被占用
```bash
# 使用不同的端口
python -m uvicorn main:app --port 8001
```

### 问题: 数据库错误
```bash
# 重新初始化数据库
python -c "from database import init_db; init_db()"
```

### 问题: 导入错误
```bash
# 确保在项目根目录运行
cd RagDocMan
python run.py
```

---

## 📞 支持

### 文档
- [后端可用性报告](BACKEND_AVAILABILITY_REPORT.md)
- [启动和测试指南](STARTUP_AND_TEST_GUIDE.md)
- [测试结果总结](TEST_RESULTS_SUMMARY.md)

### 日志
- 应用日志: `logs/ragdocman.log`
- 控制台输出: 实时显示

---

## ✅ 检查清单

启动前检查:
- [ ] Python 3.12+ 已安装
- [ ] 依赖已安装: `pip install -r requirements.txt`
- [ ] 健康检查通过: `python health_check.py`
- [ ] 端口 8000 未被占用

启动后检查:
- [ ] 服务运行中: http://localhost:8000/health
- [ ] API 文档可访问: http://localhost:8000/docs
- [ ] 日志正常输出: `logs/ragdocman.log`

---

## 🎉 完成

恭喜！RagDocMan 后端已成功启动。

**下一步**:
1. 访问 API 文档: http://localhost:8000/docs
2. 创建知识库
3. 上传文档
4. 执行搜索
5. 生成 RAG 答案

---

*最后更新: 2026-03-03*
