"""Search API routes."""
from fastapi import APIRouter, HTTPException, status, Query, Depends
from typing import Optional
from sqlalchemy.orm import Session
from models.schemas import SearchRequest, SearchResponse
from services.search_service import SearchService
from services.knowledge_base_service import KnowledgeBaseService
from exceptions import NotFoundError, ValidationError
from logger import logger
from database import get_db
from core.vector_store import get_vector_store
from core.embedding_provider import EmbeddingProviderFactory
from config import settings

router = APIRouter(prefix="", tags=["search"])


@router.post("/search", response_model=dict)
async def search(request: SearchRequest, db: Session = Depends(get_db)):
    """Perform basic hybrid search.
    
    Performs a hybrid search combining:
    1. BM25 keyword-based retrieval
    2. Vector similarity search
    3. Result fusion using Reciprocal Rank Fusion (RRF)
    4. Cross-Encoder reranking for precision
    
    **Request Example**:
    ```json
    {
      "kb_id": "kb_123456",
      "query": "产品的主要功能是什么？",
      "top_k": 5
    }
    ```
    
    **Response Example**:
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
        },
        {
          "id": "chunk_002",
          "content": "功能特性：...",
          "doc_id": "doc_789012",
          "doc_name": "产品手册.pdf",
          "score": 0.87
        }
      ],
      "message": null
    }
    ```
    
    **Performance**:
    - 典型响应时间: < 2 秒
    - 支持的最大 top_k: 100
    
    **Error Cases**:
    - 404 Not Found: 知识库不存在
    - 400 Bad Request: 查询为空或参数无效
    
    Args:
        request: Search request containing kb_id, query, and optional top_k
        db: Database session
        
    Returns:
        Search results with relevance scores
    """
    try:
        logger.info(f"Performing search in knowledge base: {request.kb_id}, query: {request.query}")
        
        # Verify knowledge base exists
        kb_service = KnowledgeBaseService()
        await kb_service.get_knowledge_base(db, kb_id=request.kb_id)
        
        # Create embedding provider if configured
        embedding_provider = None
        if settings.embedding_api_key:
            try:
                embedding_provider = EmbeddingProviderFactory.create_provider(
                    provider_type=settings.embedding_provider or "siliconflow",
                    api_key=settings.embedding_api_key,
                    model=settings.embedding_model or "BAAI/bge-small-zh-v1.5"
                )
            except Exception as e:
                logger.warning(f"Failed to create embedding provider: {e}")

        # Perform search
        search_service = SearchService(db, embedding_provider)
        search_response = await search_service.search(
            kb_id=request.kb_id,
            query=request.query,
            top_k=request.top_k or 5
        )
        
        # Convert results to list of dicts
        results_list = [
            {
                "id": result.chunk_id,
                "content": result.content,
                "doc_id": result.doc_id,
                "doc_name": result.doc_name,
                "score": result.score
            }
            for result in search_response.results
        ]
        
        return {
            "success": True,
            "data": results_list,
            "message": None
        }
    except NotFoundError as e:
        logger.warning(f"Knowledge base not found: {request.kb_id}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except ValidationError as e:
        logger.warning(f"Validation error in search: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error performing search: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform search"
        )


@router.post("/search/with-rewrite", response_model=dict)
async def search_with_rewrite(request: SearchRequest, db: Session = Depends(get_db)):
    """Perform search with query rewriting.
    
    Performs an advanced search with automatic query optimization:
    1. Query rewriting using HyDE (Hypothetical Document Embeddings)
    2. Query expansion to cover related concepts
    3. Hybrid retrieval with rewritten queries
    4. Cross-Encoder reranking
    
    This approach is particularly effective for:
    - Complex or ambiguous queries
    - Queries with implicit context
    - Multi-concept searches
    
    **Request Example**:
    ```json
    {
      "kb_id": "kb_123456",
      "query": "上周开会提到的那个客户方案在哪？",
      "top_k": 5
    }
    ```
    
    **Response Example**:
    ```json
    {
      "success": true,
      "data": {
        "results": [
          {
            "id": "chunk_001",
            "content": "客户方案详情...",
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
    
    **Performance**:
    - 典型响应时间: < 3 秒（包括 LLM 调用）
    - 需要配置 LLM API Key
    
    **Error Cases**:
    - 404 Not Found: 知识库不存在
    - 400 Bad Request: 查询为空或参数无效
    - 503 Service Unavailable: LLM 服务不可用
    
    Args:
        request: Search request containing kb_id, query, and optional top_k
        db: Database session
        
    Returns:
        Search results with rewritten query and relevance scores
    """
    try:
        logger.info(f"Performing search with rewrite in knowledge base: {request.kb_id}, query: {request.query}")
        
        # Verify knowledge base exists
        kb_service = KnowledgeBaseService()
        await kb_service.get_knowledge_base(db, kb_id=request.kb_id)
        
        # Perform search with rewrite
        search_service = SearchService(db, embedding_provider)
        search_response = await search_service.search_with_rewrite(
            kb_id=request.kb_id,
            query=request.query,
            top_k=request.top_k or 5
        )
        
        # Convert results to list of dicts
        results_list = [
            {
                "id": result.chunk_id,
                "content": result.content,
                "doc_id": result.doc_id,
                "doc_name": result.doc_name,
                "score": result.score
            }
            for result in search_response.results
        ]
        
        return {
            "success": True,
            "data": {
                "results": results_list,
                "rewritten_query": search_response.rewritten_query
            },
            "message": None
        }
    except NotFoundError as e:
        logger.warning(f"Knowledge base not found: {request.kb_id}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except ValidationError as e:
        logger.warning(f"Validation error in search: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error performing search with rewrite: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform search with rewrite"
        )
