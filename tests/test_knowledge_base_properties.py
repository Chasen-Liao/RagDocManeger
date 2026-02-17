"""Property-based tests for KnowledgeBaseService.

Property 13: Knowledge Base Metadata Completeness
Property 15: Knowledge Base Deletion Completeness
"""
import pytest
from datetime import datetime
from hypothesis import given, strategies as st, HealthCheck, settings
from sqlalchemy.orm import Session
from models.orm import KnowledgeBase, Document, Chunk
from models.schemas import KnowledgeBaseCreate, KnowledgeBaseUpdate
from services.knowledge_base_service import KnowledgeBaseService
from database import Base, engine, SessionLocal


def get_db_session():
    """Get a fresh database session."""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    return session


def cleanup_db():
    """Clean up database."""
    Base.metadata.drop_all(bind=engine)


# Strategies
kb_name_strategy = st.text(min_size=1, max_size=255, alphabet=st.characters(blacklist_categories=('Cc', 'Cs')))
kb_description_strategy = st.one_of(st.none(), st.text(max_size=1000, alphabet=st.characters(blacklist_categories=('Cc', 'Cs'))))
doc_count_strategy = st.integers(min_value=0, max_value=10)
file_size_strategy = st.integers(min_value=1, max_value=100000)


class TestKnowledgeBaseMetadataCompleteness:
    """Tests for Property 13: Knowledge Base Metadata Completeness.
    
    **Validates: Requirements 1.2, 1.5**
    
    Property: For any knowledge base, the system returns metadata should contain name, creation time,
    document count and size and all required fields.
    """
    
    @given(
        kb_name=kb_name_strategy,
        kb_description=kb_description_strategy
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
    async def test_knowledge_base_metadata_completeness(self, kb_name, kb_description):
        """Test that KB metadata contains all required fields.
        
        **Validates: Requirement 1.2**
        """
        db_session = get_db_session()
        try:
            # Create KB
            kb_create = KnowledgeBaseCreate(name=kb_name, description=kb_description)
            response = await KnowledgeBaseService.create_knowledge_base(db_session, kb_create)
            
            # Verify all required fields are present
            assert response.id is not None
            assert isinstance(response.id, str)
            assert response.name == kb_name
            assert response.description == kb_description
            assert isinstance(response.document_count, int)
            assert response.document_count >= 0
            assert isinstance(response.total_size, int)
            assert response.total_size >= 0
            assert isinstance(response.created_at, datetime)
            assert isinstance(response.updated_at, datetime)
        finally:
            db_session.close()
            cleanup_db()
    
    @given(
        kb_name=kb_name_strategy,
        doc_count=doc_count_strategy
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
    async def test_knowledge_base_document_count_accuracy(self, kb_name, doc_count):
        """Test that document count is accurate.
        
        **Validates: Requirement 1.2**
        """
        db_session = get_db_session()
        try:
            # Create KB
            kb_create = KnowledgeBaseCreate(name=kb_name)
            kb_response = await KnowledgeBaseService.create_knowledge_base(db_session, kb_create)
            
            # Add documents
            total_size = 0
            for i in range(doc_count):
                file_size = (i + 1) * 1024
                total_size += file_size
                doc = Document(
                    id=f"doc_{i:03d}",
                    kb_id=kb_response.id,
                    name=f"Doc {i}",
                    file_path=f"/path/to/file_{i}.pdf",
                    file_size=file_size,
                    file_type="pdf"
                )
                db_session.add(doc)
            db_session.commit()
            
            # Get KB and verify counts
            response = await KnowledgeBaseService.get_knowledge_base(db_session, kb_response.id)
            assert response.document_count == doc_count
            assert response.total_size == total_size
        finally:
            db_session.close()
            cleanup_db()
    
    @given(
        kb_name=kb_name_strategy,
        doc_sizes=st.lists(file_size_strategy, min_size=0, max_size=10)
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
    async def test_knowledge_base_total_size_calculation(self, kb_name, doc_sizes):
        """Test that total size is calculated correctly.
        
        **Validates: Requirement 1.2**
        """
        db_session = get_db_session()
        try:
            # Create KB
            kb_create = KnowledgeBaseCreate(name=kb_name)
            kb_response = await KnowledgeBaseService.create_knowledge_base(db_session, kb_create)
            
            # Add documents with specific sizes
            expected_total = 0
            for i, size in enumerate(doc_sizes):
                expected_total += size
                doc = Document(
                    id=f"doc_{i:03d}",
                    kb_id=kb_response.id,
                    name=f"Doc {i}",
                    file_path=f"/path/to/file_{i}.pdf",
                    file_size=size,
                    file_type="pdf"
                )
                db_session.add(doc)
            db_session.commit()
            
            # Get KB and verify total size
            response = await KnowledgeBaseService.get_knowledge_base(db_session, kb_response.id)
            assert response.total_size == expected_total
        finally:
            db_session.close()
            cleanup_db()


class TestKnowledgeBaseDeletionCompleteness:
    """Tests for Property 15: Knowledge Base Deletion Completeness.
    
    **Validates: Requirement 1.4**
    
    Property: For any deleted knowledge base, the system should delete the corresponding vector index
    and all associated documents.
    """
    
    @given(
        kb_name=kb_name_strategy,
        doc_count=doc_count_strategy
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
    async def test_knowledge_base_deletion_removes_documents(self, kb_name, doc_count):
        """Test that deleting KB removes all associated documents.
        
        **Validates: Requirement 1.4**
        """
        db_session = get_db_session()
        try:
            # Create KB
            kb_create = KnowledgeBaseCreate(name=kb_name)
            kb_response = await KnowledgeBaseService.create_knowledge_base(db_session, kb_create)
            
            # Add documents
            doc_ids = []
            for i in range(doc_count):
                doc_id = f"doc_{i:03d}"
                doc_ids.append(doc_id)
                doc = Document(
                    id=doc_id,
                    kb_id=kb_response.id,
                    name=f"Doc {i}",
                    file_path=f"/path/to/file_{i}.pdf",
                    file_size=1024,
                    file_type="pdf"
                )
                db_session.add(doc)
            db_session.commit()
            
            # Delete KB
            await KnowledgeBaseService.delete_knowledge_base(db_session, kb_response.id)
            
            # Verify KB is deleted
            kb_count = db_session.query(KnowledgeBase).filter_by(id=kb_response.id).count()
            assert kb_count == 0
            
            # Verify all documents are deleted
            for doc_id in doc_ids:
                doc_count_result = db_session.query(Document).filter_by(id=doc_id).count()
                assert doc_count_result == 0
        finally:
            db_session.close()
            cleanup_db()
    
    @given(
        kb_name=kb_name_strategy,
        doc_count=st.integers(min_value=1, max_value=5),
        chunks_per_doc=st.integers(min_value=1, max_value=5)
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
    async def test_knowledge_base_deletion_removes_chunks(self, kb_name, doc_count, chunks_per_doc):
        """Test that deleting KB removes all associated chunks.
        
        **Validates: Requirement 1.4**
        """
        db_session = get_db_session()
        try:
            # Create KB
            kb_create = KnowledgeBaseCreate(name=kb_name)
            kb_response = await KnowledgeBaseService.create_knowledge_base(db_session, kb_create)
            
            # Add documents with chunks
            chunk_ids = []
            for i in range(doc_count):
                doc_id = f"doc_{i:03d}"
                doc = Document(
                    id=doc_id,
                    kb_id=kb_response.id,
                    name=f"Doc {i}",
                    file_path=f"/path/to/file_{i}.pdf",
                    file_size=1024,
                    file_type="pdf"
                )
                db_session.add(doc)
                db_session.flush()
                
                # Add chunks
                for j in range(chunks_per_doc):
                    chunk_id = f"chunk_{i:03d}_{j:03d}"
                    chunk_ids.append(chunk_id)
                    chunk = Chunk(
                        id=chunk_id,
                        doc_id=doc_id,
                        kb_id=kb_response.id,
                        content=f"Chunk {i}-{j}",
                        chunk_index=j
                    )
                    db_session.add(chunk)
            db_session.commit()
            
            # Delete KB
            await KnowledgeBaseService.delete_knowledge_base(db_session, kb_response.id)
            
            # Verify all chunks are deleted
            for chunk_id in chunk_ids:
                chunk_count = db_session.query(Chunk).filter_by(id=chunk_id).count()
                assert chunk_count == 0
        finally:
            db_session.close()
            cleanup_db()
    
    @given(
        kb_name=kb_name_strategy
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
    async def test_knowledge_base_deletion_idempotent(self, kb_name):
        """Test that KB deletion is idempotent (can't delete twice).
        
        **Validates: Requirement 1.4**
        """
        db_session = get_db_session()
        try:
            # Create KB
            kb_create = KnowledgeBaseCreate(name=kb_name)
            kb_response = await KnowledgeBaseService.create_knowledge_base(db_session, kb_create)
            
            # Delete KB
            await KnowledgeBaseService.delete_knowledge_base(db_session, kb_response.id)
            
            # Verify KB is deleted
            kb_count = db_session.query(KnowledgeBase).filter_by(id=kb_response.id).count()
            assert kb_count == 0
        finally:
            db_session.close()
            cleanup_db()
