"""Document management service."""

import logging
import os
import uuid
from datetime import datetime
from typing import List, Optional
from pathlib import Path

from sqlalchemy.orm import Session
from models.orm import Document, Chunk, KnowledgeBase
from models.schemas import DocumentResponse, PaginatedResponse
from rag.document_processor import DocumentProcessor
from rag.chunking_strategy import ChunkingStrategy
from core.vector_store import VectorStore

logger = logging.getLogger(__name__)


class DocumentService:
    """Service for managing documents."""

    def __init__(
        self,
        db: Session,
        vector_store: VectorStore,
        embedding_provider=None,
        upload_dir: str = "uploads",
    ):
        """
        Initialize document service.

        Args:
            db: Database session
            vector_store: Vector store instance
            embedding_provider: Provider for generating embeddings
            upload_dir: Directory for storing uploaded files
        """
        self.db = db
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider
        self.upload_dir = upload_dir
        self.processor = DocumentProcessor()
        self.chunker = ChunkingStrategy()

        # Create upload directory if it doesn't exist
        Path(self.upload_dir).mkdir(parents=True, exist_ok=True)

    async def upload_document(
        self, kb_id: str, file_path: str, file_name: str
    ) -> DocumentResponse:
        """
        Upload and process a document.

        Args:
            kb_id: Knowledge base ID
            file_path: Path to the uploaded file
            file_name: Original file name

        Returns:
            DocumentResponse with document information

        Raises:
            ValueError: If knowledge base doesn't exist or file format is invalid
            Exception: If document processing fails
        """
        # Verify knowledge base exists
        kb = self.db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            raise ValueError(f"Knowledge base not found: {kb_id}")

        try:
            # Validate file
            self.processor.validate_file(file_path)

            # Get file size
            file_size = Path(file_path).stat().st_size

            # Create document record
            doc_id = str(uuid.uuid4())
            document = Document(
                id=doc_id,
                kb_id=kb_id,
                name=file_name,
                file_path=file_path,
                file_size=file_size,
                file_type=Path(file_name).suffix.lower(),
                chunk_count=0,
            )
            self.db.add(document)
            self.db.commit()

            # Process document
            content = self.processor.process_document(file_path)
            chunks = self.chunker.chunk_text(content)

            # Generate embeddings and store chunks
            chunk_ids = []
            for chunk_index, chunk_content in enumerate(chunks):
                chunk_id = str(uuid.uuid4())
                chunk_ids.append(chunk_id)

                # Create chunk record
                chunk = Chunk(
                    id=chunk_id,
                    doc_id=doc_id,
                    kb_id=kb_id,
                    content=chunk_content,
                    chunk_index=chunk_index,
                )
                self.db.add(chunk)

                # Generate embedding if provider is available
                if self.embedding_provider:
                    try:
                        embedding = await self.embedding_provider.embed_text(
                            chunk_content
                        )
                        # Store in vector store
                        await self.vector_store.add_vector(
                            kb_id=kb_id,
                            chunk_id=chunk_id,
                            content=chunk_content,
                            embedding=embedding,
                            metadata={
                                "doc_id": doc_id,
                                "doc_name": file_name,
                                "chunk_index": chunk_index,
                            },
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to generate embedding for chunk {chunk_id}: {e}"
                        )

            # Update chunk count
            document.chunk_count = len(chunks)
            self.db.commit()

            logger.info(
                f"Document {doc_id} uploaded and processed with {len(chunks)} chunks"
            )

            return DocumentResponse(
                id=doc_id,
                kb_id=kb_id,
                name=file_name,
                file_size=file_size,
                file_type=document.file_type,
                chunk_count=len(chunks),
                created_at=document.created_at,
            )

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error uploading document: {str(e)}")
            raise

    async def get_documents(
        self, kb_id: str, skip: int = 0, limit: int = 20
    ) -> PaginatedResponse:
        """
        Get documents in a knowledge base.

        Args:
            kb_id: Knowledge base ID
            skip: Number of documents to skip
            limit: Maximum number of documents to return

        Returns:
            PaginatedResponse with document list

        Raises:
            ValueError: If knowledge base doesn't exist
        """
        # Verify knowledge base exists
        kb = self.db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            raise ValueError(f"Knowledge base not found: {kb_id}")

        try:
            # Get total count
            total = (
                self.db.query(Document)
                .filter(Document.kb_id == kb_id)
                .count()
            )

            # Get documents
            documents = (
                self.db.query(Document)
                .filter(Document.kb_id == kb_id)
                .offset(skip)
                .limit(limit)
                .all()
            )

            # Convert to response objects
            doc_responses = [
                DocumentResponse(
                    id=doc.id,
                    kb_id=doc.kb_id,
                    name=doc.name,
                    file_size=doc.file_size,
                    file_type=doc.file_type,
                    chunk_count=doc.chunk_count,
                    created_at=doc.created_at,
                )
                for doc in documents
            ]

            return PaginatedResponse(
                items=doc_responses,
                meta={
                    "total": total,
                    "page": skip // limit + 1 if limit > 0 else 1,
                    "limit": limit,
                    "pages": (total + limit - 1) // limit if limit > 0 else 1,
                },
            )

        except Exception as e:
            logger.error(f"Error getting documents: {str(e)}")
            raise

    async def delete_document(self, kb_id: str, doc_id: str) -> None:
        """
        Delete a document.

        Args:
            kb_id: Knowledge base ID
            doc_id: Document ID

        Raises:
            ValueError: If document doesn't exist
            Exception: If deletion fails
        """
        try:
            # Verify document exists
            document = (
                self.db.query(Document)
                .filter(Document.id == doc_id, Document.kb_id == kb_id)
                .first()
            )
            if not document:
                raise ValueError(f"Document not found: {doc_id}")

            # Get all chunks for this document
            chunks = self.db.query(Chunk).filter(Chunk.doc_id == doc_id).all()

            # Delete from vector store
            for chunk in chunks:
                try:
                    await self.vector_store.delete_vector(
                        kb_id=kb_id, chunk_id=chunk.id
                    )
                except Exception as e:
                    logger.warning(f"Failed to delete vector for chunk {chunk.id}: {e}")

            # Delete chunks from database
            self.db.query(Chunk).filter(Chunk.doc_id == doc_id).delete()

            # Delete document from database
            self.db.delete(document)
            self.db.commit()

            # Delete file if it exists
            if document.file_path and os.path.exists(document.file_path):
                try:
                    os.remove(document.file_path)
                except Exception as e:
                    logger.warning(f"Failed to delete file {document.file_path}: {e}")

            logger.info(f"Document {doc_id} deleted")

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting document: {str(e)}")
            raise

    async def get_document(self, kb_id: str, doc_id: str) -> DocumentResponse:
        """
        Get a specific document.

        Args:
            kb_id: Knowledge base ID
            doc_id: Document ID

        Returns:
            DocumentResponse

        Raises:
            ValueError: If document doesn't exist
        """
        try:
            document = (
                self.db.query(Document)
                .filter(Document.id == doc_id, Document.kb_id == kb_id)
                .first()
            )
            if not document:
                raise ValueError(f"Document not found: {doc_id}")

            return DocumentResponse(
                id=document.id,
                kb_id=document.kb_id,
                name=document.name,
                file_size=document.file_size,
                file_type=document.file_type,
                chunk_count=document.chunk_count,
                created_at=document.created_at,
            )

        except Exception as e:
            logger.error(f"Error getting document: {str(e)}")
            raise
