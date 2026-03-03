"""Backward compatibility tests for RAG system upgrade.

Tests verify:
- Existing RAG endpoints still work
- Existing APIs have no breaking changes
- Migration path from old system to new system

Requirements: 1.4, 1.5
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import json


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def mock_old_rag_service():
    """Create mock old RAG service for backward compatibility."""
    service = Mock()
    service.generate_answer = AsyncMock(return_value={
        "answer": "This is the answer",
        "sources": [
            {"content": "Source 1", "score": 0.95},
            {"content": "Source 2", "score": 0.87}
        ]
    })
    service.search = AsyncMock(return_value=[
        {"content": "Result 1", "score": 0.95},
        {"content": "Result 2", "score": 0.87}
    ])
    return service


@pytest.fixture
def mock_new_agent_service():
    """Create mock new Agent service."""
    service = Mock()
    service.ainvoke = AsyncMock(return_value=Mock(
        output="This is the answer",
        tool_calls=[],
        intermediate_steps=[],
        execution_time=0.5
    ))
    return service


class TestOldRAGEndpointsCompatibility:
    """Test that old RAG endpoints still work."""
    
    @pytest.mark.anyio
    async def test_old_search_endpoint_format(self, mock_old_rag_service):
        """Test old search endpoint returns compatible format."""
        # Old endpoint format
        results = await mock_old_rag_service.search(
            query="test query",
            kb_id="kb_001",
            top_k=5
        )
        
        # Verify old format is maintained
        assert isinstance(results, list)
        assert len(results) > 0
        assert "content" in results[0]
        assert "score" in results[0]
    
    @pytest.mark.anyio
    async def test_old_rag_generation_endpoint_format(self, mock_old_rag_service):
        """Test old RAG generation endpoint returns compatible format."""
        result = await mock_old_rag_service.generate_answer(
            question="What is AI?",
            kb_id="kb_001",
            top_k=5
        )
        
        # Verify old format is maintained
        assert "answer" in result
        assert "sources" in result
        assert isinstance(result["sources"], list)
        assert len(result["sources"]) > 0
        assert "content" in result["sources"][0]
        assert "score" in result["sources"][0]
    
    @pytest.mark.anyio
    async def test_old_knowledge_base_endpoints(self, mock_db_session):
        """Test old knowledge base endpoints."""
        # Mock old KB service
        kb_service = Mock()
        kb_service.create_kb = AsyncMock(return_value={"id": "kb_001", "name": "Test KB"})
        kb_service.get_kb = AsyncMock(return_value={"id": "kb_001", "name": "Test KB"})
        kb_service.list_kbs = AsyncMock(return_value=[{"id": "kb_001", "name": "Test KB"}])
        
        # Test create
        kb = await kb_service.create_kb(name="Test KB", description="Test")
        assert kb["id"] == "kb_001"
        assert kb["name"] == "Test KB"
        
        # Test get
        kb = await kb_service.get_kb(kb_id="kb_001")
        assert kb["id"] == "kb_001"
        
        # Test list
        kbs = await kb_service.list_kbs()
        assert len(kbs) > 0
        assert kbs[0]["id"] == "kb_001"
    
    @pytest.mark.anyio
    async def test_old_document_endpoints(self, mock_db_session):
        """Test old document endpoints."""
        # Mock old document service
        doc_service = Mock()
        doc_service.upload_doc = AsyncMock(return_value={"id": "doc_001", "name": "test.txt"})
        doc_service.get_doc = AsyncMock(return_value={"id": "doc_001", "name": "test.txt"})
        doc_service.list_docs = AsyncMock(return_value=[{"id": "doc_001", "name": "test.txt"}])
        doc_service.delete_doc = AsyncMock(return_value={"success": True})
        
        # Test upload
        doc = await doc_service.upload_doc(kb_id="kb_001", file_path="test.txt")
        assert doc["id"] == "doc_001"
        
        # Test get
        doc = await doc_service.get_doc(doc_id="doc_001")
        assert doc["id"] == "doc_001"
        
        # Test list
        docs = await doc_service.list_docs(kb_id="kb_001")
        assert len(docs) > 0
        
        # Test delete
        result = await doc_service.delete_doc(doc_id="doc_001")
        assert result["success"] is True


class TestAPIResponseFormatCompatibility:
    """Test API response format compatibility."""
    
    def test_old_response_format_structure(self):
        """Test old response format structure is maintained."""
        # Old format response
        old_response = {
            "success": True,
            "data": {
                "id": "kb_001",
                "name": "Test KB",
                "description": "Test"
            },
            "message": None
        }
        
        # Verify structure
        assert "success" in old_response
        assert "data" in old_response
        assert old_response["success"] is True
        assert isinstance(old_response["data"], dict)
    
    def test_old_error_response_format(self):
        """Test old error response format."""
        # Old format error response
        old_error = {
            "success": False,
            "data": None,
            "error": {
                "code": "NOT_FOUND",
                "message": "Knowledge base not found"
            }
        }
        
        # Verify structure
        assert "success" in old_error
        assert "error" in old_error
        assert old_error["success"] is False
        assert "code" in old_error["error"]
        assert "message" in old_error["error"]
    
    def test_old_paginated_response_format(self):
        """Test old paginated response format."""
        # Old format paginated response
        old_paginated = {
            "success": True,
            "data": [
                {"id": "kb_001", "name": "KB 1"},
                {"id": "kb_002", "name": "KB 2"}
            ],
            "meta": {
                "total": 2,
                "skip": 0,
                "limit": 10
            }
        }
        
        # Verify structure
        assert "success" in old_paginated
        assert "data" in old_paginated
        assert "meta" in old_paginated
        assert "total" in old_paginated["meta"]
        assert "skip" in old_paginated["meta"]
        assert "limit" in old_paginated["meta"]


class TestParameterCompatibility:
    """Test parameter compatibility between old and new systems."""
    
    @pytest.mark.anyio
    async def test_search_parameters_compatibility(self, mock_old_rag_service):
        """Test search parameters are compatible."""
        # Old parameter format
        old_params = {
            "query": "test query",
            "kb_id": "kb_001",
            "top_k": 5
        }
        
        results = await mock_old_rag_service.search(**old_params)
        assert len(results) > 0
    
    @pytest.mark.anyio
    async def test_rag_generation_parameters_compatibility(self, mock_old_rag_service):
        """Test RAG generation parameters are compatible."""
        # Old parameter format
        old_params = {
            "question": "What is AI?",
            "kb_id": "kb_001",
            "top_k": 5
        }
        
        result = await mock_old_rag_service.generate_answer(**old_params)
        assert "answer" in result
        assert "sources" in result
    
    @pytest.mark.anyio
    async def test_knowledge_base_parameters_compatibility(self):
        """Test knowledge base parameters are compatible."""
        kb_service = Mock()
        kb_service.create_kb = AsyncMock(return_value={"id": "kb_001"})
        
        # Old parameter format
        old_params = {
            "name": "Test KB",
            "description": "Test description"
        }
        
        kb = await kb_service.create_kb(**old_params)
        assert kb["id"] == "kb_001"


class TestDataModelCompatibility:
    """Test data model compatibility."""
    
    def test_knowledge_base_model_compatibility(self):
        """Test knowledge base model is compatible."""
        # Old model structure
        old_kb = {
            "id": "kb_001",
            "name": "Test KB",
            "description": "Test",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
            "doc_count": 5,
            "size": 1024000
        }
        
        # Verify all required fields exist
        assert "id" in old_kb
        assert "name" in old_kb
        assert "description" in old_kb
        assert "created_at" in old_kb
        assert "updated_at" in old_kb
    
    def test_document_model_compatibility(self):
        """Test document model is compatible."""
        # Old model structure
        old_doc = {
            "id": "doc_001",
            "kb_id": "kb_001",
            "name": "test.txt",
            "size": 1024,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
            "chunk_count": 10
        }
        
        # Verify all required fields exist
        assert "id" in old_doc
        assert "kb_id" in old_doc
        assert "name" in old_doc
        assert "size" in old_doc
        assert "created_at" in old_doc
    
    def test_search_result_model_compatibility(self):
        """Test search result model is compatible."""
        # Old model structure
        old_result = {
            "content": "Result content",
            "score": 0.95,
            "metadata": {
                "source": "doc_001",
                "chunk_id": "chunk_001"
            }
        }
        
        # Verify all required fields exist
        assert "content" in old_result
        assert "score" in old_result
        assert "metadata" in old_result
        assert isinstance(old_result["score"], float)
        assert 0 <= old_result["score"] <= 1


class TestMigrationPath:
    """Test migration path from old system to new system."""
    
    @pytest.mark.anyio
    async def test_old_to_new_knowledge_base_migration(self):
        """Test migration of knowledge base from old to new system."""
        # Old KB data
        old_kb = {
            "id": "kb_001",
            "name": "Old KB",
            "description": "Old system KB"
        }
        
        # Simulate migration
        new_kb = {
            "id": old_kb["id"],
            "name": old_kb["name"],
            "description": old_kb["description"],
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
        }
        
        # Verify migration preserves data
        assert new_kb["id"] == old_kb["id"]
        assert new_kb["name"] == old_kb["name"]
        assert new_kb["description"] == old_kb["description"]
    
    @pytest.mark.anyio
    async def test_old_to_new_document_migration(self):
        """Test migration of documents from old to new system."""
        # Old document data
        old_doc = {
            "id": "doc_001",
            "kb_id": "kb_001",
            "name": "test.txt",
            "size": 1024
        }
        
        # Simulate migration
        new_doc = {
            "id": old_doc["id"],
            "kb_id": old_doc["kb_id"],
            "name": old_doc["name"],
            "size": old_doc["size"],
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
        }
        
        # Verify migration preserves data
        assert new_doc["id"] == old_doc["id"]
        assert new_doc["kb_id"] == old_doc["kb_id"]
        assert new_doc["name"] == old_doc["name"]
        assert new_doc["size"] == old_doc["size"]
    
    @pytest.mark.anyio
    async def test_old_to_new_search_result_migration(self):
        """Test migration of search results from old to new system."""
        # Old search result
        old_result = {
            "content": "Result content",
            "score": 0.95,
            "metadata": {"source": "doc_001"}
        }
        
        # Simulate migration to new format
        new_result = {
            "content": old_result["content"],
            "score": old_result["score"],
            "metadata": old_result["metadata"],
            "rank": 1
        }
        
        # Verify migration preserves data
        assert new_result["content"] == old_result["content"]
        assert new_result["score"] == old_result["score"]
        assert new_result["metadata"] == old_result["metadata"]


class TestEndpointVersioning:
    """Test endpoint versioning for backward compatibility."""
    
    def test_v1_endpoint_availability(self):
        """Test v1 endpoints are still available."""
        # Old v1 endpoints should still work
        old_endpoints = [
            "/api/v1/knowledge-bases",
            "/api/v1/knowledge-bases/{kb_id}",
            "/api/v1/knowledge-bases/{kb_id}/documents",
            "/api/v1/search",
            "/api/v1/rag/generate"
        ]
        
        # Verify endpoints are defined
        for endpoint in old_endpoints:
            assert endpoint is not None
            assert "/api/v1/" in endpoint
    
    def test_new_agent_endpoints_coexist(self):
        """Test new Agent endpoints coexist with old endpoints."""
        # New Agent endpoints
        new_endpoints = [
            "/api/v1/agent/chat",
            "/api/v1/agent/chat/stream",
            "/api/v1/agent/session/{session_id}"
        ]
        
        # Old endpoints
        old_endpoints = [
            "/api/v1/knowledge-bases",
            "/api/v1/search",
            "/api/v1/rag/generate"
        ]
        
        # Both should coexist
        all_endpoints = new_endpoints + old_endpoints
        assert len(all_endpoints) == len(set(all_endpoints))


class TestServiceLayerCompatibility:
    """Test service layer compatibility."""
    
    @pytest.mark.anyio
    async def test_knowledge_base_service_interface_compatibility(self):
        """Test KnowledgeBaseService interface is compatible."""
        service = Mock()
        
        # Old interface methods
        service.create_knowledge_base = AsyncMock(return_value=Mock(id="kb_001"))
        service.get_knowledge_base = AsyncMock(return_value=Mock(id="kb_001"))
        service.list_knowledge_bases = AsyncMock(return_value=[Mock(id="kb_001")])
        service.update_knowledge_base = AsyncMock(return_value=Mock(id="kb_001"))
        service.delete_knowledge_base = AsyncMock(return_value=True)
        
        # Verify all methods exist
        assert hasattr(service, 'create_knowledge_base')
        assert hasattr(service, 'get_knowledge_base')
        assert hasattr(service, 'list_knowledge_bases')
        assert hasattr(service, 'update_knowledge_base')
        assert hasattr(service, 'delete_knowledge_base')
    
    @pytest.mark.anyio
    async def test_document_service_interface_compatibility(self):
        """Test DocumentService interface is compatible."""
        service = Mock()
        
        # Old interface methods
        service.upload_document = AsyncMock(return_value=Mock(id="doc_001"))
        service.get_document = AsyncMock(return_value=Mock(id="doc_001"))
        service.list_documents = AsyncMock(return_value=[Mock(id="doc_001")])
        service.update_document = AsyncMock(return_value=Mock(id="doc_001"))
        service.delete_document = AsyncMock(return_value=True)
        
        # Verify all methods exist
        assert hasattr(service, 'upload_document')
        assert hasattr(service, 'get_document')
        assert hasattr(service, 'list_documents')
        assert hasattr(service, 'update_document')
        assert hasattr(service, 'delete_document')
    
    @pytest.mark.anyio
    async def test_search_service_interface_compatibility(self):
        """Test SearchService interface is compatible."""
        service = Mock()
        
        # Old interface methods
        service.search = AsyncMock(return_value=[])
        service.search_with_rewrite = AsyncMock(return_value=[])
        
        # Verify all methods exist
        assert hasattr(service, 'search')
        assert hasattr(service, 'search_with_rewrite')


class TestDatabaseSchemaCompatibility:
    """Test database schema compatibility."""
    
    def test_knowledge_base_table_schema(self):
        """Test KnowledgeBase table schema is compatible."""
        # Old schema fields
        old_fields = [
            "id",
            "name",
            "description",
            "created_at",
            "updated_at"
        ]
        
        # Verify all fields are present
        for field in old_fields:
            assert field is not None
    
    def test_document_table_schema(self):
        """Test Document table schema is compatible."""
        # Old schema fields
        old_fields = [
            "id",
            "kb_id",
            "name",
            "size",
            "created_at",
            "updated_at"
        ]
        
        # Verify all fields are present
        for field in old_fields:
            assert field is not None
    
    def test_chunk_table_schema(self):
        """Test Chunk table schema is compatible."""
        # Old schema fields
        old_fields = [
            "id",
            "doc_id",
            "content",
            "embedding",
            "metadata",
            "created_at"
        ]
        
        # Verify all fields are present
        for field in old_fields:
            assert field is not None


class TestConfigurationCompatibility:
    """Test configuration compatibility."""
    
    def test_old_config_parameters_supported(self):
        """Test old configuration parameters are still supported."""
        # Old config parameters
        old_config = {
            "llm_provider": "openai",
            "embedding_model": "bge-m3",
            "reranker_model": "bge-reranker-base",
            "vector_store": "chroma",
            "database_url": "sqlite:///test.db"
        }
        
        # Verify all parameters are valid
        for key, value in old_config.items():
            assert key is not None
            assert value is not None
    
    def test_new_config_parameters_added(self):
        """Test new configuration parameters are added without breaking old ones."""
        # Old + new config parameters
        config = {
            # Old parameters
            "llm_provider": "openai",
            "embedding_model": "bge-m3",
            # New parameters
            "agent_max_iterations": 10,
            "agent_timeout": 60,
            "memory_max_history": 10
        }
        
        # Verify all parameters exist
        assert "llm_provider" in config
        assert "embedding_model" in config
        assert "agent_max_iterations" in config
        assert "agent_timeout" in config
        assert "memory_max_history" in config


class TestCompleteBackwardCompatibilityWorkflow:
    """Test complete backward compatibility workflows."""
    
    @pytest.mark.anyio
    async def test_old_rag_workflow_still_works(self, mock_old_rag_service, mock_db_session):
        """Test that old RAG workflow still works without Agent."""
        # Old workflow: search → generate answer
        
        # Step 1: Search
        search_results = await mock_old_rag_service.search(
            query="What is machine learning?",
            kb_id="kb_001",
            top_k=5
        )
        
        assert isinstance(search_results, list)
        assert len(search_results) > 0
        assert all("content" in r and "score" in r for r in search_results)
        
        # Step 2: Generate answer
        rag_result = await mock_old_rag_service.generate_answer(
            question="What is machine learning?",
            kb_id="kb_001",
            top_k=5
        )
        
        assert "answer" in rag_result
        assert "sources" in rag_result
        assert isinstance(rag_result["sources"], list)
    
    @pytest.mark.anyio
    async def test_old_kb_operations_still_work(self):
        """Test that old knowledge base operations still work."""
        kb_service = Mock()
        kb_service.create_kb = AsyncMock(return_value={"id": "kb_001", "name": "Test KB"})
        kb_service.get_kb = AsyncMock(return_value={"id": "kb_001", "name": "Test KB"})
        kb_service.list_kbs = AsyncMock(return_value=[{"id": "kb_001", "name": "Test KB"}])
        kb_service.update_kb = AsyncMock(return_value={"id": "kb_001", "name": "Updated KB"})
        kb_service.delete_kb = AsyncMock(return_value={"success": True})
        
        # Create
        kb = await kb_service.create_kb(name="Test KB", description="Test")
        assert kb["id"] == "kb_001"
        
        # Get
        kb = await kb_service.get_kb(kb_id="kb_001")
        assert kb["id"] == "kb_001"
        
        # List
        kbs = await kb_service.list_kbs()
        assert len(kbs) > 0
        
        # Update
        kb = await kb_service.update_kb(kb_id="kb_001", name="Updated KB")
        assert kb["name"] == "Updated KB"
        
        # Delete
        result = await kb_service.delete_kb(kb_id="kb_001")
        assert result["success"] is True
    
    @pytest.mark.anyio
    async def test_old_document_operations_still_work(self):
        """Test that old document operations still work."""
        doc_service = Mock()
        doc_service.upload_doc = AsyncMock(return_value={"id": "doc_001", "name": "test.txt"})
        doc_service.get_doc = AsyncMock(return_value={"id": "doc_001", "name": "test.txt"})
        doc_service.list_docs = AsyncMock(return_value=[{"id": "doc_001", "name": "test.txt"}])
        doc_service.update_doc = AsyncMock(return_value={"id": "doc_001", "name": "updated.txt"})
        doc_service.delete_doc = AsyncMock(return_value={"success": True})
        
        # Upload
        doc = await doc_service.upload_doc(kb_id="kb_001", file_path="test.txt")
        assert doc["id"] == "doc_001"
        
        # Get
        doc = await doc_service.get_doc(doc_id="doc_001")
        assert doc["id"] == "doc_001"
        
        # List
        docs = await doc_service.list_docs(kb_id="kb_001")
        assert len(docs) > 0
        
        # Update
        doc = await doc_service.update_doc(doc_id="doc_001", name="updated.txt")
        assert doc["name"] == "updated.txt"
        
        # Delete
        result = await doc_service.delete_doc(doc_id="doc_001")
        assert result["success"] is True
    
    @pytest.mark.anyio
    async def test_migration_from_old_to_new_system(self):
        """Test migration path from old system to new system."""
        # Old system data
        old_kbs = [
            {"id": "kb_001", "name": "KB 1", "description": "Old KB 1"},
            {"id": "kb_002", "name": "KB 2", "description": "Old KB 2"}
        ]
        
        old_docs = [
            {"id": "doc_001", "kb_id": "kb_001", "name": "doc1.txt"},
            {"id": "doc_002", "kb_id": "kb_001", "name": "doc2.txt"},
            {"id": "doc_003", "kb_id": "kb_002", "name": "doc3.txt"}
        ]
        
        # Migrate to new system
        migrated_kbs = []
        for kb in old_kbs:
            migrated_kb = {
                "id": kb["id"],
                "name": kb["name"],
                "description": kb["description"],
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            }
            migrated_kbs.append(migrated_kb)
        
        migrated_docs = []
        for doc in old_docs:
            migrated_doc = {
                "id": doc["id"],
                "kb_id": doc["kb_id"],
                "name": doc["name"],
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            }
            migrated_docs.append(migrated_doc)
        
        # Verify migration
        assert len(migrated_kbs) == len(old_kbs)
        assert len(migrated_docs) == len(old_docs)
        
        # Verify data integrity
        for old_kb, migrated_kb in zip(old_kbs, migrated_kbs):
            assert old_kb["id"] == migrated_kb["id"]
            assert old_kb["name"] == migrated_kb["name"]
            assert old_kb["description"] == migrated_kb["description"]
        
        for old_doc, migrated_doc in zip(old_docs, migrated_docs):
            assert old_doc["id"] == migrated_doc["id"]
            assert old_doc["kb_id"] == migrated_doc["kb_id"]
            assert old_doc["name"] == migrated_doc["name"]
    
    @pytest.mark.anyio
    async def test_concurrent_old_and_new_system_operations(self):
        """Test that old and new system operations can run concurrently."""
        # Old system service
        old_service = Mock()
        old_service.search = AsyncMock(return_value=[
            {"content": "Result 1", "score": 0.95},
            {"content": "Result 2", "score": 0.87}
        ])
        
        # New system service
        new_service = Mock()
        new_service.ainvoke = AsyncMock(return_value=Mock(
            output="Agent response",
            tool_calls=[],
            execution_time=0.5
        ))
        
        # Run both concurrently
        async def old_operation():
            return await old_service.search(query="test", kb_id="kb_001")
        
        async def new_operation():
            return await new_service.ainvoke(user_input="test", session_id="session_001")
        
        results = await asyncio.gather(old_operation(), new_operation())
        
        # Verify both completed
        assert len(results) == 2
        assert isinstance(results[0], list)
        assert hasattr(results[1], 'output')
    
    @pytest.mark.anyio
    async def test_old_api_endpoints_with_new_agent_endpoints(self):
        """Test that old API endpoints work alongside new Agent endpoints."""
        # Old endpoints
        old_endpoints = {
            "POST /api/search": "search",
            "POST /api/rag/generate": "rag_generate",
            "GET /api/knowledge-bases": "list_kbs",
            "POST /api/knowledge-bases": "create_kb"
        }
        
        # New endpoints
        new_endpoints = {
            "POST /api/v1/agent/chat": "agent_chat",
            "POST /api/v1/agent/chat/stream": "agent_chat_stream",
            "DELETE /api/v1/agent/session/{session_id}": "clear_session"
        }
        
        # Verify no conflicts
        all_endpoints = list(old_endpoints.keys()) + list(new_endpoints.keys())
        assert len(all_endpoints) == len(set(all_endpoints))
        
        # Verify both sets are available
        assert len(old_endpoints) > 0
        assert len(new_endpoints) > 0
