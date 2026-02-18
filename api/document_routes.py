"""Document API routes."""
from fastapi import APIRouter, HTTPException, status, Query, UploadFile, File, Depends
from typing import Optional
from sqlalchemy.orm import Session
from models.schemas import DocumentResponse
from services.document_service import DocumentService
from services.knowledge_base_service import KnowledgeBaseService
from exceptions import NotFoundError, ValidationError
from logger import logger
from database import get_db
from core.vector_store import get_vector_store
from core.embedding_provider import EmbeddingProviderFactory
from config import settings

router = APIRouter(prefix="/knowledge-bases", tags=["documents"])


@router.post("/{kb_id}/documents/upload", response_model=dict, status_code=status.HTTP_201_CREATED)
async def upload_document(kb_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload a document to a knowledge base.
    
    Uploads a document file to a knowledge base. The system automatically:
    1. Validates the file format (PDF, Word, Markdown)
    2. Parses the document content
    3. Splits the content into semantic chunks
    4. Generates vector embeddings for each chunk
    5. Stores chunks in both the vector database and relational database
    
    **Supported Formats**:
    - PDF (.pdf)
    - Word (.docx, .doc)
    - Markdown (.md)
    
    **Request Example**:
    ```
    POST /knowledge-bases/kb_123456/documents/upload
    Content-Type: multipart/form-data
    
    file: <binary file content>
    ```
    
    **Response Example**:
    ```json
    {
      "success": true,
      "data": {
        "id": "doc_789012",
        "kb_id": "kb_123456",
        "name": "产品手册.pdf",
        "file_size": 2048000,
        "file_type": "pdf",
        "chunk_count": 45,
        "created_at": "2024-01-15T10:30:00"
      },
      "message": "Document uploaded successfully"
    }
    ```
    
    **Error Cases**:
    - 404 Not Found: 知识库不存在
    - 400 Bad Request: 不支持的文件格式或文件过大
    - 500 Internal Server Error: 文档处理失败
    
    Args:
        kb_id: Knowledge base ID
        file: Document file to upload
        db: Database session
        
    Returns:
        Uploaded document information
    """
    try:
        logger.info(f"Uploading document to knowledge base: {kb_id}, filename: {file.filename}")
        
        # Verify knowledge base exists
        kb_service = KnowledgeBaseService()
        await kb_service.get_knowledge_base(db, kb_id=kb_id)
        
        # Save uploaded file temporarily
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        try:
            # Upload document
            vector_store = get_vector_store()

            # Create embedding provider if API key is configured
            embedding_provider = None
            if settings.embedding_api_key:
                try:
                    embedding_provider = EmbeddingProviderFactory.create_provider(
                        provider_type=settings.embedding_provider or "siliconflow",
                        api_key=settings.embedding_api_key,
                        model=settings.embedding_model or "BAAI/bge-small-zh-v1.5"
                    )
                except Exception as e:
                    logger.warning(f"Failed to create embedding provider: {e}")

            doc_service = DocumentService(db, vector_store, embedding_provider)
            doc = await doc_service.upload_document(kb_id=kb_id, file_path=tmp_file_path, file_name=file.filename)
            
            return {
                "success": True,
                "data": doc,
                "message": "Document uploaded successfully"
            }
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_file_path):
                os.remove(tmp_file_path)
    except NotFoundError as e:
        logger.warning(f"Knowledge base not found: {kb_id}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except ValidationError as e:
        logger.warning(f"Validation error uploading document: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload document"
        )


@router.get("/{kb_id}/documents", response_model=dict)
async def get_documents(
    kb_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get list of documents in a knowledge base.
    
    Retrieves a paginated list of all documents in a specific knowledge base.
    
    **Path Parameters**:
    - `kb_id`: 知识库 ID
    
    **Query Parameters**:
    - `skip`: 跳过的记录数（默认 0）
    - `limit`: 返回的最大记录数（默认 20，最大 100）
    
    **Request Example**:
    ```
    GET /knowledge-bases/kb_123456/documents?skip=0&limit=20
    ```
    
    **Response Example**:
    ```json
    {
      "success": true,
      "data": [
        {
          "id": "doc_789012",
          "kb_id": "kb_123456",
          "name": "产品手册.pdf",
          "file_size": 2048000,
          "file_type": "pdf",
          "chunk_count": 45,
          "created_at": "2024-01-15T10:30:00"
        }
      ],
      "meta": {
        "total": 5,
        "skip": 0,
        "limit": 20,
        "page": 1,
        "pages": 1
      },
      "message": null
    }
    ```
    
    **Error Cases**:
    - 404 Not Found: 知识库不存在
    
    Args:
        kb_id: Knowledge base ID
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
        
    Returns:
        Paginated list of documents
    """
    try:
        logger.info(f"Fetching documents for knowledge base: {kb_id}, skip={skip}, limit={limit}")
        
        # Verify knowledge base exists
        kb_service = KnowledgeBaseService()
        await kb_service.get_knowledge_base(db, kb_id=kb_id)
        
        # Get documents
        vector_store = get_vector_store()
        doc_service = DocumentService(db, vector_store)
        paginated_response = await doc_service.get_documents(kb_id=kb_id, skip=skip, limit=limit)
        
        return {
            "success": True,
            "data": paginated_response.items,
            "meta": paginated_response.meta,
            "message": None
        }
    except NotFoundError as e:
        logger.warning(f"Knowledge base not found: {kb_id}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error fetching documents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch documents"
        )


@router.delete("/{kb_id}/documents/{doc_id}", response_model=dict, status_code=status.HTTP_200_OK)
async def delete_document(kb_id: str, doc_id: str, db: Session = Depends(get_db)):
    """Delete a document from a knowledge base.
    
    Deletes a document and all its associated chunks from both the vector database
    and the relational database. This operation is irreversible.
    
    **Path Parameters**:
    - `kb_id`: 知识库 ID
    - `doc_id`: 文档 ID
    
    **Request Example**:
    ```
    DELETE /knowledge-bases/kb_123456/documents/doc_789012
    ```
    
    **Response Example**:
    ```json
    {
      "success": true,
      "data": null,
      "message": "Document deleted successfully"
    }
    ```
    
    **Error Cases**:
    - 404 Not Found: 知识库或文档不存在
    
    Args:
        kb_id: Knowledge base ID
        doc_id: Document ID
        db: Database session
        
    Returns:
        Success message
    """
    try:
        logger.info(f"Deleting document: {doc_id} from knowledge base: {kb_id}")
        
        # Verify knowledge base exists
        kb_service = KnowledgeBaseService()
        await kb_service.get_knowledge_base(db, kb_id=kb_id)
        
        # Delete document
        vector_store = get_vector_store()
        doc_service = DocumentService(db, vector_store)
        await doc_service.delete_document(kb_id=kb_id, doc_id=doc_id)
        
        return {
            "success": True,
            "data": None,
            "message": "Document deleted successfully"
        }
    except NotFoundError as e:
        logger.warning(f"Resource not found: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document"
        )
