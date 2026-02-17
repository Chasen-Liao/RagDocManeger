"""Property-based tests for ORM models - Property 8: Data Persistence Consistency."""
import pytest
from datetime import datetime
from hypothesis import given, strategies as st, HealthCheck, settings
from sqlalchemy.orm import Session
from models.orm import KnowledgeBase, Document, Chunk
from database import Base, engine, SessionLocal


def get_db_session():
    """Get a fresh database session."""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    return session


def cleanup_db():
    """Clean up database."""
    Base.metadata.drop_all(bind=engine)


# Strategies for generating test data
kb_id_strategy = st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=('Cc', 'Cs')))
kb_name_strategy = st.text(min_size=1, max_size=255, alphabet=st.characters(blacklist_categories=('Cc', 'Cs')))
kb_description_strategy = st.one_of(st.none(), st.text(max_size=1000, alphabet=st.characters(blacklist_categories=('Cc', 'Cs'))))
doc_id_strategy = st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=('Cc', 'Cs')))
doc_name_strategy = st.text(min_size=1, max_size=255, alphabet=st.characters(blacklist_categories=('Cc', 'Cs')))
file_path_strategy = st.text(min_size=1, max_size=500, alphabet=st.characters(blacklist_categories=('Cc', 'Cs')))
file_size_strategy = st.integers(min_value=1, max_value=1000000)
file_type_strategy = st.sampled_from(['pdf', 'docx', 'md', 'txt'])
chunk_id_strategy = st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=('Cc', 'Cs')))
chunk_content_strategy = st.text(min_size=1, max_size=10000, alphabet=st.characters(blacklist_categories=('Cc', 'Cs')))
chunk_index_strategy = st.integers(min_value=0, max_value=10000)


class TestDataPersistenceConsistency:
    """Tests for Property 8: Data Persistence Consistency.
    
    **Validates: Requirements 12.1, 12.2, 12.3, 12.4**
    
    Property: For any created knowledge base or uploaded document, the system should be able to
    recover all data after restart, and the data should be consistent with before restart.
    """
    
    @given(
        kb_id=kb_id_strategy,
        kb_name=kb_name_strategy,
        kb_description=kb_description_strategy
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
    def test_knowledge_base_persistence(self, kb_id, kb_name, kb_description):
        """Test that knowledge base data persists correctly.
        
        **Validates: Requirement 12.1**
        """
        db_session = get_db_session()
        try:
            # Create knowledge base
            kb = KnowledgeBase(
                id=kb_id,
                name=kb_name,
                description=kb_description
            )
            db_session.add(kb)
            db_session.commit()
            
            # Retrieve and verify
            retrieved = db_session.query(KnowledgeBase).filter_by(id=kb_id).first()
            assert retrieved is not None
            assert retrieved.id == kb_id
            assert retrieved.name == kb_name
            assert retrieved.description == kb_description
            assert isinstance(retrieved.created_at, datetime)
            assert isinstance(retrieved.updated_at, datetime)
        finally:
            db_session.close()
            cleanup_db()
    
    @given(
        kb_id=kb_id_strategy,
        kb_name=kb_name_strategy,
        doc_id=doc_id_strategy,
        doc_name=doc_name_strategy,
        file_path=file_path_strategy,
        file_size=file_size_strategy,
        file_type=file_type_strategy,
        chunk_count=st.integers(min_value=0, max_value=1000)
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
    def test_document_persistence(self, kb_id, kb_name, doc_id, doc_name, 
                                  file_path, file_size, file_type, chunk_count):
        """Test that document metadata persists correctly.
        
        **Validates: Requirement 12.2**
        """
        db_session = get_db_session()
        try:
            # Create knowledge base first
            kb = KnowledgeBase(id=kb_id, name=kb_name)
            db_session.add(kb)
            db_session.commit()
            
            # Create document
            doc = Document(
                id=doc_id,
                kb_id=kb_id,
                name=doc_name,
                file_path=file_path,
                file_size=file_size,
                file_type=file_type,
                chunk_count=chunk_count
            )
            db_session.add(doc)
            db_session.commit()
            
            # Retrieve and verify
            retrieved = db_session.query(Document).filter_by(id=doc_id).first()
            assert retrieved is not None
            assert retrieved.id == doc_id
            assert retrieved.kb_id == kb_id
            assert retrieved.name == doc_name
            assert retrieved.file_path == file_path
            assert retrieved.file_size == file_size
            assert retrieved.file_type == file_type
            assert retrieved.chunk_count == chunk_count
            assert isinstance(retrieved.created_at, datetime)
        finally:
            db_session.close()
            cleanup_db()
    
    @given(
        kb_id=kb_id_strategy,
        kb_name=kb_name_strategy,
        doc_id=doc_id_strategy,
        doc_name=doc_name_strategy,
        file_path=file_path_strategy,
        file_size=file_size_strategy,
        file_type=file_type_strategy,
        chunk_id=chunk_id_strategy,
        chunk_content=chunk_content_strategy,
        chunk_index=chunk_index_strategy
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
    def test_chunk_persistence(self, kb_id, kb_name, doc_id, doc_name,
                               file_path, file_size, file_type, chunk_id, chunk_content, chunk_index):
        """Test that chunk data persists correctly.
        
        **Validates: Requirement 12.3**
        """
        db_session = get_db_session()
        try:
            # Create knowledge base
            kb = KnowledgeBase(id=kb_id, name=kb_name)
            db_session.add(kb)
            db_session.commit()
            
            # Create document
            doc = Document(
                id=doc_id,
                kb_id=kb_id,
                name=doc_name,
                file_path=file_path,
                file_size=file_size,
                file_type=file_type
            )
            db_session.add(doc)
            db_session.commit()
            
            # Create chunk
            chunk = Chunk(
                id=chunk_id,
                doc_id=doc_id,
                kb_id=kb_id,
                content=chunk_content,
                chunk_index=chunk_index
            )
            db_session.add(chunk)
            db_session.commit()
            
            # Retrieve and verify
            retrieved = db_session.query(Chunk).filter_by(id=chunk_id).first()
            assert retrieved is not None
            assert retrieved.id == chunk_id
            assert retrieved.doc_id == doc_id
            assert retrieved.kb_id == kb_id
            assert retrieved.content == chunk_content
            assert retrieved.chunk_index == chunk_index
            assert isinstance(retrieved.created_at, datetime)
        finally:
            db_session.close()
            cleanup_db()
    
    @given(
        kb_id=kb_id_strategy,
        kb_name=kb_name_strategy,
        doc_ids=st.lists(doc_id_strategy, min_size=1, max_size=10, unique=True),
        doc_names=st.lists(doc_name_strategy, min_size=1, max_size=10)
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
    def test_multiple_documents_persistence(self, kb_id, kb_name, doc_ids, doc_names):
        """Test that multiple documents persist correctly.
        
        **Validates: Requirement 12.4**
        """
        db_session = get_db_session()
        try:
            # Create knowledge base
            kb = KnowledgeBase(id=kb_id, name=kb_name)
            db_session.add(kb)
            db_session.commit()
            
            # Create multiple documents
            num_docs = min(len(doc_ids), len(doc_names))
            for i in range(num_docs):
                doc = Document(
                    id=doc_ids[i],
                    kb_id=kb_id,
                    name=doc_names[i],
                    file_path=f"/path/to/file_{i}.pdf",
                    file_size=1024 * (i + 1),
                    file_type="pdf"
                )
                db_session.add(doc)
            db_session.commit()
            
            # Retrieve and verify all documents
            retrieved_docs = db_session.query(Document).filter_by(kb_id=kb_id).all()
            assert len(retrieved_docs) == num_docs
            
            # Verify each document
            for i in range(num_docs):
                doc = next((d for d in retrieved_docs if d.id == doc_ids[i]), None)
                assert doc is not None
                assert doc.name == doc_names[i]
                assert doc.kb_id == kb_id
        finally:
            db_session.close()
            cleanup_db()
    
    @given(
        kb_id=kb_id_strategy,
        kb_name=kb_name_strategy,
        doc_id=doc_id_strategy,
        doc_name=doc_name_strategy,
        file_path=file_path_strategy,
        file_size=file_size_strategy,
        file_type=file_type_strategy,
        chunk_ids=st.lists(chunk_id_strategy, min_size=1, max_size=20, unique=True),
        chunk_contents=st.lists(chunk_content_strategy, min_size=1, max_size=20)
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
    def test_multiple_chunks_persistence(self, kb_id, kb_name, doc_id, doc_name,
                                        file_path, file_size, file_type, chunk_ids, chunk_contents):
        """Test that multiple chunks persist correctly.
        
        **Validates: Requirement 12.4**
        """
        db_session = get_db_session()
        try:
            # Create knowledge base
            kb = KnowledgeBase(id=kb_id, name=kb_name)
            db_session.add(kb)
            db_session.commit()
            
            # Create document
            doc = Document(
                id=doc_id,
                kb_id=kb_id,
                name=doc_name,
                file_path=file_path,
                file_size=file_size,
                file_type=file_type
            )
            db_session.add(doc)
            db_session.commit()
            
            # Create multiple chunks
            num_chunks = min(len(chunk_ids), len(chunk_contents))
            for i in range(num_chunks):
                chunk = Chunk(
                    id=chunk_ids[i],
                    doc_id=doc_id,
                    kb_id=kb_id,
                    content=chunk_contents[i],
                    chunk_index=i
                )
                db_session.add(chunk)
            db_session.commit()
            
            # Retrieve and verify all chunks
            retrieved_chunks = db_session.query(Chunk).filter_by(doc_id=doc_id).all()
            assert len(retrieved_chunks) == num_chunks
            
            # Verify each chunk
            for i in range(num_chunks):
                chunk = next((c for c in retrieved_chunks if c.id == chunk_ids[i]), None)
                assert chunk is not None
                assert chunk.content == chunk_contents[i]
                assert chunk.chunk_index == i
                assert chunk.doc_id == doc_id
        finally:
            db_session.close()
            cleanup_db()
    
    @given(
        kb_id=kb_id_strategy,
        kb_name=kb_name_strategy,
        new_description=kb_description_strategy
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
    def test_knowledge_base_update_persistence(self, kb_id, kb_name, new_description):
        """Test that knowledge base updates persist correctly."""
        db_session = get_db_session()
        try:
            # Create knowledge base
            kb = KnowledgeBase(id=kb_id, name=kb_name, description="Original")
            db_session.add(kb)
            db_session.commit()
            
            # Update knowledge base
            kb.description = new_description
            db_session.commit()
            
            # Retrieve and verify
            retrieved = db_session.query(KnowledgeBase).filter_by(id=kb_id).first()
            assert retrieved is not None
            assert retrieved.description == new_description
        finally:
            db_session.close()
            cleanup_db()
