"""End-to-end integration tests for complete workflows."""
import pytest
import asyncio
from pathlib import Path
from fastapi.testclient import TestClient
from main import create_app
from database import init_db, get_db, SessionLocal
from models.orm import Base, KnowledgeBase, Document, Chunk
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import tempfile
import os


# Use in-memory SQLite for testing
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def test_db():
    """Create test database."""
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    yield TestingSessionLocal
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_db):
    """Create test client."""
    app = create_app()
    
    def override_get_db():
        db = test_db()
        try:
            yield db
        finally:
            db.close()
    
    # Override database dependency
    from database import get_db
    app.dependency_overrides[get_db] = override_get_db
    
    return TestClient(app)


@pytest.fixture
def sample_text_file():
    """Create a sample text file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("This is a sample document for testing.\n")
        f.write("It contains multiple paragraphs.\n")
        f.write("The system should be able to process this file.\n")
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)


class TestKnowledgeBaseWorkflow:
    """Test complete knowledge base workflow."""
    
    def test_create_knowledge_base(self, client):
        """Test creating a knowledge base."""
        response = client.post(
            "/api/knowledge-bases",
            json={
                "name": "Test KB",
                "description": "A test knowledge base"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "Test KB"
        assert data["data"]["description"] == "A test knowledge base"
        assert "id" in data["data"]
    
    def test_get_knowledge_bases(self, client):
        """Test getting list of knowledge bases."""
        # Create a knowledge base first
        create_response = client.post(
            "/api/knowledge-bases",
            json={"name": "Test KB 1", "description": "First KB"}
        )
        assert create_response.status_code == 201
        
        # Get list
        response = client.get("/api/knowledge-bases")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) >= 1
        assert data["meta"]["total"] >= 1
    
    def test_get_knowledge_base_details(self, client):
        """Test getting knowledge base details."""
        # Create a knowledge base
        create_response = client.post(
            "/api/knowledge-bases",
            json={"name": "Test KB", "description": "Test"}
        )
        kb_id = create_response.json()["data"]["id"]
        
        # Get details
        response = client.get(f"/api/knowledge-bases/{kb_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == kb_id
        assert data["data"]["name"] == "Test KB"
    
    def test_update_knowledge_base(self, client):
        """Test updating a knowledge base."""
        # Create a knowledge base
        create_response = client.post(
            "/api/knowledge-bases",
            json={"name": "Test KB", "description": "Original"}
        )
        kb_id = create_response.json()["data"]["id"]
        
        # Update
        response = client.put(
            f"/api/knowledge-bases/{kb_id}",
            json={"name": "Updated KB", "description": "Updated description"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "Updated KB"
        assert data["data"]["description"] == "Updated description"
    
    def test_delete_knowledge_base(self, client):
        """Test deleting a knowledge base."""
        # Create a knowledge base
        create_response = client.post(
            "/api/knowledge-bases",
            json={"name": "Test KB", "description": "To delete"}
        )
        kb_id = create_response.json()["data"]["id"]
        
        # Delete
        response = client.delete(f"/api/knowledge-bases/{kb_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # Verify it's deleted
        get_response = client.get(f"/api/knowledge-bases/{kb_id}")
        assert get_response.status_code == 404


class TestDocumentWorkflow:
    """Test complete document workflow."""
    
    def test_upload_document(self, client, sample_text_file):
        """Test uploading a document."""
        # Create knowledge base first
        kb_response = client.post(
            "/api/knowledge-bases",
            json={"name": "Test KB", "description": "For documents"}
        )
        kb_id = kb_response.json()["data"]["id"]
        
        # Upload document
        with open(sample_text_file, 'rb') as f:
            response = client.post(
                f"/api/knowledge-bases/{kb_id}/documents",
                files={"file": (Path(sample_text_file).name, f, "text/plain")}
            )
        
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "id" in data["data"]
        assert data["data"]["name"] == Path(sample_text_file).name
    
    def test_get_documents(self, client, sample_text_file):
        """Test getting list of documents."""
        # Create knowledge base
        kb_response = client.post(
            "/api/knowledge-bases",
            json={"name": "Test KB", "description": "For documents"}
        )
        kb_id = kb_response.json()["data"]["id"]
        
        # Upload document
        with open(sample_text_file, 'rb') as f:
            client.post(
                f"/api/knowledge-bases/{kb_id}/documents",
                files={"file": (Path(sample_text_file).name, f, "text/plain")}
            )
        
        # Get documents
        response = client.get(f"/api/knowledge-bases/{kb_id}/documents")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) >= 1
        assert data["meta"]["total"] >= 1
    
    def test_delete_document(self, client, sample_text_file):
        """Test deleting a document."""
        # Create knowledge base
        kb_response = client.post(
            "/api/knowledge-bases",
            json={"name": "Test KB", "description": "For documents"}
        )
        kb_id = kb_response.json()["data"]["id"]
        
        # Upload document
        with open(sample_text_file, 'rb') as f:
            upload_response = client.post(
                f"/api/knowledge-bases/{kb_id}/documents",
                files={"file": (Path(sample_text_file).name, f, "text/plain")}
            )
        doc_id = upload_response.json()["data"]["id"]
        
        # Delete document
        response = client.delete(f"/api/knowledge-bases/{kb_id}/documents/{doc_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestSearchWorkflow:
    """Test complete search workflow."""
    
    def test_search_basic(self, client):
        """Test basic search."""
        # Create knowledge base
        kb_response = client.post(
            "/api/knowledge-bases",
            json={"name": "Test KB", "description": "For search"}
        )
        kb_id = kb_response.json()["data"]["id"]
        
        # Perform search
        response = client.post(
            "/api/search",
            json={
                "kb_id": kb_id,
                "query": "test query",
                "top_k": 5
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
    
    def test_search_with_rewrite(self, client):
        """Test search with query rewriting."""
        # Create knowledge base
        kb_response = client.post(
            "/api/knowledge-bases",
            json={"name": "Test KB", "description": "For search"}
        )
        kb_id = kb_response.json()["data"]["id"]
        
        # Perform search with rewrite
        response = client.post(
            "/api/search/with-rewrite",
            json={
                "kb_id": kb_id,
                "query": "test query",
                "top_k": 5
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data


class TestConfigWorkflow:
    """Test configuration workflow."""
    
    def test_get_config(self, client):
        """Test getting configuration."""
        response = client.get("/api/config")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "app_name" in data["data"]
        assert "app_version" in data["data"]
    
    def test_update_config(self, client):
        """Test updating configuration."""
        response = client.put(
            "/api/config",
            json={
                "debug": False,
                "log_level": "INFO"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestErrorHandling:
    """Test error handling in workflows."""
    
    def test_knowledge_base_not_found(self, client):
        """Test accessing non-existent knowledge base."""
        response = client.get("/api/knowledge-bases/nonexistent")
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert "error" in data
    
    def test_duplicate_knowledge_base_name(self, client):
        """Test creating knowledge base with duplicate name."""
        # Create first KB
        client.post(
            "/api/knowledge-bases",
            json={"name": "Test KB", "description": "First"}
        )
        
        # Try to create with same name
        response = client.post(
            "/api/knowledge-bases",
            json={"name": "Test KB", "description": "Second"}
        )
        assert response.status_code == 409
        data = response.json()
        assert data["success"] is False
    
    def test_invalid_search_request(self, client):
        """Test search with invalid request."""
        response = client.post(
            "/api/search",
            json={
                "kb_id": "",  # Empty KB ID
                "query": "test"
            }
        )
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False


class TestAPIResponseFormat:
    """Test API response format consistency."""
    
    def test_success_response_format(self, client):
        """Test success response format."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "success" in data
        assert "data" in data
        assert data["success"] is True
    
    def test_error_response_format(self, client):
        """Test error response format."""
        response = client.get("/api/knowledge-bases/nonexistent")
        assert response.status_code == 404
        data = response.json()
        
        # Check required fields
        assert "success" in data
        assert "error" in data
        assert data["success"] is False
        assert "code" in data["error"]
        assert "message" in data["error"]
    
    def test_paginated_response_format(self, client):
        """Test paginated response format."""
        # Create a KB first
        client.post(
            "/api/knowledge-bases",
            json={"name": "Test KB", "description": "Test"}
        )
        
        response = client.get("/api/knowledge-bases")
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "success" in data
        assert "data" in data
        assert "meta" in data
        assert "total" in data["meta"]
        assert "skip" in data["meta"]
        assert "limit" in data["meta"]
