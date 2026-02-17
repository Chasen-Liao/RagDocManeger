"""Tests for VectorStore."""
import pytest
import shutil
import os
import uuid
from core.vector_store import VectorStore
from config import settings


@pytest.fixture
def vector_store():
    """Create a test vector store."""
    # Create a custom vector store for testing
    store = VectorStore()
    
    yield store


class TestVectorStore:
    """Tests for VectorStore."""
    
    def test_create_collection(self, vector_store: VectorStore):
        """Test creating a collection."""
        kb_id = f"kb_test_{uuid.uuid4().hex[:8]}"
        collection = vector_store.create_collection(kb_id, "Test KB")
        
        assert collection is not None
        assert kb_id in vector_store.collections
    
    def test_get_collection(self, vector_store: VectorStore):
        """Test getting a collection."""
        kb_id = f"kb_test_{uuid.uuid4().hex[:8]}"
        created = vector_store.create_collection(kb_id, "Test KB")
        
        retrieved = vector_store.get_collection(kb_id)
        assert retrieved is not None
    
    def test_get_nonexistent_collection(self, vector_store: VectorStore):
        """Test getting a non-existent collection."""
        retrieved = vector_store.get_collection("nonexistent_kb")
        assert retrieved is None
    
    def test_add_documents(self, vector_store: VectorStore):
        """Test adding documents to a collection."""
        kb_id = f"kb_test_{uuid.uuid4().hex[:8]}"
        vector_store.create_collection(kb_id, "Test KB")
        
        ids = ["doc_001", "doc_002"]
        documents = ["Document 1", "Document 2"]
        
        vector_store.add_documents(kb_id, ids, documents)
        
        # Verify documents were added
        count = vector_store.get_collection_count(kb_id)
        assert count == 2
    
    def test_add_documents_with_embeddings(self, vector_store: VectorStore):
        """Test adding documents with embeddings."""
        kb_id = f"kb_test_{uuid.uuid4().hex[:8]}"
        vector_store.create_collection(kb_id, "Test KB")
        
        ids = ["doc_001"]
        documents = ["Document 1"]
        embeddings = [[0.1, 0.2, 0.3, 0.4, 0.5]]
        
        vector_store.add_documents(kb_id, ids, documents, embeddings=embeddings)
        
        count = vector_store.get_collection_count(kb_id)
        assert count == 1
    
    def test_add_documents_with_metadata(self, vector_store: VectorStore):
        """Test adding documents with metadata."""
        kb_id = f"kb_test_{uuid.uuid4().hex[:8]}"
        vector_store.create_collection(kb_id, "Test KB")
        
        ids = ["doc_001"]
        documents = ["Document 1"]
        metadatas = [{"source": "test.pdf", "page": 1}]
        
        vector_store.add_documents(kb_id, ids, documents, metadatas=metadatas)
        
        count = vector_store.get_collection_count(kb_id)
        assert count == 1
    
    def test_query_documents(self, vector_store: VectorStore):
        """Test querying documents."""
        kb_id = f"kb_test_{uuid.uuid4().hex[:8]}"
        vector_store.create_collection(kb_id, "Test KB")
        
        # Add documents
        ids = ["doc_001", "doc_002", "doc_003"]
        documents = ["Python programming", "Java development", "JavaScript coding"]
        vector_store.add_documents(kb_id, ids, documents)
        
        # Query
        results = vector_store.query(kb_id, ["Python"], n_results=2)
        
        assert results is not None
        assert "ids" in results
        assert len(results["ids"]) > 0
    
    def test_delete_documents(self, vector_store: VectorStore):
        """Test deleting documents."""
        kb_id = f"kb_test_{uuid.uuid4().hex[:8]}"
        vector_store.create_collection(kb_id, "Test KB")
        
        # Add documents
        ids = ["doc_001", "doc_002"]
        documents = ["Document 1", "Document 2"]
        vector_store.add_documents(kb_id, ids, documents)
        
        # Delete one document
        vector_store.delete_documents(kb_id, ["doc_001"])
        
        # Verify
        count = vector_store.get_collection_count(kb_id)
        assert count == 1
    
    def test_delete_collection(self, vector_store: VectorStore):
        """Test deleting a collection."""
        kb_id = f"kb_test_{uuid.uuid4().hex[:8]}"
        vector_store.create_collection(kb_id, "Test KB")
        
        # Add documents
        ids = ["doc_001"]
        documents = ["Document 1"]
        vector_store.add_documents(kb_id, ids, documents)
        
        # Delete collection
        vector_store.delete_collection(kb_id)
        
        # Verify collection is deleted
        retrieved = vector_store.get_collection(kb_id)
        assert retrieved is None
    
    def test_get_collection_count(self, vector_store: VectorStore):
        """Test getting collection count."""
        kb_id = f"kb_test_{uuid.uuid4().hex[:8]}"
        vector_store.create_collection(kb_id, "Test KB")
        
        # Initially empty
        count = vector_store.get_collection_count(kb_id)
        assert count == 0
        
        # Add documents
        ids = ["doc_001", "doc_002", "doc_003"]
        documents = ["Document 1", "Document 2", "Document 3"]
        vector_store.add_documents(kb_id, ids, documents)
        
        # Verify count
        count = vector_store.get_collection_count(kb_id)
        assert count == 3
    
    def test_get_collection_count_nonexistent(self, vector_store: VectorStore):
        """Test getting count for non-existent collection."""
        count = vector_store.get_collection_count("nonexistent_kb")
        assert count == 0
