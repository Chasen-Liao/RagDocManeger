"""
Search Tools for RagDocMan Agent

This module provides search tools that integrate hybrid retrieval (vector + keyword)
with reranking capabilities for the RagDocMan Agent.

Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
"""

import logging
from typing import Type, Optional, Any

from pydantic import Field

from .base import ToolInput, ToolOutput, BaseRagDocManTool
from services.search_service import SearchService

# Configure logger
logger = logging.getLogger(__name__)


class SearchInput(ToolInput):
    """
    Input schema for search tool.
    
    **Validates: Requirements 8.1, 8.3**
    """
    
    query: str = Field(
        description="搜索查询文本"
    )
    kb_id: str = Field(
        description="知识库 ID"
    )
    top_k: int = Field(
        default=5,
        description="返回结果数量，默认为 5",
        ge=1,
        le=50
    )


class SearchTool(BaseRagDocManTool):
    """
    Search tool for hybrid retrieval with reranking.
    
    This tool performs hybrid search (vector + keyword) in a knowledge base
    and uses a reranker to order results by relevance.
    
    **Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5**
    
    Features:
    - Hybrid retrieval combining vector and keyword search
    - Reranking for improved result quality
    - Configurable top_k parameter
    - Returns results with scores and metadata
    - Graceful handling of empty results
    """
    
    name: str = "search"
    description: str = (
        "在知识库中搜索相关文档。使用混合检索（向量搜索 + 关键词搜索）"
        "并通过重排序模型对结果进行排序。返回最相关的文档片段及其分数和元数据。"
    )
    args_schema: Type[ToolInput] = SearchInput
    
    # Service dependency
    search_service: Any = Field(
        description="Search service for executing searches"
    )
    
    def __init__(self, search_service: SearchService, **kwargs):
        """
        Initialize search tool.
        
        Args:
            search_service: SearchService instance for executing searches
            **kwargs: Additional arguments passed to BaseRagDocManTool
        """
        super().__init__(search_service=search_service, **kwargs)
    
    async def _aexecute(
        self,
        query: str,
        kb_id: str,
        top_k: int = 5
    ) -> ToolOutput:
        """
        Execute search asynchronously.
        
        This method performs hybrid retrieval (vector + keyword search)
        and applies reranking to return the most relevant results.
        
        **Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5**
        
        Args:
            query: Search query text
            kb_id: Knowledge base ID to search in
            top_k: Number of top results to return (default: 5)
            
        Returns:
            ToolOutput with search results including:
            - results: List of search results with content, score, and metadata
            - total_count: Total number of results found
            - query: Original query text
            
        Raises:
            ValueError: If query is empty or knowledge base doesn't exist
            Exception: If search operation fails
        """
        try:
            # Validate inputs
            if not query or not query.strip():
                return self._create_error_output(
                    message="搜索失败",
                    error="查询文本不能为空"
                )
            
            if not kb_id or not kb_id.strip():
                return self._create_error_output(
                    message="搜索失败",
                    error="知识库 ID 不能为空"
                )
            
            # Log search operation
            self._log_execution_start(
                f"Searching in knowledge base {kb_id} with query: {query[:50]}..."
            )
            
            # Execute search using search service
            # The search service handles:
            # - Hybrid retrieval (vector + keyword)
            # - Reranking with fallback
            # - Result formatting
            search_response = await self.search_service.search(
                kb_id=kb_id,
                query=query,
                top_k=top_k
            )
            
            # Handle empty results gracefully (Requirement 8.5)
            if not search_response.results or len(search_response.results) == 0:
                logger.info(f"No results found for query: {query}")
                return self._create_success_output(
                    message=f"未找到与查询 '{query}' 相关的文档",
                    data={
                        "query": query,
                        "results": [],
                        "total_count": 0
                    }
                )
            
            # Format results with scores and metadata (Requirement 8.4)
            formatted_results = []
            for result in search_response.results:
                formatted_results.append({
                    "content": result.content,
                    "score": result.score,
                    "metadata": {
                        "chunk_id": result.chunk_id,
                        "doc_id": result.doc_id,
                        "doc_name": result.doc_name
                    }
                })
            
            # Log success
            logger.info(
                f"Search completed successfully: found {len(formatted_results)} results"
            )
            
            # Return successful output
            return self._create_success_output(
                message=f"找到 {len(formatted_results)} 个相关结果",
                data={
                    "query": query,
                    "results": formatted_results,
                    "total_count": search_response.total_count
                }
            )
            
        except ValueError as e:
            # Handle validation errors
            error_msg = str(e)
            logger.warning(f"Search validation error: {error_msg}")
            return self._create_error_output(
                message="搜索失败",
                error=error_msg
            )
            
        except Exception as e:
            # Handle unexpected errors
            error_msg = str(e)
            self._log_error("Search operation", e)
            return self._create_error_output(
                message="搜索过程中发生错误",
                error=error_msg
            )
    
    def _execute(
        self,
        query: str,
        kb_id: str,
        top_k: int = 5
    ) -> ToolOutput:
        """
        Execute search synchronously.
        
        This is a synchronous wrapper around the async _aexecute method.
        
        Args:
            query: Search query text
            kb_id: Knowledge base ID to search in
            top_k: Number of top results to return (default: 5)
            
        Returns:
            ToolOutput with search results
        """
        import asyncio
        
        # Get or create event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Run async method
        return loop.run_until_complete(
            self._aexecute(query=query, kb_id=kb_id, top_k=top_k)
        )


class SearchWithRewriteTool(BaseRagDocManTool):
    """
    Advanced search tool with query rewriting.
    
    This tool performs search with automatic query rewriting to improve
    retrieval quality by generating multiple query variations.
    
    **Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5**
    
    Features:
    - Automatic query rewriting using LLM
    - Hybrid retrieval on multiple query variations
    - Result deduplication and reranking
    - Configurable top_k parameter
    - Returns results with scores and metadata
    """
    
    name: str = "search_with_rewrite"
    description: str = (
        "在知识库中搜索相关文档，使用查询重写技术提高检索质量。"
        "系统会自动生成多个查询变体，执行混合检索，并对结果去重和重排序。"
    )
    args_schema: Type[ToolInput] = SearchInput
    
    # Service dependency
    search_service: Any = Field(
        description="Search service for executing searches"
    )
    
    def __init__(self, search_service: SearchService, **kwargs):
        """
        Initialize search with rewrite tool.
        
        Args:
            search_service: SearchService instance for executing searches
            **kwargs: Additional arguments passed to BaseRagDocManTool
        """
        super().__init__(search_service=search_service, **kwargs)
    
    async def _aexecute(
        self,
        query: str,
        kb_id: str,
        top_k: int = 5
    ) -> ToolOutput:
        """
        Execute search with query rewriting asynchronously.
        
        Args:
            query: Search query text
            kb_id: Knowledge base ID to search in
            top_k: Number of top results to return (default: 5)
            
        Returns:
            ToolOutput with search results and rewritten query information
        """
        try:
            # Validate inputs
            if not query or not query.strip():
                return self._create_error_output(
                    message="搜索失败",
                    error="查询文本不能为空"
                )
            
            if not kb_id or not kb_id.strip():
                return self._create_error_output(
                    message="搜索失败",
                    error="知识库 ID 不能为空"
                )
            
            # Log search operation
            self._log_execution_start(
                f"Searching with rewrite in KB {kb_id}: {query[:50]}..."
            )
            
            # Execute search with rewriting
            search_response = await self.search_service.search_with_rewrite(
                kb_id=kb_id,
                query=query,
                top_k=top_k
            )
            
            # Handle empty results gracefully
            if not search_response.results or len(search_response.results) == 0:
                logger.info(f"No results found for query: {query}")
                return self._create_success_output(
                    message=f"未找到与查询 '{query}' 相关的文档",
                    data={
                        "query": query,
                        "rewritten_query": search_response.rewritten_query,
                        "results": [],
                        "total_count": 0
                    }
                )
            
            # Format results with scores and metadata
            formatted_results = []
            for result in search_response.results:
                formatted_results.append({
                    "content": result.content,
                    "score": result.score,
                    "metadata": {
                        "chunk_id": result.chunk_id,
                        "doc_id": result.doc_id,
                        "doc_name": result.doc_name
                    }
                })
            
            # Log success
            logger.info(
                f"Search with rewrite completed: found {len(formatted_results)} results"
            )
            
            # Return successful output
            return self._create_success_output(
                message=f"找到 {len(formatted_results)} 个相关结果",
                data={
                    "query": query,
                    "rewritten_query": search_response.rewritten_query,
                    "results": formatted_results,
                    "total_count": search_response.total_count
                }
            )
            
        except ValueError as e:
            error_msg = str(e)
            logger.warning(f"Search validation error: {error_msg}")
            return self._create_error_output(
                message="搜索失败",
                error=error_msg
            )
            
        except Exception as e:
            error_msg = str(e)
            self._log_error("Search with rewrite operation", e)
            return self._create_error_output(
                message="搜索过程中发生错误",
                error=error_msg
            )
    
    def _execute(
        self,
        query: str,
        kb_id: str,
        top_k: int = 5
    ) -> ToolOutput:
        """
        Execute search with rewriting synchronously.
        
        Args:
            query: Search query text
            kb_id: Knowledge base ID to search in
            top_k: Number of top results to return (default: 5)
            
        Returns:
            ToolOutput with search results
        """
        import asyncio
        
        # Get or create event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Run async method
        return loop.run_until_complete(
            self._aexecute(query=query, kb_id=kb_id, top_k=top_k)
        )



class RAGGenerateInput(ToolInput):
    """
    Input schema for RAG generation tool.
    
    **Validates: Requirements 9.1, 9.2, 9.3**
    """
    
    question: str = Field(
        description="用户问题"
    )
    kb_id: str = Field(
        description="知识库 ID"
    )
    top_k: int = Field(
        default=5,
        description="检索文档数量，默认为 5",
        ge=1,
        le=20
    )
    stream: bool = Field(
        default=False,
        description="是否启用流式输出"
    )


class RAGGenerateTool(BaseRagDocManTool):
    """
    RAG (Retrieval-Augmented Generation) tool for generating answers based on knowledge base.
    
    This tool combines search and LLM to generate contextual answers:
    1. Retrieves relevant documents from knowledge base using hybrid search
    2. Builds context from retrieved documents
    3. Constructs prompt template with context and question
    4. Generates answer using LLM
    5. Returns answer with source citations
    
    **Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5**
    
    Features:
    - Integrates search and LLM for answer generation
    - Context building from retrieved documents
    - Prompt template with context and question
    - Streaming support for real-time responses
    - Returns answers with source citations
    """
    
    name: str = "rag_generate"
    description: str = (
        "基于知识库生成答案。该工具会从知识库中检索相关文档，"
        "构建上下文，并使用 LLM 生成准确的答案。支持流式输出和来源引用。"
    )
    args_schema: Type[ToolInput] = RAGGenerateInput
    
    # Service dependencies
    search_service: Any = Field(
        description="Search service for retrieving documents"
    )
    llm_provider: Any = Field(
        description="LLM provider for generating answers"
    )
    
    def __init__(
        self,
        search_service: SearchService,
        llm_provider: Any,
        **kwargs
    ):
        """
        Initialize RAG generation tool.
        
        Args:
            search_service: SearchService instance for document retrieval
            llm_provider: LLM provider instance for answer generation
            **kwargs: Additional arguments passed to BaseRagDocManTool
        """
        super().__init__(
            search_service=search_service,
            llm_provider=llm_provider,
            **kwargs
        )
    
    def _build_context(self, search_results: list) -> str:
        """
        Build context string from search results.
        
        **Validates: Requirement 9.2**
        
        Args:
            search_results: List of search results with content and metadata
            
        Returns:
            Formatted context string
        """
        if not search_results:
            return ""
        
        context_parts = []
        for idx, result in enumerate(search_results, 1):
            content = result.get("content", "")
            metadata = result.get("metadata", {})
            doc_name = metadata.get("doc_name", "未知文档")
            
            # Format each document chunk with source information
            context_parts.append(
                f"[文档 {idx}: {doc_name}]\n{content}"
            )
        
        return "\n\n".join(context_parts)
    
    def _build_prompt(self, question: str, context: str) -> str:
        """
        Build prompt template with context and question.
        
        **Validates: Requirement 9.3**
        
        Args:
            question: User's question
            context: Context built from retrieved documents
            
        Returns:
            Formatted prompt string
        """
        if not context:
            # No context available - inform LLM
            prompt = f"""请回答以下问题。注意：当前没有找到相关的上下文信息。

问题：{question}

请明确说明没有找到相关信息，并建议用户提供更多细节或尝试不同的问题。"""
        else:
            # Context available - use RAG pattern
            prompt = f"""请基于以下上下文信息回答问题。

上下文信息：
{context}

问题：{question}

请基于上下文提供准确的答案。如果上下文中没有足够的信息来回答问题，请明确说明。在回答时，请引用相关的文档来源。"""
        
        return prompt
    
    def _extract_sources(self, search_results: list) -> list:
        """
        Extract source citations from search results.
        
        **Validates: Requirement 9.4**
        
        Args:
            search_results: List of search results
            
        Returns:
            List of source citations with content preview and metadata
        """
        sources = []
        for result in search_results:
            content = result.get("content", "")
            score = result.get("score", 0.0)
            metadata = result.get("metadata", {})
            
            # Create source citation with preview (first 200 chars)
            content_preview = content[:200] + "..." if len(content) > 200 else content
            
            sources.append({
                "content_preview": content_preview,
                "score": score,
                "doc_id": metadata.get("doc_id"),
                "doc_name": metadata.get("doc_name"),
                "chunk_id": metadata.get("chunk_id")
            })
        
        return sources
    
    async def _aexecute(
        self,
        question: str,
        kb_id: str,
        top_k: int = 5,
        stream: bool = False
    ) -> ToolOutput:
        """
        Execute RAG generation asynchronously.
        
        This method performs the complete RAG pipeline:
        1. Retrieve relevant documents (Requirement 9.1)
        2. Build context from documents (Requirement 9.2)
        3. Construct prompt template (Requirement 9.3)
        4. Generate answer with LLM
        5. Return answer with sources (Requirement 9.4)
        
        **Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5**
        
        Args:
            question: User's question
            kb_id: Knowledge base ID to search in
            top_k: Number of documents to retrieve (default: 5)
            stream: Whether to enable streaming output (default: False)
            
        Returns:
            ToolOutput with generated answer and source citations
            
        Raises:
            ValueError: If question is empty or knowledge base doesn't exist
            Exception: If RAG generation fails
        """
        try:
            # Validate inputs
            if not question or not question.strip():
                return self._create_error_output(
                    message="RAG 生成失败",
                    error="问题不能为空"
                )
            
            if not kb_id or not kb_id.strip():
                return self._create_error_output(
                    message="RAG 生成失败",
                    error="知识库 ID 不能为空"
                )
            
            # Log operation start
            self._log_execution_start(
                f"RAG generation for question: {question[:50]}... in KB {kb_id}"
            )
            
            # Step 1: Retrieve relevant documents (Requirement 9.1)
            logger.info(f"[{self.name}] Retrieving documents from knowledge base")
            search_response = await self.search_service.search(
                kb_id=kb_id,
                query=question,
                top_k=top_k
            )
            
            # Handle case with no search results
            if not search_response.results or len(search_response.results) == 0:
                logger.warning(f"[{self.name}] No documents found for question")
                
                # Still generate answer but inform about lack of context
                prompt = self._build_prompt(question, "")
                # Support both custom LLMProvider and LangChain ChatOpenAI
                from langchain_core.language_models import BaseChatModel
                if isinstance(self.llm_provider, BaseChatModel):
                    response = await self.llm_provider.ainvoke(prompt)
                    answer = response.content if hasattr(response, 'content') else str(response)
                else:
                    answer = await self.llm_provider.generate(prompt)
                
                return self._create_success_output(
                    message="已生成答案（未找到相关文档）",
                    data={
                        "question": question,
                        "answer": answer,
                        "sources": [],
                        "context_used": False
                    }
                )
            
            # Format search results
            formatted_results = []
            for result in search_response.results:
                formatted_results.append({
                    "content": result.content,
                    "score": result.score,
                    "metadata": {
                        "chunk_id": result.chunk_id,
                        "doc_id": result.doc_id,
                        "doc_name": result.doc_name
                    }
                })
            
            # Step 2: Build context from retrieved documents (Requirement 9.2)
            logger.info(f"[{self.name}] Building context from {len(formatted_results)} documents")
            context = self._build_context(formatted_results)
            
            # Step 3: Construct prompt template (Requirement 9.3)
            logger.info(f"[{self.name}] Constructing prompt template")
            prompt = self._build_prompt(question, context)
            
            # Step 4: Generate answer with LLM
            logger.info(f"[{self.name}] Generating answer with LLM")
            
            # Check if streaming is requested (Requirement 9.5)
            if stream:
                # For streaming, we need to return a different format
                # This will be handled by the caller
                logger.info(f"[{self.name}] Streaming mode requested")
                
                # Extract sources for citation (Requirement 9.4)
                sources = self._extract_sources(formatted_results)
                
                return self._create_success_output(
                    message="RAG 生成已启动（流式模式）",
                    data={
                        "question": question,
                        "answer": "[STREAMING]",  # Placeholder for streaming
                        "sources": sources,
                        "context_used": True,
                        "stream": True,
                        "prompt": prompt  # Include prompt for streaming
                    }
                )
            else:
                # Non-streaming mode
                # Support both custom LLMProvider and LangChain ChatOpenAI
                from langchain_core.language_models import BaseChatModel
                if isinstance(self.llm_provider, BaseChatModel):
                    # LangChain ChatOpenAI - use invoke
                    response = await self.llm_provider.ainvoke(prompt)
                    answer = response.content if hasattr(response, 'content') else str(response)
                else:
                    # Custom LLMProvider
                    answer = await self.llm_provider.generate(prompt)
                
                # Step 5: Extract sources for citation (Requirement 9.4)
                sources = self._extract_sources(formatted_results)
                
                logger.info(f"[{self.name}] RAG generation completed successfully")
                
                return self._create_success_output(
                    message="成功生成答案",
                    data={
                        "question": question,
                        "answer": answer,
                        "sources": sources,
                        "context_used": True
                    }
                )
            
        except ValueError as e:
            # Handle validation errors
            error_msg = str(e)
            logger.warning(f"[{self.name}] Validation error: {error_msg}")
            return self._create_error_output(
                message="RAG 生成失败",
                error=error_msg
            )
            
        except Exception as e:
            # Handle unexpected errors
            error_msg = str(e)
            self._log_error("RAG generation", e)
            return self._create_error_output(
                message="RAG 生成过程中发生错误",
                error=error_msg
            )
    
    async def generate_stream(
        self,
        question: str,
        kb_id: str,
        top_k: int = 5
    ):
        """
        Generate answer with streaming support.
        
        This is a separate method for streaming to allow yielding chunks.
        
        **Validates: Requirement 9.5**
        
        Args:
            question: User's question
            kb_id: Knowledge base ID
            top_k: Number of documents to retrieve
            
        Yields:
            Chunks of generated answer
            
        Raises:
            ValueError: If inputs are invalid
            Exception: If generation fails
        """
        try:
            # Validate inputs
            if not question or not question.strip():
                raise ValueError("问题不能为空")
            
            if not kb_id or not kb_id.strip():
                raise ValueError("知识库 ID 不能为空")
            
            # Retrieve documents
            logger.info(f"[{self.name}] Retrieving documents for streaming RAG")
            search_response = await self.search_service.search(
                kb_id=kb_id,
                query=question,
                top_k=top_k
            )
            
            # Build context
            formatted_results = []
            if search_response.results:
                for result in search_response.results:
                    formatted_results.append({
                        "content": result.content,
                        "score": result.score,
                        "metadata": {
                            "chunk_id": result.chunk_id,
                            "doc_id": result.doc_id,
                            "doc_name": result.doc_name
                        }
                    })
            
            context = self._build_context(formatted_results)
            prompt = self._build_prompt(question, context)

            # Stream answer generation - support both custom and LangChain providers
            logger.info(f"[{self.name}] Starting streaming generation")
            from langchain_core.language_models import BaseChatModel
            if isinstance(self.llm_provider, BaseChatModel):
                # LangChain ChatOpenAI - use astream
                async for chunk in self.llm_provider.astream(prompt):
                    content = chunk.content if hasattr(chunk, 'content') else str(chunk)
                    yield content
            else:
                # Custom LLMProvider
                async for chunk in self.llm_provider.generate_stream(prompt):
                    yield chunk
            
            logger.info(f"[{self.name}] Streaming generation completed")
            
        except Exception as e:
            error_msg = str(e)
            self._log_error("Streaming RAG generation", e)
            raise
    
    def _execute(
        self,
        question: str,
        kb_id: str,
        top_k: int = 5,
        stream: bool = False
    ) -> ToolOutput:
        """
        Execute RAG generation synchronously.
        
        This is a synchronous wrapper around the async _aexecute method.
        
        Args:
            question: User's question
            kb_id: Knowledge base ID
            top_k: Number of documents to retrieve (default: 5)
            stream: Whether to enable streaming (default: False)
            
        Returns:
            ToolOutput with generated answer and sources
        """
        import asyncio
        
        # Get or create event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Run async method
        return loop.run_until_complete(
            self._aexecute(
                question=question,
                kb_id=kb_id,
                top_k=top_k,
                stream=stream
            )
        )
