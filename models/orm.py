"""ORM models for RagDocMan database."""
from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship, Mapped, mapped_column
from database import Base


class KnowledgeBase(Base):
    """Knowledge Base ORM model."""
    
    __tablename__ = "knowledge_bases"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    documents: Mapped[List["Document"]] = relationship("Document", back_populates="knowledge_base", cascade="all, delete-orphan")
    chunks: Mapped[List["Chunk"]] = relationship("Chunk", back_populates="knowledge_base", cascade="all, delete-orphan")


class Document(Base):
    """Document ORM model."""
    
    __tablename__ = "documents"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    kb_id: Mapped[str] = mapped_column(String, ForeignKey("knowledge_bases.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_type: Mapped[str] = mapped_column(String, nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    knowledge_base: Mapped["KnowledgeBase"] = relationship("KnowledgeBase", back_populates="documents")
    chunks: Mapped[List["Chunk"]] = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")


class Chunk(Base):
    """Chunk ORM model."""
    
    __tablename__ = "chunks"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    doc_id: Mapped[str] = mapped_column(String, ForeignKey("documents.id"), nullable=False, index=True)
    kb_id: Mapped[str] = mapped_column(String, ForeignKey("knowledge_bases.id"), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="chunks")
    knowledge_base: Mapped["KnowledgeBase"] = relationship("KnowledgeBase", back_populates="chunks")
