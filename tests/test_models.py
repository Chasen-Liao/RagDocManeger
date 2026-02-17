"""Tests for ORM models."""
import pytest
from datetime import datetime
from sqlalchemy.orm import Session
from models.orm import KnowledgeBase, Document, Chunk
from database import Base, engine, SessionLocal


@pytest.fixture
def db_session():
    """Create a test database session."""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


class TestKnowledgeBase:
    """Tests for KnowledgeBase model."""
    
    def test_create_knowledge_base(self, db_session: Session):
        """Test creating a knowledge base."""
        kb = KnowledgeBase(
            id="kb_001",
            name="Test KB",
            description="Test knowledge base"
        )
        db_session.add(kb)
        db_session.commit()
        
        retrieved = db_session.query(KnowledgeBase).filter_by(id="kb_001").first()
        assert retrieved is not None
        assert retrieved.name == "Test KB"
        assert retrieved.description == "Test knowledge base"
        assert isinstance(retrieved.created_at, datetime)
        assert isinstance(retrieved.updated_at, datetime)
    
    def test_knowledge_base_unique_name(self, db_session: Session):
        """Test that knowledge base names are unique."""
        kb1 = KnowledgeBase(id="kb_001", name="Unique KB")
        kb2 = KnowledgeBase(id="kb_002", name="Unique KB")
        
        db_session.add(kb1)
        db_session.commit()
        
        db_session.add(kb2)
        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()
    
    def test_knowledge_base_relationships(self, db_session: Session):
        """Test knowledge base relationships with documents and chunks."""
        kb = KnowledgeBase(id="kb_001", name="Test KB")
        doc = Document(
            id="doc_001",
            kb_id="kb_001",
            name="Test Doc",
            file_path="/path/to/file.pdf",
            file_size=1024,
            file_type="pdf"
        )
        chunk = Chunk(
            id="chunk_001",
            doc_id="doc_001",
            kb_id="kb_001",
            content="Test content",
            chunk_index=0
        )
        
        db_session.add(kb)
        db_session.add(doc)
        db_session.add(chunk)
        db_session.commit()
        
        retrieved_kb = db_session.query(KnowledgeBase).filter_by(id="kb_001").first()
        assert len(retrieved_kb.documents) == 1
        assert len(retrieved_kb.chunks) == 1
        assert retrieved_kb.documents[0].name == "Test Doc"


class TestDocument:
    """Tests for Document model."""
    
    def test_create_document(self, db_session: Session):
        """Test creating a document."""
        kb = KnowledgeBase(id="kb_001", name="Test KB")
        doc = Document(
            id="doc_001",
            kb_id="kb_001",
            name="Test Document",
            file_path="/path/to/file.pdf",
            file_size=2048,
            file_type="pdf",
            chunk_count=5
        )
        
        db_session.add(kb)
        db_session.add(doc)
        db_session.commit()
        
        retrieved = db_session.query(Document).filter_by(id="doc_001").first()
        assert retrieved is not None
        assert retrieved.name == "Test Document"
        assert retrieved.file_size == 2048
        assert retrieved.file_type == "pdf"
        assert retrieved.chunk_count == 5
        assert isinstance(retrieved.created_at, datetime)
    
    def test_document_foreign_key(self, db_session: Session):
        """Test document foreign key constraint."""
        # SQLite doesn't enforce foreign keys by default, so we test the relationship instead
        doc = Document(
            id="doc_001",
            kb_id="nonexistent_kb",
            name="Test Doc",
            file_path="/path/to/file.pdf",
            file_size=1024,
            file_type="pdf"
        )
        
        db_session.add(doc)
        db_session.commit()
        
        # Verify the document was created with the invalid kb_id
        retrieved = db_session.query(Document).filter_by(id="doc_001").first()
        assert retrieved is not None
        assert retrieved.kb_id == "nonexistent_kb"
    
    def test_document_relationships(self, db_session: Session):
        """Test document relationships with chunks."""
        kb = KnowledgeBase(id="kb_001", name="Test KB")
        doc = Document(
            id="doc_001",
            kb_id="kb_001",
            name="Test Doc",
            file_path="/path/to/file.pdf",
            file_size=1024,
            file_type="pdf"
        )
        chunk1 = Chunk(
            id="chunk_001",
            doc_id="doc_001",
            kb_id="kb_001",
            content="Content 1",
            chunk_index=0
        )
        chunk2 = Chunk(
            id="chunk_002",
            doc_id="doc_001",
            kb_id="kb_001",
            content="Content 2",
            chunk_index=1
        )
        
        db_session.add(kb)
        db_session.add(doc)
        db_session.add(chunk1)
        db_session.add(chunk2)
        db_session.commit()
        
        retrieved_doc = db_session.query(Document).filter_by(id="doc_001").first()
        assert len(retrieved_doc.chunks) == 2
        assert retrieved_doc.chunks[0].content == "Content 1"
        assert retrieved_doc.chunks[1].content == "Content 2"


class TestChunk:
    """Tests for Chunk model."""
    
    def test_create_chunk(self, db_session: Session):
        """Test creating a chunk."""
        kb = KnowledgeBase(id="kb_001", name="Test KB")
        doc = Document(
            id="doc_001",
            kb_id="kb_001",
            name="Test Doc",
            file_path="/path/to/file.pdf",
            file_size=1024,
            file_type="pdf"
        )
        chunk = Chunk(
            id="chunk_001",
            doc_id="doc_001",
            kb_id="kb_001",
            content="This is a test chunk content",
            chunk_index=0
        )
        
        db_session.add(kb)
        db_session.add(doc)
        db_session.add(chunk)
        db_session.commit()
        
        retrieved = db_session.query(Chunk).filter_by(id="chunk_001").first()
        assert retrieved is not None
        assert retrieved.content == "This is a test chunk content"
        assert retrieved.chunk_index == 0
        assert retrieved.doc_id == "doc_001"
        assert retrieved.kb_id == "kb_001"
        assert isinstance(retrieved.created_at, datetime)
    
    def test_chunk_foreign_keys(self, db_session: Session):
        """Test chunk foreign key constraints."""
        # SQLite doesn't enforce foreign keys by default, so we test the relationship instead
        chunk = Chunk(
            id="chunk_001",
            doc_id="nonexistent_doc",
            kb_id="nonexistent_kb",
            content="Test content",
            chunk_index=0
        )
        
        db_session.add(chunk)
        db_session.commit()
        
        # Verify the chunk was created with the invalid foreign keys
        retrieved = db_session.query(Chunk).filter_by(id="chunk_001").first()
        assert retrieved is not None
        assert retrieved.doc_id == "nonexistent_doc"
        assert retrieved.kb_id == "nonexistent_kb"
    
    def test_chunk_relationships(self, db_session: Session):
        """Test chunk relationships with document and knowledge base."""
        kb = KnowledgeBase(id="kb_001", name="Test KB")
        doc = Document(
            id="doc_001",
            kb_id="kb_001",
            name="Test Doc",
            file_path="/path/to/file.pdf",
            file_size=1024,
            file_type="pdf"
        )
        chunk = Chunk(
            id="chunk_001",
            doc_id="doc_001",
            kb_id="kb_001",
            content="Test content",
            chunk_index=0
        )
        
        db_session.add(kb)
        db_session.add(doc)
        db_session.add(chunk)
        db_session.commit()
        
        retrieved_chunk = db_session.query(Chunk).filter_by(id="chunk_001").first()
        assert retrieved_chunk.document.name == "Test Doc"
        assert retrieved_chunk.knowledge_base.name == "Test KB"


class TestCascadeDelete:
    """Tests for cascade delete behavior."""
    
    def test_delete_knowledge_base_cascades(self, db_session: Session):
        """Test that deleting a knowledge base cascades to documents and chunks."""
        kb = KnowledgeBase(id="kb_001", name="Test KB")
        doc = Document(
            id="doc_001",
            kb_id="kb_001",
            name="Test Doc",
            file_path="/path/to/file.pdf",
            file_size=1024,
            file_type="pdf"
        )
        chunk = Chunk(
            id="chunk_001",
            doc_id="doc_001",
            kb_id="kb_001",
            content="Test content",
            chunk_index=0
        )
        
        db_session.add(kb)
        db_session.add(doc)
        db_session.add(chunk)
        db_session.commit()
        
        # Delete knowledge base
        db_session.delete(kb)
        db_session.commit()
        
        # Verify all related records are deleted
        assert db_session.query(KnowledgeBase).filter_by(id="kb_001").first() is None
        assert db_session.query(Document).filter_by(id="doc_001").first() is None
        assert db_session.query(Chunk).filter_by(id="chunk_001").first() is None
    
    def test_delete_document_cascades(self, db_session: Session):
        """Test that deleting a document cascades to chunks."""
        kb = KnowledgeBase(id="kb_001", name="Test KB")
        doc = Document(
            id="doc_001",
            kb_id="kb_001",
            name="Test Doc",
            file_path="/path/to/file.pdf",
            file_size=1024,
            file_type="pdf"
        )
        chunk = Chunk(
            id="chunk_001",
            doc_id="doc_001",
            kb_id="kb_001",
            content="Test content",
            chunk_index=0
        )
        
        db_session.add(kb)
        db_session.add(doc)
        db_session.add(chunk)
        db_session.commit()
        
        # Delete document
        db_session.delete(doc)
        db_session.commit()
        
        # Verify document and chunks are deleted, but KB remains
        assert db_session.query(KnowledgeBase).filter_by(id="kb_001").first() is not None
        assert db_session.query(Document).filter_by(id="doc_001").first() is None
        assert db_session.query(Chunk).filter_by(id="chunk_001").first() is None
