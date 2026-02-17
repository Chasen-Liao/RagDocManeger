"""FAISS-based vector retrieval optimization."""
import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from logger import logger

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning("FAISS not available, vector optimization disabled")


class FAISSIndexManager:
    """Manager for FAISS vector indices."""
    
    def __init__(self, dimension: int = 768):
        """
        Initialize FAISS index manager.
        
        Args:
            dimension: Dimension of vectors
        """
        if not FAISS_AVAILABLE:
            raise RuntimeError("FAISS is not installed")
        
        self.dimension = dimension
        self.indices: Dict[str, Any] = {}
        self.id_maps: Dict[str, Dict[int, str]] = {}
        self.vector_stores: Dict[str, List[np.ndarray]] = {}
    
    def create_index(self, kb_id: str, index_type: str = "flat") -> None:
        """
        Create a FAISS index for a knowledge base.
        
        Args:
            kb_id: Knowledge base ID
            index_type: Type of index ("flat", "ivf", "hnsw")
        """
        logger.info(f"Creating FAISS index for KB {kb_id} (type: {index_type})")
        
        try:
            if index_type == "flat":
                # Simple flat index for small datasets
                index = faiss.IndexFlatL2(self.dimension)
            elif index_type == "ivf":
                # Inverted file index for medium datasets
                quantizer = faiss.IndexFlatL2(self.dimension)
                index = faiss.IndexIVFFlat(quantizer, self.dimension, 100)
                index.train(np.random.random((1000, self.dimension)).astype('float32'))
            elif index_type == "hnsw":
                # HNSW index for large datasets
                index = faiss.IndexHNSWFlat(self.dimension, 32)
            else:
                raise ValueError(f"Unknown index type: {index_type}")
            
            self.indices[kb_id] = index
            self.id_maps[kb_id] = {}
            self.vector_stores[kb_id] = []
            
            logger.info(f"FAISS index created for KB {kb_id}")
            
        except Exception as e:
            logger.error(f"Error creating FAISS index: {str(e)}")
            raise
    
    def add_vectors(
        self,
        kb_id: str,
        chunk_ids: List[str],
        vectors: List[List[float]]
    ) -> None:
        """
        Add vectors to FAISS index.
        
        Args:
            kb_id: Knowledge base ID
            chunk_ids: List of chunk IDs
            vectors: List of vectors (embeddings)
        """
        if kb_id not in self.indices:
            raise ValueError(f"Index not found for KB {kb_id}")
        
        try:
            # Convert to numpy array
            vectors_array = np.array(vectors, dtype='float32')
            
            # Add to FAISS index
            index = self.indices[kb_id]
            start_id = index.ntotal
            index.add(vectors_array)
            
            # Map internal IDs to chunk IDs
            id_map = self.id_maps[kb_id]
            for i, chunk_id in enumerate(chunk_ids):
                id_map[start_id + i] = chunk_id
            
            # Store vectors for reference
            self.vector_stores[kb_id].extend(vectors)
            
            logger.debug(f"Added {len(chunk_ids)} vectors to FAISS index for KB {kb_id}")
            
        except Exception as e:
            logger.error(f"Error adding vectors to FAISS index: {str(e)}")
            raise
    
    def search(
        self,
        kb_id: str,
        query_vector: List[float],
        top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """
        Search for similar vectors in FAISS index.
        
        Args:
            kb_id: Knowledge base ID
            query_vector: Query vector (embedding)
            top_k: Number of top results to return
            
        Returns:
            List of (chunk_id, distance) tuples
        """
        if kb_id not in self.indices:
            raise ValueError(f"Index not found for KB {kb_id}")
        
        try:
            # Convert query to numpy array
            query_array = np.array([query_vector], dtype='float32')
            
            # Search in FAISS index
            index = self.indices[kb_id]
            distances, indices = index.search(query_array, min(top_k, index.ntotal))
            
            # Map internal IDs back to chunk IDs
            id_map = self.id_maps[kb_id]
            results = []
            
            for i, idx in enumerate(indices[0]):
                if idx >= 0 and idx in id_map:
                    chunk_id = id_map[idx]
                    distance = float(distances[0][i])
                    # Convert L2 distance to similarity score (0-1)
                    similarity = 1.0 / (1.0 + distance)
                    results.append((chunk_id, similarity))
            
            logger.debug(f"FAISS search returned {len(results)} results for KB {kb_id}")
            return results
            
        except Exception as e:
            logger.error(f"Error searching FAISS index: {str(e)}")
            raise
    
    def delete_vectors(
        self,
        kb_id: str,
        chunk_ids: List[str]
    ) -> None:
        """
        Delete vectors from FAISS index.
        
        Note: FAISS doesn't support efficient deletion, so we rebuild the index.
        
        Args:
            kb_id: Knowledge base ID
            chunk_ids: List of chunk IDs to delete
        """
        if kb_id not in self.indices:
            raise ValueError(f"Index not found for KB {kb_id}")
        
        try:
            id_map = self.id_maps[kb_id]
            chunk_id_set = set(chunk_ids)
            
            # Find indices to keep
            indices_to_keep = [
                idx for idx, chunk_id in id_map.items()
                if chunk_id not in chunk_id_set
            ]
            
            if not indices_to_keep:
                # Rebuild empty index
                self.create_index(kb_id)
                logger.debug(f"Deleted all vectors from FAISS index for KB {kb_id}")
                return
            
            # Rebuild index with remaining vectors
            vectors_to_keep = [
                self.vector_stores[kb_id][idx]
                for idx in sorted(indices_to_keep)
            ]
            
            # Create new index
            self.create_index(kb_id)
            
            # Get chunk IDs for remaining vectors
            old_id_map = id_map
            chunk_ids_to_keep = [
                old_id_map[idx]
                for idx in sorted(indices_to_keep)
            ]
            
            # Add vectors back
            self.add_vectors(kb_id, chunk_ids_to_keep, vectors_to_keep)
            
            logger.debug(f"Deleted {len(chunk_ids)} vectors from FAISS index for KB {kb_id}")
            
        except Exception as e:
            logger.error(f"Error deleting vectors from FAISS index: {str(e)}")
            raise
    
    def get_index_stats(self, kb_id: str) -> Dict[str, Any]:
        """
        Get statistics for a FAISS index.
        
        Args:
            kb_id: Knowledge base ID
            
        Returns:
            Dictionary with index statistics
        """
        if kb_id not in self.indices:
            return {"error": f"Index not found for KB {kb_id}"}
        
        index = self.indices[kb_id]
        return {
            "kb_id": kb_id,
            "vector_count": index.ntotal,
            "dimension": self.dimension,
            "index_type": type(index).__name__
        }
    
    def delete_index(self, kb_id: str) -> None:
        """
        Delete a FAISS index.
        
        Args:
            kb_id: Knowledge base ID
        """
        if kb_id in self.indices:
            del self.indices[kb_id]
            del self.id_maps[kb_id]
            del self.vector_stores[kb_id]
            logger.info(f"FAISS index deleted for KB {kb_id}")


class OptimizedVectorRetriever:
    """Vector retriever optimized with FAISS."""
    
    def __init__(self, embedding_dimension: int = 768, use_faiss: bool = True):
        """
        Initialize optimized vector retriever.
        
        Args:
            embedding_dimension: Dimension of embeddings
            use_faiss: Whether to use FAISS optimization
        """
        self.embedding_dimension = embedding_dimension
        self.use_faiss = use_faiss and FAISS_AVAILABLE
        
        if self.use_faiss:
            self.faiss_manager = FAISSIndexManager(embedding_dimension)
            logger.info("FAISS-based vector retriever initialized")
        else:
            logger.info("Standard vector retriever initialized (FAISS not available)")
    
    async def retrieve(
        self,
        kb_id: str,
        query_vector: List[float],
        top_k: int = 10,
        vector_store=None
    ) -> List[Tuple[str, float]]:
        """
        Retrieve similar vectors.
        
        Args:
            kb_id: Knowledge base ID
            query_vector: Query vector (embedding)
            top_k: Number of top results
            vector_store: Fallback vector store if FAISS not available
            
        Returns:
            List of (chunk_id, similarity_score) tuples
        """
        if self.use_faiss:
            try:
                return self.faiss_manager.search(kb_id, query_vector, top_k)
            except Exception as e:
                logger.warning(f"FAISS search failed, falling back to vector store: {str(e)}")
        
        # Fallback to vector store
        if vector_store:
            return await vector_store.search(kb_id, query_vector, top_k)
        
        raise RuntimeError("No vector retrieval method available")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get retriever statistics."""
        if self.use_faiss:
            return {
                "retriever_type": "FAISS-optimized",
                "faiss_available": True
            }
        else:
            return {
                "retriever_type": "Standard",
                "faiss_available": False
            }
