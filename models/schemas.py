"""Pydantic schemas for API requests and responses."""
from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


# Knowledge Base Schemas
class KnowledgeBaseCreate(BaseModel):
    """Schema for creating a knowledge base."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)


class KnowledgeBaseUpdate(BaseModel):
    """Schema for updating a knowledge base."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)


class KnowledgeBaseResponse(BaseModel):
    """Schema for knowledge base response."""
    id: str
    name: str
    description: Optional[str]
    document_count: int
    total_size: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Document Schemas
class DocumentResponse(BaseModel):
    """Schema for document response."""
    id: str
    kb_id: str
    name: str
    file_size: int
    file_type: str
    chunk_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# Chunk Schemas
class ChunkResponse(BaseModel):
    """Schema for chunk response."""
    id: str
    doc_id: str
    kb_id: str
    content: str
    chunk_index: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# Retrieval Schemas
class SearchRequest(BaseModel):
    """Schema for search request."""
    kb_id: str = Field(..., min_length=1)
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: Optional[int] = Field(5, ge=1, le=100)


class RetrievalResult(BaseModel):
    """Schema for retrieval result."""
    chunk_id: str
    doc_id: str
    doc_name: str
    content: str
    score: float


class SearchResponse(BaseModel):
    """Schema for search response."""
    query: str
    results: List[RetrievalResult]
    total_count: int


# Intent Recognition Schemas
class IntentResult(BaseModel):
    """Schema for intent recognition result."""
    intent: str  # query, manage, update, delete
    entities: Dict[str, Any]
    confidence: float


class QueryRewriteResult(BaseModel):
    """Schema for query rewrite result."""
    original_query: str
    rewritten_queries: List[str]
    method: str  # hyde, expansion, etc.


# Pagination Schemas
class PaginationMeta(BaseModel):
    """Schema for pagination metadata."""
    total: int
    page: int
    limit: int
    pages: int


class PaginatedResponse(BaseModel):
    """Generic paginated response schema."""
    items: List[Any]
    meta: PaginationMeta


# API Response Schemas
class APIResponse(BaseModel):
    """Standard API response schema."""
    success: bool
    data: Optional[Any] = None
    error: Optional[Dict[str, str]] = None
    message: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


class ErrorDetail(BaseModel):
    """Error detail schema."""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
