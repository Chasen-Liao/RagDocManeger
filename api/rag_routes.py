"""RAG API routes for generating answers from knowledge base."""
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import StreamingResponse
from typing import Optional, List
from sqlalchemy.orm import Session
from pydantic import BaseModel
import json
import asyncio
from services.search_service import SearchService
from services.knowledge_base_service import KnowledgeBaseService
from core.llm_provider import SiliconFlowProvider
from core.embedding_provider import EmbeddingProviderFactory
from config import settings
from exceptions import NotFoundError, ValidationError
from logger import logger
from database import get_db

router = APIRouter(prefix="/rag", tags=["rag"])


class RagRequest(BaseModel):
    """RAG request model."""
    kb_id: str
    query: str
    top_k: int = 5
    include_sources: bool = True


class SourceReference(BaseModel):
    """Source reference model."""
    doc_id: str
    doc_name: str
    chunk_id: str
    content: str
    score: float


class RagResponse(BaseModel):
    """RAG response model."""
    answer: str
    sources: List[SourceReference]
    query: str
    success: bool = True
    message: Optional[str] = None


# RAG system prompt
RAG_SYSTEM_PROMPT = """你是一个专业的知识库问答助手。请根据以下上下文信息回答用户的问题。

要求：
1. 只基于提供的上下文信息回答，不要编造信息
2. 如果上下文中没有相关信息，请明确告知用户
3. 回答要准确、简洁、有条理
4. 如果需要，可以引用上下文中的具体内容

上下文信息：
{context}

用户问题：{question}

请给出你的回答："""


async def generate_answer_stream_generator(request: RagRequest, db: Session):
    """Async generator for streaming answer."""
    try:
        logger.info(f"Generating streaming answer for query: {request.query}, kb_id: {request.kb_id}")

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

        # Perform search to get relevant chunks
        search_service = SearchService(db, embedding_provider)
        search_response = await search_service.search(
            kb_id=request.kb_id,
            query=request.query,
            top_k=request.top_k or 5
        )

        # Build context from search results
        context_parts = []
        sources = []

        for result in search_response.results:
            context_parts.append(f"[{result.doc_name}]\n{result.content}")
            sources.append({
                "doc_id": result.doc_id,
                "doc_name": result.doc_name,
                "chunk_id": result.chunk_id,
                "content": result.content,
                "score": result.score
            })

        context = "\n\n---\n\n".join(context_parts)

        # First yield sources
        if request.include_sources:
            yield f"data: {json.dumps({'type': 'sources', 'data': sources})}\n\n"
            await asyncio.sleep(0.1)

        # Generate answer using LLM with streaming
        llm_provider = None

        if settings.llm_api_key:
            llm_provider = SiliconFlowProvider(
                api_key=settings.llm_api_key,
                model=settings.llm_model or "Qwen/Qwen2-7B-Instruct",
                temperature=0.7,
                max_tokens=2048
           )

        if llm_provider and sources:
            prompt = RAG_SYSTEM_PROMPT.format(
                context=context,
                question=request.query
            )

            try:
                async for chunk in llm_provider.generate_stream(prompt):
                    yield f"data: {json.dumps({'type': 'content', 'data': chunk})}\n\n"
            except Exception as e:
                logger.warning(f"LLM streaming failed: {e}, falling back to context")
                fallback = f"基于搜索结果，以下是与您问题相关的信息：\n\n{context}"
                for i in range(0, len(fallback), 20):
                    yield f"data: {json.dumps({'type': 'content', 'data': fallback[i:i+20]})}\n\n"
                    await asyncio.sleep(0.05)
        elif sources:
            fallback = f"基于搜索结果，以下是与您问题相关的信息：\n\n{context}"
            for i in range(0, len(fallback), 20):
                yield f"data: {json.dumps({'type': 'content', 'data': fallback[i:i+20]})}\n\n"
                await asyncio.sleep(0.05)
        else:
            yield f"data: {json.dumps({'type': 'content', 'data': '抱歉，我在知识库中没有找到与您问题相关的信息。'})}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    except NotFoundError as e:
        logger.warning(f"Knowledge base not found: {request.kb_id}")
        yield f"data: {json.dumps({'type': 'error', 'data': e.message})}\n\n"
    except ValidationError as e:
        logger.warning(f"Validation error in RAG: {e.message}")
        yield f"data: {json.dumps({'type': 'error', 'data': e.message})}\n\n"
    except Exception as e:
        logger.error(f"Error generating streaming answer: {str(e)}")
        yield f"data: {json.dumps({'type': 'error', 'data': '生成回答时出错'})}\n\n"


@router.post("/answer/stream")
async def generate_answer_stream(request: RagRequest, db: Session = Depends(get_db)):
    """Generate answer from knowledge base using RAG with streaming."""
    return StreamingResponse(
        generate_answer_stream_generator(request, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.post("/answer", response_model=dict)
async def generate_answer(request: RagRequest, db: Session = Depends(get_db)):
    """Generate answer from knowledge base using RAG.

    Args:
        request: RAG request containing kb_id, query, and optional top_k
        db: Database session

    Returns:
        Answer with source references
    """
    try:
        logger.info(f"Generating answer for query: {request.query}, kb_id: {request.kb_id}")

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

        # Perform search to get relevant chunks
        search_service = SearchService(db, embedding_provider)
        search_response = await search_service.search(
            kb_id=request.kb_id,
            query=request.query,
            top_k=request.top_k or 5
        )

        if not search_response.results:
            return {
                "success": True,
                "data": {
                    "answer": "抱歉，我在知识库中没有找到与您问题相关的信息。",
                    "sources": [],
                    "query": request.query
                },
                "message": None
            }

        # Build context from search results
        context_parts = []
        sources = []

        for result in search_response.results:
            context_parts.append(f"[{result.doc_name}]\n{result.content}")
            sources.append({
                "doc_id": result.doc_id,
                "doc_name": result.doc_name,
                "chunk_id": result.chunk_id,
                "content": result.content,
                "score": result.score
            })

        context = "\n\n---\n\n".join(context_parts)

        # Generate answer using LLM
        llm_provider = None

        if settings.llm_api_key:
            llm_provider = SiliconFlowProvider(
                api_key=settings.llm_api_key,
                model=settings.llm_model or "Qwen/Qwen2-7B-Instruct",
                temperature=0.7,
                max_tokens=2048
            )

        if llm_provider:
            # Build prompt
            prompt = RAG_SYSTEM_PROMPT.format(
                context=context,
                question=request.query
            )

            try:
                answer = await llm_provider.generate(prompt)
            except Exception as e:
                logger.warning(f"LLM generation failed: {e}, falling back to context")
                answer = f"基于搜索结果，以下是与您问题相关的信息：\n\n{context}"
        else:
            # No LLM available, return context as answer
            answer = f"基于搜索结果，以下是与您问题相关的信息：\n\n{context}"

        return {
            "success": True,
            "data": {
                "answer": answer,
                "sources": sources if request.include_sources else [],
                "query": request.query
            },
            "message": None
        }

    except NotFoundError as e:
        logger.warning(f"Knowledge base not found: {request.kb_id}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except ValidationError as e:
        logger.warning(f"Validation error in RAG: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error generating answer: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate answer"
        )