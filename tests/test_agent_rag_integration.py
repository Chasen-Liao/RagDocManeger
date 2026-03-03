"""Integration tests for Agent-RAG system."""

import pytest
import asyncio
from typing import List
from unittest.mock import Mock, AsyncMock
from sqlalchemy.orm import Session

from rag.agent_service_integration import (
    AgentServiceIntegration,
    ServiceConnectionPool,
    ServiceRegistry
)
from rag.tool_service_interaction import (
    ToolServiceAdapter,
    RetryConfig,
    ServiceResponse,
    RetryStrategy
)


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def mock_llm_provider():
    """Create mock LLM provider."""
    provider = Mock()
    provider.generate = AsyncMock(return_value="Test response")
    return provider


@pytest.fixture
def mock_embedding_provider():
    """Create mock embedding provider."""
    provider = Mock()
    provider.embed_documents = AsyncMock(return_value=[[0.1, 0.2, 0.3]])
    provider.embed_query = AsyncMock(return_value=[0.1, 0.2, 0.3])
    return provider


@pytest.fixture
def mock_reranker_provider():
    """Create mock reranker provider."""
    provider = Mock()
    provider.rerank = AsyncMock(return_value=[{"score": 0.9, "index": 0}])
    return provider


@pytest.fixture
def agent_service_integration(mock_db_session, mock_llm_provider, mock_embedding_provider, mock_reranker_provider):
    """Create AgentServiceIntegration instance."""
    return AgentServiceIntegration(
        db_session=mock_db_session,
        llm_provider=mock_llm_provider,
        embedding_provider=mock_embedding_provider,
        reranker_provider=mock_reranker_provider,
        max_concurrent_agents=5
    )


class TestServiceConnectionPool:
    """Test ServiceConnectionPool."""
    
    def test_connection_pool_initialization(self):
        """Test connection pool initialization."""
        pool = ServiceConnectionPool(max_connections=10)
        assert pool.max_connections == 10
        assert pool.active_connections == 0
    
    @pytest.mark.anyio
    async def test_connection_pool_acquire_release(self):
        """Test acquiring and releasing connections."""
        pool = ServiceConnectionPool(max_connections=2)
        
        async with pool.acquire():
            assert pool.active_connections == 1
        
        assert pool.active_connections == 0
    
    @pytest.mark.anyio
    async def test_connection_pool_concurrent_access(self):
        """Test concurrent access to connection pool."""
        pool = ServiceConnectionPool(max_connections=3)
        
        async def use_connection():
            async with pool.acquire():
                await asyncio.sleep(0.01)
        
        tasks = [use_connection() for _ in range(5)]
        await asyncio.gather(*tasks)
        
        assert pool.active_connections == 0
    
    def test_connection_pool_stats(self):
        """Test connection pool statistics."""
        pool = ServiceConnectionPool(max_connections=5)
        
        stats = pool.get_stats()
        assert stats["max_connections"] == 5
        assert stats["active_connections"] == 0
        assert stats["available_connections"] == 5


class TestAgentServiceIntegration:
    """Test AgentServiceIntegration."""
    
    def test_initialization(self, agent_service_integration):
        """Test initialization."""
        assert agent_service_integration.llm_provider is not None
        assert agent_service_integration.embedding_provider is not None
        assert agent_service_integration.connection_pool is not None
    
    @pytest.mark.anyio
    async def test_get_services(self, agent_service_integration):
        """Test getting services."""
        async with agent_service_integration.get_services() as (kb_svc, doc_svc, search_svc):
            assert kb_svc is not None
            assert doc_svc is not None
            assert search_svc is not None
    
    @pytest.mark.anyio
    async def test_get_knowledge_base_service(self, agent_service_integration):
        """Test getting knowledge base service."""
        service = await agent_service_integration.get_knowledge_base_service()
        assert service is not None
    
    @pytest.mark.anyio
    async def test_get_document_service(self, agent_service_integration):
        """Test getting document service."""
        service = await agent_service_integration.get_document_service()
        assert service is not None
    
    @pytest.mark.anyio
    async def test_get_search_service(self, agent_service_integration):
        """Test getting search service."""
        service = await agent_service_integration.get_search_service()
        assert service is not None
    
    def test_get_shared_database_connection(self, agent_service_integration, mock_db_session):
        """Test getting shared database connection."""
        conn = agent_service_integration.get_shared_database_connection()
        assert conn == mock_db_session
    
    def test_get_connection_pool_stats(self, agent_service_integration):
        """Test getting connection pool statistics."""
        stats = agent_service_integration.get_connection_pool_stats()
        assert "pool_stats" in stats
        assert "services" in stats
    
    @pytest.mark.anyio
    async def test_validate_services(self, agent_service_integration):
        """Test service validation."""
        result = await agent_service_integration.validate_services()
        assert result is True
    
    @pytest.mark.anyio
    async def test_health_check(self, agent_service_integration):
        """Test health check."""
        health = await agent_service_integration.health_check()
        assert health["status"] == "healthy"
        assert "services" in health
        assert "providers" in health


class TestToolServiceInteraction:
    """Test ToolServiceInteraction."""
    
    @pytest.mark.anyio
    async def test_service_call_success(self):
        """Test successful service call."""
        adapter = ToolServiceAdapter()
        
        async def mock_service():
            return {"success": True, "data": {"result": "test"}}
        
        response = await adapter.call_service(mock_service)
        assert response.success is True
        assert response.data["result"] == "test"
    
    @pytest.mark.anyio
    async def test_service_call_with_retry(self):
        """Test service call with retry."""
        config = RetryConfig(max_retries=2, initial_delay=0.01)
        adapter = ToolServiceAdapter(config)
        
        call_count = 0
        
        async def mock_service_with_failure():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Temporary error")
            return {"success": True, "data": {"result": "success"}}
        
        response = await adapter.call_service(mock_service_with_failure)
        assert response.success is True
        assert call_count == 2
    
    @pytest.mark.anyio
    async def test_service_call_timeout(self):
        """Test service call timeout."""
        config = RetryConfig(timeout=0.05, max_retries=1, initial_delay=0.01)
        adapter = ToolServiceAdapter(config)
        
        async def slow_service():
            await asyncio.sleep(1)
            return {"success": True}
        
        response = await adapter.call_service(slow_service)
        assert response.success is False
        assert response.error_code == "TIMEOUT_ERROR"
    
    @pytest.mark.anyio
    async def test_batch_operation(self):
        """Test batch operation."""
        adapter = ToolServiceAdapter()
        
        async def process_item(item):
            return {"success": True, "data": {"item": item, "processed": True}}
        
        items = [1, 2, 3, 4, 5]
        responses = await adapter.call_service_batch(items, process_item, batch_size=2)
        
        assert len(responses) == 5
        assert all(r.success for r in responses)
    
    def test_response_parsing(self):
        """Test response parsing."""
        adapter = ToolServiceAdapter()
        
        response = adapter.parse_response({"success": True, "data": {"key": "value"}})
        assert response.success is True
        assert response.data["key"] == "value"
        
        response = adapter.parse_response([1, 2, 3])
        assert response.success is True
        assert response.data == [1, 2, 3]
        
        response = adapter.parse_response(None)
        assert response.success is True
        assert response.data is None
    
    def test_response_validation(self):
        """Test response validation."""
        adapter = ToolServiceAdapter()
        
        response = ServiceResponse(success=True, data={"field1": "value1", "field2": "value2"})
        assert adapter.validate_response(response, ["field1", "field2"]) is True
        
        response = ServiceResponse(success=True, data={"field1": "value1"})
        with pytest.raises(Exception):
            adapter.validate_response(response, ["field1", "field2"])


class TestEndToEndFlow:
    """Test end-to-end Agent-RAG flow."""
    
    @pytest.mark.anyio
    async def test_user_input_to_response_flow(self, agent_service_integration):
        """Test complete flow: user input to response."""
        async with agent_service_integration.get_services() as (kb_svc, doc_svc, search_svc):
            user_input = "Search for documents about AI"
            
            assert kb_svc is not None
            assert doc_svc is not None
            assert search_svc is not None
    
    @pytest.mark.anyio
    async def test_concurrent_agent_instances(self, agent_service_integration):
        """Test concurrent Agent instances with shared resources."""
        async def agent_task(task_id):
            async with agent_service_integration.get_services() as (kb_svc, doc_svc, search_svc):
                await asyncio.sleep(0.01)
                return task_id
        
        tasks = [agent_task(i) for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 5
        assert all(isinstance(r, int) for r in results)


class TestServiceRegistry:
    """Test ServiceRegistry."""
    
    def test_registry_singleton(self, mock_db_session, mock_llm_provider, mock_embedding_provider):
        """Test registry singleton pattern."""
        ServiceRegistry._instance = None
        ServiceRegistry._integration = None
        
        registry1 = ServiceRegistry.initialize(
            db_session=mock_db_session,
            llm_provider=mock_llm_provider,
            embedding_provider=mock_embedding_provider
        )
        
        registry2 = ServiceRegistry()
        
        assert registry1 is registry2
    
    def test_get_integration(self, mock_db_session, mock_llm_provider, mock_embedding_provider):
        """Test getting integration from registry."""
        ServiceRegistry._instance = None
        ServiceRegistry._integration = None
        
        ServiceRegistry.initialize(
            db_session=mock_db_session,
            llm_provider=mock_llm_provider,
            embedding_provider=mock_embedding_provider
        )
        
        integration = ServiceRegistry.get_integration()
        assert integration is not None
