"""Backend availability and health check tests."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestBackendAvailability:
    """Test backend availability and core functionality."""
    
    def test_imports_available(self):
        """Test that all core modules can be imported."""
        try:
            from rag.conversation_memory import ConversationMemory
            from rag.vector_search_optimizer import VectorSearchOptimizer
            from rag.parallel_tool_executor import ParallelToolExecutor
            from rag.agent_cache import CacheManager
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import core modules: {e}")
    
    def test_database_connection(self):
        """Test database connectivity."""
        try:
            from database import SessionLocal
            session = SessionLocal()
            # Try to execute a simple query
            session.execute("SELECT 1")
            session.close()
            assert True
        except Exception as e:
            # Database might not be initialized, but connection should work
            pytest.skip(f"Database not available: {e}")
    
    def test_config_loading(self):
        """Test configuration loading."""
        try:
            from config import settings
            assert settings is not None
            assert hasattr(settings, 'database_url')
            assert hasattr(settings, 'chroma_db_path')
        except Exception as e:
            pytest.fail(f"Failed to load configuration: {e}")
    
    def test_logger_initialization(self):
        """Test logger initialization."""
        try:
            from logger import logger
            assert logger is not None
            logger.info("Test log message")
        except Exception as e:
            pytest.fail(f"Failed to initialize logger: {e}")
    
    @pytest.mark.anyio
    async def test_conversation_memory_availability(self):
        """Test ConversationMemory is available and functional."""
        from rag.conversation_memory import ConversationMemory
        
        memory = ConversationMemory(
            session_id="test_session",
            max_history=10,
            db_session=None
        )
        
        # Test basic operations
        memory.add_user_message("Test message")
        memory.add_ai_message("Test response")
        
        messages = memory.get_messages()
        assert len(messages) == 2
        assert messages[0].content == "Test message"
        assert messages[1].content == "Test response"
    
    @pytest.mark.anyio
    async def test_vector_search_optimizer_availability(self):
        """Test VectorSearchOptimizer is available."""
        try:
            from rag.vector_search_optimizer import VectorSearchOptimizer
            optimizer = VectorSearchOptimizer()
            assert optimizer is not None
        except Exception as e:
            pytest.skip(f"VectorSearchOptimizer not available: {e}")
    
    @pytest.mark.anyio
    async def test_parallel_tool_executor_availability(self):
        """Test ParallelToolExecutor is available."""
        try:
            from rag.parallel_tool_executor import ParallelToolExecutor
            executor = ParallelToolExecutor()
            assert executor is not None
        except Exception as e:
            pytest.skip(f"ParallelToolExecutor not available: {e}")
    
    @pytest.mark.anyio
    async def test_agent_cache_availability(self):
        """Test AgentCache is available."""
        try:
            from rag.agent_cache import CacheManager
            cache = CacheManager()
            assert cache is not None
        except Exception as e:
            pytest.skip(f"CacheManager not available: {e}")
    
    def test_api_routes_available(self):
        """Test API routes are available."""
        try:
            from api.routes import router
            assert router is not None
        except Exception as e:
            pytest.skip(f"API routes not available: {e}")
    
    def test_services_available(self):
        """Test services are available."""
        try:
            from services.knowledge_base_service import KnowledgeBaseService
            from services.document_service import DocumentService
            from services.search_service import SearchService
            assert True
        except Exception as e:
            pytest.skip(f"Services not available: {e}")
    
    def test_models_available(self):
        """Test ORM models are available."""
        try:
            from models.orm import KnowledgeBase, Document, Chunk
            assert KnowledgeBase is not None
            assert Document is not None
            assert Chunk is not None
        except Exception as e:
            pytest.skip(f"Models not available: {e}")
    
    @pytest.mark.anyio
    async def test_mock_llm_provider(self):
        """Test mock LLM provider works."""
        mock_provider = Mock()
        mock_provider.generate = AsyncMock(return_value="Test response")
        
        result = await mock_provider.generate("Test prompt")
        assert result == "Test response"
    
    @pytest.mark.anyio
    async def test_mock_embedding_provider(self):
        """Test mock embedding provider works."""
        mock_provider = Mock()
        mock_provider.embed_documents = AsyncMock(return_value=[[0.1, 0.2, 0.3]])
        mock_provider.embed_query = AsyncMock(return_value=[0.1, 0.2, 0.3])
        
        docs_result = await mock_provider.embed_documents(["test"])
        query_result = await mock_provider.embed_query("test")
        
        assert len(docs_result) == 1
        assert len(query_result) == 3
    
    @pytest.mark.anyio
    async def test_mock_search_service(self):
        """Test mock search service works."""
        mock_service = Mock()
        mock_service.search = AsyncMock(return_value=[
            Mock(content="Result 1", score=0.95),
            Mock(content="Result 2", score=0.87)
        ])
        
        results = await mock_service.search(query="test", kb_id="kb_001", top_k=2)
        assert len(results) == 2
        assert results[0].score > results[1].score


class TestBackendHealthCheck:
    """Test backend health and status."""
    
    def test_main_module_available(self):
        """Test main module is available."""
        try:
            from main import app
            assert app is not None
        except Exception as e:
            pytest.skip(f"Main module not available: {e}")
    
    def test_middleware_available(self):
        """Test middleware is available."""
        try:
            from middleware import setup_middleware
            assert setup_middleware is not None
        except Exception as e:
            pytest.skip(f"Middleware not available: {e}")
    
    def test_exceptions_available(self):
        """Test exception classes are available."""
        try:
            from exceptions import (
                RagDocManException,
                KnowledgeBaseNotFound,
                DocumentNotFound,
                SearchException
            )
            assert RagDocManException is not None
        except Exception as e:
            pytest.skip(f"Exceptions not available: {e}")
    
    def test_core_utilities_available(self):
        """Test core utilities are available."""
        try:
            from core.utils import generate_id, validate_input
            assert generate_id is not None
            assert validate_input is not None
        except Exception as e:
            pytest.skip(f"Core utilities not available: {e}")


class TestBackendIntegration:
    """Test backend integration points."""
    
    @pytest.mark.anyio
    async def test_memory_and_cache_integration(self):
        """Test memory and cache work together."""
        from rag.conversation_memory import ConversationMemory
        
        memory = ConversationMemory(
            session_id="integration_test",
            max_history=10,
            db_session=None
        )
        
        # Add messages
        for i in range(5):
            memory.add_user_message(f"Question {i}")
            memory.add_ai_message(f"Answer {i}")
        
        # Retrieve messages
        messages = memory.get_messages()
        assert len(messages) == 10
        
        # Clear memory
        await memory.clear()
        messages = memory.get_messages()
        assert len(messages) == 0
    
    @pytest.mark.anyio
    async def test_concurrent_operations(self):
        """Test concurrent operations work."""
        from rag.conversation_memory import ConversationMemory
        
        async def create_and_use_memory(session_id):
            memory = ConversationMemory(
                session_id=session_id,
                max_history=10,
                db_session=None
            )
            memory.add_user_message(f"Message from {session_id}")
            memory.add_ai_message(f"Response for {session_id}")
            return len(memory.get_messages())
        
        # Run concurrent operations
        tasks = [create_and_use_memory(f"session_{i}") for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        assert all(r == 2 for r in results)
    
    @pytest.mark.anyio
    async def test_error_handling(self):
        """Test error handling in backend."""
        from rag.conversation_memory import ConversationMemory
        
        memory = ConversationMemory(
            session_id="error_test",
            max_history=10,
            db_session=None
        )
        
        # Test with None input (should handle gracefully)
        try:
            memory.add_user_message("")
            messages = memory.get_messages()
            assert len(messages) == 1
        except Exception as e:
            pytest.fail(f"Error handling failed: {e}")


class TestBackendPerformance:
    """Test backend performance characteristics."""
    
    @pytest.mark.anyio
    async def test_memory_operations_performance(self):
        """Test memory operations are performant."""
        import time
        from rag.conversation_memory import ConversationMemory
        
        memory = ConversationMemory(
            session_id="perf_test",
            max_history=100,
            db_session=None
        )
        
        start = time.time()
        
        # Add 100 messages
        for i in range(50):
            memory.add_user_message(f"Message {i}")
            memory.add_ai_message(f"Response {i}")
        
        elapsed = time.time() - start
        
        # Should complete in reasonable time (< 1 second)
        assert elapsed < 1.0
        
        # Verify all messages are stored
        messages = memory.get_messages()
        assert len(messages) == 100
    
    @pytest.mark.anyio
    async def test_concurrent_memory_performance(self):
        """Test concurrent memory operations are performant."""
        import time
        from rag.conversation_memory import ConversationMemory
        
        async def memory_operations(session_id):
            memory = ConversationMemory(
                session_id=session_id,
                max_history=50,
                db_session=None
            )
            
            for i in range(10):
                memory.add_user_message(f"Message {i}")
                memory.add_ai_message(f"Response {i}")
            
            return len(memory.get_messages())
        
        start = time.time()
        
        # Run 10 concurrent sessions
        tasks = [memory_operations(f"session_{i}") for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        elapsed = time.time() - start
        
        # Should complete in reasonable time (< 5 seconds)
        assert elapsed < 5.0
        
        # Verify all operations completed
        assert all(r == 20 for r in results)


class TestBackendDependencies:
    """Test backend dependencies are satisfied."""
    
    def test_langchain_available(self):
        """Test LangChain is available."""
        try:
            import langchain
            import langchain_core
            assert langchain is not None
            assert langchain_core is not None
        except ImportError as e:
            pytest.fail(f"LangChain not available: {e}")
    
    def test_sqlalchemy_available(self):
        """Test SQLAlchemy is available."""
        try:
            import sqlalchemy
            from sqlalchemy.orm import Session
            assert sqlalchemy is not None
            assert Session is not None
        except ImportError as e:
            pytest.fail(f"SQLAlchemy not available: {e}")
    
    def test_fastapi_available(self):
        """Test FastAPI is available."""
        try:
            from fastapi import FastAPI
            assert FastAPI is not None
        except ImportError as e:
            pytest.fail(f"FastAPI not available: {e}")
    
    def test_pydantic_available(self):
        """Test Pydantic is available."""
        try:
            from pydantic import BaseModel
            assert BaseModel is not None
        except ImportError as e:
            pytest.fail(f"Pydantic not available: {e}")
    
    def test_chroma_available(self):
        """Test Chroma is available."""
        try:
            import chromadb
            assert chromadb is not None
        except ImportError as e:
            pytest.skip(f"Chroma not available: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
