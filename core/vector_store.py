"""Vector store integration with ChromaDB."""
import os
from typing import List, Optional, Dict, Any
import chromadb
from config import settings
from logger import logger


class VectorStore:
    """Vector store wrapper for ChromaDB."""
    
    def __init__(self):
        """Initialize ChromaDB client."""
        self.client = None
        self.collections: Dict[str, Any] = {}
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize ChromaDB client."""
        try:
            # Create vector store directory if it doesn't exist
            os.makedirs(settings.vector_store_path, exist_ok=True)
            
            # Initialize ChromaDB client with new API
            self.client = chromadb.PersistentClient(path=settings.vector_store_path)
            logger.info(f"ChromaDB client initialized with path: {settings.vector_store_path}")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB client: {str(e)}")
            raise
    
    def create_collection(self, kb_id: str, name: str) -> Any:
        """Create a new collection for a knowledge base.
        
        Args:
            kb_id: Knowledge base ID
            name: Collection name
            
        Returns:
            ChromaDB collection object
        """
        try:
            # Use kb_id as collection name to ensure uniqueness
            collection_name = f"kb_{kb_id}"
            
            # Create collection with metadata
            collection = self.client.create_collection(
                name=collection_name,
                metadata={"kb_id": kb_id, "kb_name": name}
            )
            
            self.collections[kb_id] = collection
            logger.info(f"Collection created: {collection_name}")
            
            return collection
        except Exception as e:
            logger.error(f"Failed to create collection for KB {kb_id}: {str(e)}")
            raise
    
    def get_collection(self, kb_id: str) -> Optional[Any]:
        """Get a collection by knowledge base ID.
        
        Args:
            kb_id: Knowledge base ID
            
        Returns:
            ChromaDB collection object or None if not found
        """
        try:
            if kb_id in self.collections:
                return self.collections[kb_id]
            
            # Try to get existing collection
            collection_name = f"kb_{kb_id}"
            collection = self.client.get_collection(name=collection_name)
            self.collections[kb_id] = collection
            
            return collection
        except Exception as e:
            logger.debug(f"Collection not found for KB {kb_id}: {str(e)}")
            return None
    
    def delete_collection(self, kb_id: str) -> None:
        """Delete a collection.
        
        Args:
            kb_id: Knowledge base ID
        """
        try:
            collection_name = f"kb_{kb_id}"
            self.client.delete_collection(name=collection_name)
            
            if kb_id in self.collections:
                del self.collections[kb_id]
            
            logger.info(f"Collection deleted: {collection_name}")
        except Exception as e:
            logger.error(f"Failed to delete collection for KB {kb_id}: {str(e)}")
            raise
    
    def add_documents(
        self,
        kb_id: str,
        ids: List[str],
        documents: List[str],
        embeddings: Optional[List[List[float]]] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """Add documents to a collection.
        
        Args:
            kb_id: Knowledge base ID
            ids: Document IDs
            documents: Document texts
            embeddings: Optional pre-computed embeddings
            metadatas: Optional metadata for each document
        """
        try:
            collection = self.get_collection(kb_id)
            if not collection:
                raise ValueError(f"Collection not found for KB {kb_id}")
            
            # Add documents to collection
            collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas
            )
            
            logger.info(f"Added {len(ids)} documents to collection for KB {kb_id}")
        except Exception as e:
            logger.error(f"Failed to add documents to KB {kb_id}: {str(e)}")
            raise
    
    def query(
        self,
        kb_id: str,
        query_texts: List[str],
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Query documents from a collection.
        
        Args:
            kb_id: Knowledge base ID
            query_texts: Query texts
            n_results: Number of results to return
            where: Optional filter conditions
            
        Returns:
            Query results with ids, documents, distances, and metadatas
        """
        try:
            collection = self.get_collection(kb_id)
            if not collection:
                raise ValueError(f"Collection not found for KB {kb_id}")
            
            # Query collection
            results = collection.query(
                query_texts=query_texts,
                n_results=n_results,
                where=where
            )
            
            logger.debug(f"Queried collection for KB {kb_id}: {len(results['ids'][0])} results")
            
            return results
        except Exception as e:
            logger.error(f"Failed to query collection for KB {kb_id}: {str(e)}")
            raise
    
    def delete_documents(self, kb_id: str, ids: List[str]) -> None:
        """Delete documents from a collection.
        
        Args:
            kb_id: Knowledge base ID
            ids: Document IDs to delete
        """
        try:
            collection = self.get_collection(kb_id)
            if not collection:
                raise ValueError(f"Collection not found for KB {kb_id}")
            
            # Delete documents
            collection.delete(ids=ids)
            
            logger.info(f"Deleted {len(ids)} documents from collection for KB {kb_id}")
        except Exception as e:
            logger.error(f"Failed to delete documents from KB {kb_id}: {str(e)}")
            raise
    
    def get_collection_count(self, kb_id: str) -> int:
        """Get the number of documents in a collection.
        
        Args:
            kb_id: Knowledge base ID
            
        Returns:
            Number of documents in the collection
        """
        try:
            collection = self.get_collection(kb_id)
            if not collection:
                return 0
            
            return collection.count()
        except Exception as e:
            logger.error(f"Failed to get collection count for KB {kb_id}: {str(e)}")
            return 0


# Global vector store instance
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Get or create the global vector store instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
