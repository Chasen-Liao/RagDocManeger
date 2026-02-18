# RagDocMan API 文档

## 概述

RagDocMan 是一个基于高级 RAG（检索增强生成）技术的智能知识库管理系统。本文档提供了完整的 API 使用指南和示例。

### 文档访问方式

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI Schema**: `http://localhost:8000/openapi.json`

### 响应格式

所有 API 接口使用统一的响应格式。

#### 成功响应

```json
{
  "success": true,
  "data": { ... },
  "message": null
}
```

#### 错误响应

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述"
  }
}
```

#### 分页响应

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

## API 端点

### 1. 知识库管理 API

#### 1.1 创建知识库

**端点**: `POST /knowledge-bases`

**描述**: 创建一个新的知识库。每个知识库拥有独立的向量索引和文档集合。

**请求体**:

```json
{
  "name": "产品文档库",
  "description": "存储所有产品相关的文档"
}
```

**响应示例** (201 Created):

```json
{
  "success": true,
  "data": {
    "id": "kb_123456",
    "name": "产品文档库",
    "description": "存储所有产品相关的文档",
    "document_count": 0,
    "total_size": 0,
    "created_at": "2024-01-15T10:30:00",
    "updated_at": "2024-01-15T10:30:00"
  },
  "message": "Knowledge base created successfully"
}
```

**错误情况**:

- `409 Conflict`: 知识库名称已存在
- `400 Bad Request`: 缺失必要字段或字段格式不正确

**cURL 示例**:

```bash
curl -X POST "http://localhost:8000/knowledge-bases" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "产品文档库",
    "description": "存储所有产品相关的文档"
  }'
```

**Python 示例**:

```python
import requests

url = "http://localhost:8000/knowledge-bases"
payload = {
    "name": "产品文档库",
    "description": "存储所有产品相关的文档"
}

response = requests.post(url, json=payload)
print(response.json())
```

---

#### 1.2 获取知识库列表

**端点**: `GET /knowledge-bases`

**描述**: 获取所有知识库的分页列表。

**查询参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| skip | integer | 0 | 跳过的记录数 |
| limit | integer | 20 | 返回的最大记录数（最大 100） |

**响应示例** (200 OK):

```json
{
  "success": true,
  "data": [
    {
      "id": "kb_123456",
      "name": "产品文档库",
      "description": "存储所有产品相关的文档",
      "document_count": 5,
      "total_size": 1024000,
      "created_at": "2024-01-15T10:30:00",
      "updated_at": "2024-01-15T10:30:00"
    },
    {
      "id": "kb_789012",
      "name": "技术文档库",
      "description": "技术相关文档",
      "document_count": 3,
      "total_size": 512000,
      "created_at": "2024-01-14T15:20:00",
      "updated_at": "2024-01-14T15:20:00"
    }
  ],
  "meta": {
    "total": 2,
    "skip": 0,
    "limit": 20,
    "page": 1,
    "pages": 1
  },
  "message": null
}
```

**cURL 示例**:

```bash
curl -X GET "http://localhost:8000/knowledge-bases?skip=0&limit=20"
```

**Python 示例**:

```python
import requests

url = "http://localhost:8000/knowledge-bases"
params = {"skip": 0, "limit": 20}

response = requests.get(url, params=params)
print(response.json())
```

---

#### 1.3 获取知识库详情

**端点**: `GET /knowledge-bases/{kb_id}`

**描述**: 获取指定知识库的详细信息。

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| kb_id | string | 知识库 ID |

**响应示例** (200 OK):

```json
{
  "success": true,
  "data": {
    "id": "kb_123456",
    "name": "产品文档库",
    "description": "存储所有产品相关的文档",
    "document_count": 5,
    "total_size": 1024000,
    "created_at": "2024-01-15T10:30:00",
    "updated_at": "2024-01-15T10:30:00"
  },
  "message": null
}
```

**错误情况**:

- `404 Not Found`: 知识库不存在

**cURL 示例**:

```bash
curl -X GET "http://localhost:8000/knowledge-bases/kb_123456"
```

---

#### 1.4 更新知识库

**端点**: `PUT /knowledge-bases/{kb_id}`

**描述**: 更新知识库的名称和描述。

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| kb_id | string | 知识库 ID |

**请求体**:

```json
{
  "name": "产品文档库 v2",
  "description": "更新的描述"
}
```

**响应示例** (200 OK):

```json
{
  "success": true,
  "data": {
    "id": "kb_123456",
    "name": "产品文档库 v2",
    "description": "更新的描述",
    "document_count": 5,
    "total_size": 1024000,
    "created_at": "2024-01-15T10:30:00",
    "updated_at": "2024-01-15T11:00:00"
  },
  "message": "Knowledge base updated successfully"
}
```

**错误情况**:

- `404 Not Found`: 知识库不存在
- `409 Conflict`: 新名称已被其他知识库使用

**cURL 示例**:

```bash
curl -X PUT "http://localhost:8000/knowledge-bases/kb_123456" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "产品文档库 v2",
    "description": "更新的描述"
  }'
```

---

#### 1.5 删除知识库

**端点**: `DELETE /knowledge-bases/{kb_id}`

**描述**: 删除知识库及其所有关联的文档和向量嵌入。此操作不可逆。

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| kb_id | string | 知识库 ID |

**响应示例** (200 OK):

```json
{
  "success": true,
  "data": null,
  "message": "Knowledge base deleted successfully"
}
```

**错误情况**:

- `404 Not Found`: 知识库不存在

**cURL 示例**:

```bash
curl -X DELETE "http://localhost:8000/knowledge-bases/kb_123456"
```

---

### 2. 文档管理 API

#### 2.1 上传文档

**端点**: `POST /knowledge-bases/{kb_id}/documents/upload`

**描述**: 上传文档到知识库。系统自动进行文档解析、分块和向量化。

**支持的文件格式**:

- PDF (.pdf)
- Word (.docx, .doc)
- Markdown (.md)

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| kb_id | string | 知识库 ID |

**请求体**: multipart/form-data

| 字段 | 类型 | 说明 |
|------|------|------|
| file | file | 要上传的文档文件 |

**响应示例** (201 Created):

```json
{
  "success": true,
  "data": {
    "id": "doc_789012",
    "kb_id": "kb_123456",
    "name": "产品手册.pdf",
    "file_size": 2048000,
    "file_type": "pdf",
    "chunk_count": 45,
    "created_at": "2024-01-15T10:30:00"
  },
  "message": "Document uploaded successfully"
}
```

**错误情况**:

- `404 Not Found`: 知识库不存在
- `400 Bad Request`: 不支持的文件格式或文件过大
- `500 Internal Server Error`: 文档处理失败

**cURL 示例**:

```bash
curl -X POST "http://localhost:8000/knowledge-bases/kb_123456/documents/upload" \
  -F "file=@产品手册.pdf"
```

**Python 示例**:

```python
import requests

url = "http://localhost:8000/knowledge-bases/kb_123456/documents/upload"

with open("产品手册.pdf", "rb") as f:
    files = {"file": f}
    response = requests.post(url, files=files)
    print(response.json())
```

---

#### 2.2 获取文档列表

**端点**: `GET /knowledge-bases/{kb_id}/documents`

**描述**: 获取知识库中的所有文档列表。

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| kb_id | string | 知识库 ID |

**查询参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| skip | integer | 0 | 跳过的记录数 |
| limit | integer | 20 | 返回的最大记录数（最大 100） |

**响应示例** (200 OK):

```json
{
  "success": true,
  "data": [
    {
      "id": "doc_789012",
      "kb_id": "kb_123456",
      "name": "产品手册.pdf",
      "file_size": 2048000,
      "file_type": "pdf",
      "chunk_count": 45,
      "created_at": "2024-01-15T10:30:00"
    }
  ],
  "meta": {
    "total": 1,
    "skip": 0,
    "limit": 20,
    "page": 1,
    "pages": 1
  },
  "message": null
}
```

**cURL 示例**:

```bash
curl -X GET "http://localhost:8000/knowledge-bases/kb_123456/documents?skip=0&limit=20"
```

---

#### 2.3 删除文档

**端点**: `DELETE /knowledge-bases/{kb_id}/documents/{doc_id}`

**描述**: 删除知识库中的文档及其所有关联的块。此操作不可逆。

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| kb_id | string | 知识库 ID |
| doc_id | string | 文档 ID |

**响应示例** (200 OK):

```json
{
  "success": true,
  "data": null,
  "message": "Document deleted successfully"
}
```

**错误情况**:

- `404 Not Found`: 知识库或文档不存在

**cURL 示例**:

```bash
curl -X DELETE "http://localhost:8000/knowledge-bases/kb_123456/documents/doc_789012"
```

---

### 3. RAG 对话 API

#### 3.1 生成答案（流式）- 推荐方案

**端点**: `POST /rag/answer/stream`

**描述**: 基于知识库生成答案，使用 Server-Sent Events (SSE) 流式返回结果。**推荐用于前端实时显示 LLM 生成过程**。

**请求体**:

```json
{
  "kb_id": "kb_123456",
  "query": "产品的主要功能是什么？",
  "top_k": 5,
  "include_sources": true
}
```

**响应格式**: Server-Sent Events (SSE)

流式响应包含多个事件，每个事件的格式为：

```
data: {"type": "sources", "data": [...]}

data: {"type": "content", "data": "答案内容片段"}

data: {"type": "done"}
```

**响应示例**:

```
data: {"type": "sources", "data": [{"doc_id": "doc_789012", "doc_name": "产品手册.pdf", "chunk_id": "chunk_001", "content": "产品的主要功能包括...", "score": 0.95}]}

data: {"type": "content", "data": "根据"}

data: {"type": "content", "data": "产品文档"}

data: {"type": "content", "data": "，产品的"}

data: {"type": "content", "data": "主要功能"}

data: {"type": "content", "data": "包括："}

data: {"type": "content", "data": "\n1. 数据管理"}

data: {"type": "content", "data": "\n2. 智能分析"}

data: {"type": "content", "data": "\n3. 自动化处理"}

data: {"type": "done"}
```

**事件类型**:

| 类型 | 说明 |
|------|------|
| sources | 返回检索到的源文档（通常首先返回） |
| content | 返回 LLM 生成的答案片段（逐字返回） |
| error | 返回错误信息 |
| done | 表示流式传输完成 |

**请求参数**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| kb_id | string | 是 | 知识库 ID |
| query | string | 是 | 用户问题 |
| top_k | integer | 否 | 检索的最大块数（默认 5） |
| include_sources | boolean | 否 | 是否返回源文档引用（默认 true） |

**性能指标**:

- 首字节时间: < 1 秒
- 流式传输速度: 实时（逐字返回）
- 需要配置 LLM API Key

**错误情况**:

- `404 Not Found`: 知识库不存在
- `400 Bad Request`: 查询为空或参数无效
- `503 Service Unavailable`: LLM 服务不可用

**cURL 示例**:

```bash
curl -X POST "http://localhost:8000/rag/answer/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "kb_id": "kb_123456",
    "query": "产品的主要功能是什么？",
    "top_k": 5,
    "include_sources": true
  }'
```

**JavaScript 示例** (前端实时显示 - 推荐):

```javascript
async function streamAnswer(kbId, query) {
  const response = await fetch('http://localhost:8000/rag/answer/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      kb_id: kbId,
      query: query,
      top_k: 5,
      include_sources: true
    })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let sources = [];
  let answer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const text = decoder.decode(value);
    const lines = text.split('\n');

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const event = JSON.parse(line.slice(6));
          
          if (event.type === 'sources') {
            sources = event.data;
            // 显示来源文档
            const sourcesList = sources.map(s => `${s.doc_name} (相关度: ${(s.score * 100).toFixed(0)}%)`).join(', ');
            document.getElementById('sources').textContent = `来源: ${sourcesList}`;
          } 
          else if (event.type === 'content') {
            answer += event.data;
            // 实时更新答案显示
            document.getElementById('answer').textContent = answer;
            // 自动滚动到底部
            document.getElementById('answer').scrollTop = document.getElementById('answer').scrollHeight;
          } 
          else if (event.type === 'done') {
            document.getElementById('status').textContent = '✓ 完成';
          } 
          else if (event.type === 'error') {
            document.getElementById('status').textContent = `✗ 错误: ${event.data}`;
          }
        } catch (e) {
          console.error('Parse error:', e);
        }
      }
    }
  }

  return { answer, sources };
}

// 使用示例
document.getElementById('sendBtn').addEventListener('click', async () => {
  const query = document.getElementById('queryInput').value;
  const kbId = document.getElementById('kbSelect').value;
  
  document.getElementById('status').textContent = '⏳ 生成中...';
  document.getElementById('answer').textContent = '';
  
  await streamAnswer(kbId, query);
});
```

**Python 示例** (流式处理 - 推荐):

```python
import requests
import json

def stream_answer(kb_id, query, top_k=5):
    """流式获取答案"""
    url = "http://localhost:8000/rag/answer/stream"
    payload = {
        "kb_id": kb_id,
        "query": query,
        "top_k": top_k,
        "include_sources": True
    }

    response = requests.post(url, json=payload, stream=True)
    
    sources = []
    answer = ""

    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith('data: '):
                try:
                    event = json.loads(line[6:])
                    
                    if event['type'] == 'sources':
                        sources = event['data']
                        print("📚 来源文档:")
                        for source in sources:
                            print(f"   - {source['doc_name']} (相关度: {source['score']:.0%})")
                        print()
                    
                    elif event['type'] == 'content':
                        chunk = event['data']
                        answer += chunk
                        print(chunk, end='', flush=True)
                    
                    elif event['type'] == 'done':
                        print("\n\n✓ 生成完成")
                    
                    elif event['type'] == 'error':
                        print(f"\n✗ 错误: {event['data']}")
                        
                except json.JSONDecodeError:
                    pass
    
    return answer, sources

# 使用示例
answer, sources = stream_answer('kb_123456', '产品的主要功能是什么？')
```

---

#### 3.2 生成答案（非流式）

**端点**: `POST /rag/answer`

**描述**: 基于知识库生成答案。一次性返回完整答案，适合后端服务调用。

**请求体**:

```json
{
  "kb_id": "kb_123456",
  "query": "产品的主要功能是什么？",
  "top_k": 5,
  "include_sources": true
}
```

**响应示例** (200 OK):

```json
{
  "success": true,
  "data": {
    "answer": "根据产品文档，产品的主要功能包括：\n1. 数据管理 - 支持多种数据格式的导入和管理\n2. 智能分析 - 提供实时数据分析和可视化\n3. 自动化处理 - 支持工作流自动化和任务调度\n4. 高可用性 - 支持分布式部署和故障转移",
    "sources": [
      {
        "doc_id": "doc_789012",
        "doc_name": "产品手册.pdf",
        "chunk_id": "chunk_001",
        "content": "产品的主要功能包括数据管理、智能分析和自动化处理...",
        "score": 0.95
      }
    ],
    "query": "产品的主要功能是什么？"
  },
  "message": null
}
```

**请求参数**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| kb_id | string | 是 | 知识库 ID |
| query | string | 是 | 用户问题 |
| top_k | integer | 否 | 检索的最大块数（默认 5） |
| include_sources | boolean | 否 | 是否返回源文档引用（默认 true） |

**性能指标**:

- 典型响应时间: 2-5 秒（包括 LLM 调用）
- 需要配置 LLM API Key

**错误情况**:

- `404 Not Found`: 知识库不存在
- `400 Bad Request`: 查询为空或参数无效
- `503 Service Unavailable`: LLM 服务不可用

**cURL 示例**:

```bash
curl -X POST "http://localhost:8000/rag/answer" \
  -H "Content-Type: application/json" \
  -d '{
    "kb_id": "kb_123456",
    "query": "产品的主要功能是什么？",
    "top_k": 5,
    "include_sources": true
  }'
```

**Python 示例**:

```python
import requests

url = "http://localhost:8000/rag/answer"
payload = {
    "kb_id": "kb_123456",
    "query": "产品的主要功能是什么？",
    "top_k": 5,
    "include_sources": True
}

response = requests.post(url, json=payload)
data = response.json()

if data["success"]:
    answer = data["data"]["answer"]
    sources = data["data"]["sources"]
    
    print("答案:")
    print(answer)
    print("\n来源:")
    for source in sources:
        print(f"- {source['doc_name']}: {source['content'][:100]}...")
```

---

### 4. 搜索 API

#### 4.1 基础混合搜索

**端点**: `POST /search`

**描述**: 执行混合搜索，结合 BM25 关键词检索和向量相似度检索。

**请求体**:

```json
{
  "kb_id": "kb_123456",
  "query": "产品的主要功能是什么？",
  "top_k": 5
}
```

**响应示例** (200 OK):

```json
{
  "success": true,
  "data": [
    {
      "id": "chunk_001",
      "content": "产品的主要功能包括数据管理、智能分析和自动化处理...",
      "doc_id": "doc_789012",
      "doc_name": "产品手册.pdf",
      "score": 0.95
    },
    {
      "id": "chunk_002",
      "content": "功能特性：支持多种数据格式、实时处理、高可用性...",
      "doc_id": "doc_789012",
      "doc_name": "产品手册.pdf",
      "score": 0.87
    }
  ],
  "message": null
}
```

**请求参数**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| kb_id | string | 是 | 知识库 ID |
| query | string | 是 | 搜索查询 |
| top_k | integer | 否 | 返回的最大结果数（默认 5，最大 100） |

**性能指标**:

- 典型响应时间: < 2 秒
- 支持的最大 top_k: 100

**错误情况**:

- `404 Not Found`: 知识库不存在
- `400 Bad Request`: 查询为空或参数无效

**cURL 示例**:

```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "kb_id": "kb_123456",
    "query": "产品的主要功能是什么？",
    "top_k": 5
  }'
```

**Python 示例**:

```python
import requests

url = "http://localhost:8000/search"
payload = {
    "kb_id": "kb_123456",
    "query": "产品的主要功能是什么？",
    "top_k": 5
}

response = requests.post(url, json=payload)
results = response.json()

for result in results["data"]:
    print(f"Score: {result['score']}")
    print(f"Content: {result['content']}")
    print(f"Document: {result['doc_name']}")
    print("---")
```

---

#### 4.2 带查询改写的搜索

**端点**: `POST /search/with-rewrite`

**描述**: 执行高级搜索，包含自动查询改写和优化。特别适合复杂或模糊的查询。

**请求体**:

```json
{
  "kb_id": "kb_123456",
  "query": "上周开会提到的那个客户方案在哪？",
  "top_k": 5
}
```

**响应示例** (200 OK):

```json
{
  "success": true,
  "data": {
    "results": [
      {
        "id": "chunk_001",
        "content": "客户方案详情：该方案包括...",
        "doc_id": "doc_789012",
        "doc_name": "会议记录.md",
        "score": 0.98
      }
    ],
    "rewritten_query": "客户方案 会议 上周"
  },
  "message": null
}
```

**请求参数**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| kb_id | string | 是 | 知识库 ID |
| query | string | 是 | 搜索查询 |
| top_k | integer | 否 | 返回的最大结果数（默认 5，最大 100） |

**性能指标**:

- 典型响应时间: < 3 秒（包括 LLM 调用）
- 需要配置 LLM API Key

**错误情况**:

- `404 Not Found`: 知识库不存在
- `400 Bad Request`: 查询为空或参数无效
- `503 Service Unavailable`: LLM 服务不可用

**cURL 示例**:

```bash
curl -X POST "http://localhost:8000/search/with-rewrite" \
  -H "Content-Type: application/json" \
  -d '{
    "kb_id": "kb_123456",
    "query": "上周开会提到的那个客户方案在哪？",
    "top_k": 5
  }'
```

---

### 5. 配置 API

#### 5.1 获取配置

**端点**: `GET /config`

**描述**: 获取当前系统配置。敏感字段（如 API Key）会被掩码处理。

**响应示例** (200 OK):

```json
{
  "success": true,
  "data": {
    "app_name": "RagDocMan",
    "app_version": "1.0.0",
    "debug": false,
    "log_level": "INFO",
    "database_url": "***",
    "chroma_db_path": "./chroma_data",
    "llm_provider": "siliconflow",
    "embedding_provider": "siliconflow",
    "embedding_model": "BAAI/bge-small-zh-v1.5",
    "reranker_provider": "siliconflow",
    "reranker_model": "BAAI/bge-reranker-large",
    "max_file_size_mb": 100,
    "supported_file_types": ["pdf", "docx", "md"],
    "chunk_size": 1000,
    "chunk_overlap": 200,
    "retrieval_top_k": 10,
    "reranking_top_k": 5
  },
  "message": null
}
```

**cURL 示例**:

```bash
curl -X GET "http://localhost:8000/config"
```

---

#### 5.2 更新配置

**端点**: `PUT /config`

**描述**: 更新系统配置参数。只有非敏感字段可以更新。

**可更新的字段**:

| 字段 | 类型 | 说明 |
|------|------|------|
| debug | boolean | 调试模式开关 |
| log_level | string | 日志级别 (DEBUG, INFO, WARNING, ERROR) |
| llm_provider | string | LLM 服务商 |
| embedding_provider | string | 嵌入模型服务商 |
| embedding_model | string | 嵌入模型名称 |
| reranker_provider | string | 重排序模型服务商 |
| reranker_model | string | 重排序模型名称 |
| chunk_size | integer | 文本块大小 |
| chunk_overlap | integer | 块重叠大小 |
| retrieval_top_k | integer | 检索返回的最大块数 |
| reranking_top_k | integer | 重排序返回的最大块数 |

**请求体**:

```json
{
  "debug": true,
  "log_level": "DEBUG",
  "chunk_size": 1500,
  "retrieval_top_k": 15
}
```

**响应示例** (200 OK):

```json
{
  "success": true,
  "data": {
    "app_name": "RagDocMan",
    "app_version": "1.0.0",
    "debug": true,
    "log_level": "DEBUG",
    "chunk_size": 1500,
    "retrieval_top_k": 15
  },
  "message": "Configuration updated successfully"
}
```

**错误情况**:

- `400 Bad Request`: 包含无效的配置字段或值
- `422 Unprocessable Entity`: 配置验证失败

**cURL 示例**:

```bash
curl -X PUT "http://localhost:8000/config" \
  -H "Content-Type: application/json" \
  -d '{
    "debug": true,
    "log_level": "DEBUG"
  }'
```

---

### 6. 健康检查 API

#### 6.1 健康检查

**端点**: `GET /health`

**描述**: 检查系统健康状态。

**响应示例** (200 OK):

```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "app_name": "RagDocMan",
    "version": "1.0.0"
  },
  "message": null
}
```

**cURL 示例**:

```bash
curl -X GET "http://localhost:8000/health"
```

---

## 完整工作流示例

### 场景：创建知识库、上传文档、执行对话

#### 步骤 1: 创建知识库

```bash
curl -X POST "http://localhost:8000/knowledge-bases" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "产品文档库",
    "description": "存储所有产品相关的文档"
  }'
```

响应:
```json
{
  "success": true,
  "data": {
    "id": "kb_123456",
    "name": "产品文档库",
    ...
  }
}
```

#### 步骤 2: 上传文档

```bash
curl -X POST "http://localhost:8000/knowledge-bases/kb_123456/documents/upload" \
  -F "file=@产品手册.pdf"
```

响应:
```json
{
  "success": true,
  "data": {
    "id": "doc_789012",
    "kb_id": "kb_123456",
    "name": "产品手册.pdf",
    "chunk_count": 45,
    ...
  }
}
```

#### 步骤 3: 执行对话（流式）

```bash
curl -X POST "http://localhost:8000/rag/answer/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "kb_id": "kb_123456",
    "query": "产品的主要功能是什么？",
    "top_k": 5,
    "include_sources": true
  }'
```

流式响应:
```
data: {"type": "sources", "data": [{"doc_id": "doc_789012", "doc_name": "产品手册.pdf", ...}]}

data: {"type": "content", "data": "根据"}

data: {"type": "content", "data": "产品文档"}

data: {"type": "content", "data": "，产品的主要功能包括..."}

data: {"type": "done"}
```

#### 步骤 4: 执行搜索（可选）

```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "kb_id": "kb_123456",
    "query": "产品的主要功能是什么？",
    "top_k": 5
  }'
```

响应:
```json
{
  "success": true,
  "data": [
    {
      "id": "chunk_001",
      "content": "产品的主要功能包括...",
      "doc_id": "doc_789012",
      "doc_name": "产品手册.pdf",
      "score": 0.95
    }
  ]
}
```

---

## 完整工作流示例

### 场景：创建知识库、上传文档、执行搜索

#### 步骤 1: 创建知识库

```bash
curl -X POST "http://localhost:8000/knowledge-bases" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "产品文档库",
    "description": "存储所有产品相关的文档"
  }'
```

响应:
```json
{
  "success": true,
  "data": {
    "id": "kb_123456",
    "name": "产品文档库",
    ...
  }
}
```

#### 步骤 2: 上传文档

```bash
curl -X POST "http://localhost:8000/knowledge-bases/kb_123456/documents/upload" \
  -F "file=@产品手册.pdf"
```

响应:
```json
{
  "success": true,
  "data": {
    "id": "doc_789012",
    "kb_id": "kb_123456",
    "name": "产品手册.pdf",
    "chunk_count": 45,
    ...
  }
}
```

---

## 错误处理

### 常见错误代码

| 状态码 | 错误代码 | 说明 |
|--------|---------|------|
| 400 | INVALID_REQUEST | 请求参数无效 |
| 404 | NOT_FOUND | 资源不存在 |
| 409 | CONFLICT | 资源冲突（如名称重复） |
| 422 | VALIDATION_ERROR | 数据验证失败 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |
| 503 | SERVICE_UNAVAILABLE | 外部服务不可用 |

### 错误响应示例

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "NOT_FOUND",
    "message": "Knowledge base with id 'kb_invalid' not found"
  }
}
```

---

## 最佳实践

### 1. 错误处理

始终检查响应的 `success` 字段：

```python
response = requests.post(url, json=payload)
data = response.json()

if data["success"]:
    # 处理成功响应
    result = data["data"]
else:
    # 处理错误
    error = data["error"]
    print(f"Error: {error['code']} - {error['message']}")
```

### 2. 分页处理

处理大量数据时使用分页：

```python
skip = 0
limit = 20

while True:
    response = requests.get(
        "http://localhost:8000/knowledge-bases",
        params={"skip": skip, "limit": limit}
    )
    data = response.json()
    
    if not data["data"]:
        break
    
    # 处理当前页数据
    for item in data["data"]:
        print(item)
    
    skip += limit
```

### 3. 搜索优化

- 对于简单查询，使用基础搜索 (`/search`)
- 对于复杂或模糊查询，使用带改写的搜索 (`/search/with-rewrite`)
- 根据需要调整 `top_k` 参数以平衡性能和准确性

### 4. 文件上传

- 确保文件格式受支持（PDF、Word、Markdown）
- 检查文件大小不超过配置的限制
- 上传后等待处理完成再执行搜索

---

## 常见问题

### Q: 如何获取知识库 ID？

A: 创建知识库时会返回 ID，或通过 `GET /knowledge-bases` 获取所有知识库列表。

### Q: 搜索结果的分数是什么意思？

A: 分数表示搜索结果与查询的相关性，范围通常为 0-1，分数越高表示相关性越强。

### Q: 如何提高搜索准确性？

A: 
1. 使用带改写的搜索 API
2. 调整 `chunk_size` 和 `chunk_overlap` 参数
3. 确保上传的文档质量良好
4. 使用更具体的查询表述

### Q: 支持哪些文件格式？

A: 目前支持 PDF、Word (.docx, .doc) 和 Markdown (.md) 格式。

### Q: 如何配置 LLM 服务？

A: 在 `.env` 文件中设置 `LLM_API_KEY` 和 `LLM_PROVIDER`，然后重启应用。

---

## 更多资源

- **项目 GitHub**: [RagDocMan](https://github.com/example/ragdocman)
- **问题报告**: 提交 Issue 到项目仓库
- **讨论**: 在项目讨论区提问

