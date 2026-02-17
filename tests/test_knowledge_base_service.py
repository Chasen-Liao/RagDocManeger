"""Tests for KnowledgeBaseService."""
import pytest
from sqlalchemy.orm import Session
from models.orm import KnowledgeBase, Document
from models.schemas import KnowledgeBaseCreate, KnowledgeBaseUpdate
from services.knowledge_base_service import KnowledgeBaseService
from exceptions import ResourceNotFoundError, ConflictError
from database import Base, engine, SessionLocal


@pytest.fixture
def db_session():
    """Create a test database session."""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


class TestKnowledgeBaseService:
    """Tests for KnowledgeBaseService."""
    
    @pytest.mark.asyncio
    async def test_create_knowledge_base(self, db_session: Session):
        """Test creating a knowledge base."""
        kb_create = KnowledgeBaseCreate(
            name="Test KB",
            description="Test knowledge base"
        )
        
        response = await KnowledgeBaseService.create_knowledge_base(db_session, kb_create)
        
        assert response.id is not None
        assert response.name == "Test KB"
        assert response.description == "Test knowledge base"
        assert response.document_count == 0
        assert response.total_size == 0
        assert response.created_at is not None
        assert response.updated_at is not None
    
    @pytest.mark.asyncio
    async def test_create_knowledge_base_duplicate_name(self, db_session: Session):
        """Test creating a knowledge base with duplicate name."""
        kb_create = KnowledgeBaseCreate(name="Duplicate KB")
        
        # Create first KB
        await KnowledgeBaseService.create_knowledge_base(db_session, kb_create)
        
        # Try to create second KB with same name
        with pytest.raises(ConflictError):
            await KnowledgeBaseService.create_knowledge_base(db_session, kb_create)
    
    @pytest.mark.asyncio
    async def test_get_knowledge_bases(self, db_session: Session):
        """Test getting list of knowledge bases."""
        # Create multiple KBs
        for i in range(3):
            kb_create = KnowledgeBaseCreate(name=f"KB {i}")
            await KnowledgeBaseService.create_knowledge_base(db_session, kb_create)
        
        # Get list
        responses, total = await KnowledgeBaseService.get_knowledge_bases(db_session, skip=0, limit=20)
        
        assert len(responses) == 3
        assert total == 3
    
    @pytest.mark.asyncio
    async def test_get_knowledge_bases_pagination(self, db_session: Session):
        """Test pagination of knowledge bases."""
        # Create 5 KBs
        for i in range(5):
            kb_create = KnowledgeBaseCreate(name=f"KB {i}")
            await KnowledgeBaseService.create_knowledge_base(db_session, kb_create)
        
        # Get first page
        responses1, total1 = await KnowledgeBaseService.get_knowledge_bases(db_session, skip=0, limit=2)
        assert len(responses1) == 2
        assert total1 == 5
        
        # Get second page
        responses2, total2 = await KnowledgeBaseService.get_knowledge_bases(db_session, skip=2, limit=2)
        assert len(responses2) == 2
        assert total2 == 5
    
    @pytest.mark.asyncio
    async def test_get_knowledge_base(self, db_session: Session):
        """Test getting a specific knowledge base."""
        kb_create = KnowledgeBaseCreate(name="Test KB")
        created = await KnowledgeBaseService.create_knowledge_base(db_session, kb_create)
        
        response = await KnowledgeBaseService.get_knowledge_base(db_session, created.id)
        
        assert response.id == created.id
        assert response.name == "Test KB"
    
    @pytest.mark.asyncio
    async def test_get_knowledge_base_not_found(self, db_session: Session):
        """Test getting a non-existent knowledge base."""
        with pytest.raises(ResourceNotFoundError):
            await KnowledgeBaseService.get_knowledge_base(db_session, "nonexistent_id")
    
    @pytest.mark.asyncio
    async def test_update_knowledge_base(self, db_session: Session):
        """Test updating a knowledge base."""
        kb_create = KnowledgeBaseCreate(name="Original KB", description="Original")
        created = await KnowledgeBaseService.create_knowledge_base(db_session, kb_create)
        
        kb_update = KnowledgeBaseUpdate(name="Updated KB", description="Updated")
        response = await KnowledgeBaseService.update_knowledge_base(db_session, created.id, kb_update)
        
        assert response.name == "Updated KB"
        assert response.description == "Updated"
    
    @pytest.mark.asyncio
    async def test_update_knowledge_base_not_found(self, db_session: Session):
        """Test updating a non-existent knowledge base."""
        kb_update = KnowledgeBaseUpdate(name="Updated KB")
        
        with pytest.raises(ResourceNotFoundError):
            await KnowledgeBaseService.update_knowledge_base(db_session, "nonexistent_id", kb_update)
    
    @pytest.mark.asyncio
    async def test_update_knowledge_base_duplicate_name(self, db_session: Session):
        """Test updating a knowledge base with duplicate name."""
        # Create two KBs
        kb1 = await KnowledgeBaseService.create_knowledge_base(
            db_session, KnowledgeBaseCreate(name="KB 1")
        )
        kb2 = await KnowledgeBaseService.create_knowledge_base(
            db_session, KnowledgeBaseCreate(name="KB 2")
        )
        
        # Try to update KB2 with KB1's name
        kb_update = KnowledgeBaseUpdate(name="KB 1")
        with pytest.raises(ConflictError):
            await KnowledgeBaseService.update_knowledge_base(db_session, kb2.id, kb_update)
    
    @pytest.mark.asyncio
    async def test_delete_knowledge_base(self, db_session: Session):
        """Test deleting a knowledge base."""
        kb_create = KnowledgeBaseCreate(name="Test KB")
        created = await KnowledgeBaseService.create_knowledge_base(db_session, kb_create)
        
        await KnowledgeBaseService.delete_knowledge_base(db_session, created.id)
        
        # Verify it's deleted
        with pytest.raises(ResourceNotFoundError):
            await KnowledgeBaseService.get_knowledge_base(db_session, created.id)
    
    @pytest.mark.asyncio
    async def test_delete_knowledge_base_not_found(self, db_session: Session):
        """Test deleting a non-existent knowledge base."""
        with pytest.raises(ResourceNotFoundError):
            await KnowledgeBaseService.delete_knowledge_base(db_session, "nonexistent_id")
    
    @pytest.mark.asyncio
    async def test_delete_knowledge_base_cascades(self, db_session: Session):
        """Test that deleting a KB cascades to documents."""
        # Create KB
        kb = await KnowledgeBaseService.create_knowledge_base(
            db_session, KnowledgeBaseCreate(name="Test KB")
        )
        
        # Add document
        doc = Document(
            id="doc_001",
            kb_id=kb.id,
            name="Test Doc",
            file_path="/path/to/file.pdf",
            file_size=1024,
            file_type="pdf"
        )
        db_session.add(doc)
        db_session.commit()
        
        # Delete KB
        await KnowledgeBaseService.delete_knowledge_base(db_session, kb.id)
        
        # Verify document is also deleted
        assert db_session.query(Document).filter_by(id="doc_001").first() is None
    
    @pytest.mark.asyncio
    async def test_knowledge_base_document_count(self, db_session: Session):
        """Test that document count is calculated correctly."""
        # Create KB
        kb = await KnowledgeBaseService.create_knowledge_base(
            db_session, KnowledgeBaseCreate(name="Test KB")
        )
        
        # Add documents
        for i in range(3):
            doc = Document(
                id=f"doc_{i:03d}",
                kb_id=kb.id,
                name=f"Doc {i}",
                file_path=f"/path/to/file_{i}.pdf",
                file_size=1024 * (i + 1),
                file_type="pdf"
            )
            db_session.add(doc)
        db_session.commit()
        
        # Get KB and verify count
        response = await KnowledgeBaseService.get_knowledge_base(db_session, kb.id)
        assert response.document_count == 3
        assert response.total_size == 1024 + 2048 + 3072
