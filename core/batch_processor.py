"""Batch processing utilities for documents and vectors."""
import asyncio
from typing import List, Optional, Any, Callable
from logger import logger


class BatchProcessor:
    """Utility for batch processing with configurable batch size."""
    
    def __init__(self, batch_size: int = 32):
        """
        Initialize batch processor.
        
        Args:
            batch_size: Number of items to process in each batch
        """
        self.batch_size = batch_size
    
    async def process_batch(
        self,
        items: List[Any],
        process_func: Callable,
        *args,
        **kwargs
    ) -> List[Any]:
        """
        Process items in batches.
        
        Args:
            items: List of items to process
            process_func: Async function to process each item
            *args: Additional positional arguments for process_func
            **kwargs: Additional keyword arguments for process_func
            
        Returns:
            List of processed results
        """
        results = []
        total_batches = (len(items) + self.batch_size - 1) // self.batch_size
        
        logger.info(f"Processing {len(items)} items in {total_batches} batches")
        
        for batch_idx in range(0, len(items), self.batch_size):
            batch = items[batch_idx:batch_idx + self.batch_size]
            batch_num = batch_idx // self.batch_size + 1
            
            logger.debug(f"Processing batch {batch_num}/{total_batches}")
            
            try:
                # Process batch items concurrently
                batch_results = await asyncio.gather(
                    *[process_func(item, *args, **kwargs) for item in batch],
                    return_exceptions=True
                )
                
                # Handle exceptions in batch results
                for i, result in enumerate(batch_results):
                    if isinstance(result, Exception):
                        logger.warning(
                            f"Error processing item {batch_idx + i}: {str(result)}"
                        )
                    else:
                        results.append(result)
                        
            except Exception as e:
                logger.error(f"Error processing batch {batch_num}: {str(e)}")
                raise
        
        logger.info(f"Batch processing completed: {len(results)} items processed")
        return results
    
    async def process_batch_with_callback(
        self,
        items: List[Any],
        process_func: Callable,
        callback_func: Optional[Callable] = None,
        *args,
        **kwargs
    ) -> List[Any]:
        """
        Process items in batches with callback after each batch.
        
        Args:
            items: List of items to process
            process_func: Async function to process each item
            callback_func: Optional callback function called after each batch
            *args: Additional positional arguments for process_func
            **kwargs: Additional keyword arguments for process_func
            
        Returns:
            List of processed results
        """
        results = []
        total_batches = (len(items) + self.batch_size - 1) // self.batch_size
        
        logger.info(f"Processing {len(items)} items in {total_batches} batches with callback")
        
        for batch_idx in range(0, len(items), self.batch_size):
            batch = items[batch_idx:batch_idx + self.batch_size]
            batch_num = batch_idx // self.batch_size + 1
            
            logger.debug(f"Processing batch {batch_num}/{total_batches}")
            
            try:
                # Process batch items concurrently
                batch_results = await asyncio.gather(
                    *[process_func(item, *args, **kwargs) for item in batch],
                    return_exceptions=True
                )
                
                # Handle exceptions in batch results
                for i, result in enumerate(batch_results):
                    if isinstance(result, Exception):
                        logger.warning(
                            f"Error processing item {batch_idx + i}: {str(result)}"
                        )
                    else:
                        results.append(result)
                
                # Call callback after batch processing
                if callback_func:
                    try:
                        await callback_func(batch_num, total_batches, len(results))
                    except Exception as e:
                        logger.warning(f"Error in callback: {str(e)}")
                        
            except Exception as e:
                logger.error(f"Error processing batch {batch_num}: {str(e)}")
                raise
        
        logger.info(f"Batch processing completed: {len(results)} items processed")
        return results


class VectorBatchProcessor:
    """Specialized batch processor for vector operations."""
    
    def __init__(self, batch_size: int = 32):
        """
        Initialize vector batch processor.
        
        Args:
            batch_size: Number of vectors to process in each batch
        """
        self.batch_size = batch_size
        self.batch_processor = BatchProcessor(batch_size)
    
    async def batch_embed_texts(
        self,
        texts: List[str],
        embedding_provider
    ) -> List[List[float]]:
        """
        Generate embeddings for texts in batches.
        
        Args:
            texts: List of texts to embed
            embedding_provider: Provider for generating embeddings
            
        Returns:
            List of embeddings
        """
        logger.info(f"Batch embedding {len(texts)} texts")
        
        embeddings = []
        total_batches = (len(texts) + self.batch_size - 1) // self.batch_size
        
        for batch_idx in range(0, len(texts), self.batch_size):
            batch = texts[batch_idx:batch_idx + self.batch_size]
            batch_num = batch_idx // self.batch_size + 1
            
            logger.debug(f"Embedding batch {batch_num}/{total_batches}")
            
            try:
                # Use batch embedding if available
                if hasattr(embedding_provider, 'embed_texts'):
                    batch_embeddings = await embedding_provider.embed_texts(batch)
                else:
                    # Fall back to individual embedding
                    batch_embeddings = await asyncio.gather(
                        *[embedding_provider.embed_text(text) for text in batch],
                        return_exceptions=True
                    )
                
                embeddings.extend(batch_embeddings)
                
            except Exception as e:
                logger.error(f"Error embedding batch {batch_num}: {str(e)}")
                raise
        
        logger.info(f"Batch embedding completed: {len(embeddings)} embeddings generated")
        return embeddings
    
    async def batch_add_vectors(
        self,
        kb_id: str,
        chunk_ids: List[str],
        contents: List[str],
        embeddings: List[List[float]],
        vector_store,
        metadata_list: Optional[List[dict]] = None
    ) -> None:
        """
        Add vectors to vector store in batches.
        
        Args:
            kb_id: Knowledge base ID
            chunk_ids: List of chunk IDs
            contents: List of chunk contents
            embeddings: List of embeddings
            vector_store: Vector store instance
            metadata_list: Optional list of metadata dicts
        """
        logger.info(f"Batch adding {len(chunk_ids)} vectors to vector store")
        
        if len(chunk_ids) != len(contents) or len(chunk_ids) != len(embeddings):
            raise ValueError("Mismatched lengths of chunk_ids, contents, and embeddings")
        
        total_batches = (len(chunk_ids) + self.batch_size - 1) // self.batch_size
        
        for batch_idx in range(0, len(chunk_ids), self.batch_size):
            batch_num = batch_idx // self.batch_size + 1
            
            logger.debug(f"Adding batch {batch_num}/{total_batches} to vector store")
            
            try:
                batch_chunk_ids = chunk_ids[batch_idx:batch_idx + self.batch_size]
                batch_contents = contents[batch_idx:batch_idx + self.batch_size]
                batch_embeddings = embeddings[batch_idx:batch_idx + self.batch_size]
                batch_metadata = (
                    metadata_list[batch_idx:batch_idx + self.batch_size]
                    if metadata_list
                    else [None] * len(batch_chunk_ids)
                )
                
                # Add batch to vector store
                await asyncio.gather(
                    *[
                        vector_store.add_vector(
                            kb_id=kb_id,
                            chunk_id=chunk_id,
                            content=content,
                            embedding=embedding,
                            metadata=metadata
                        )
                        for chunk_id, content, embedding, metadata in zip(
                            batch_chunk_ids,
                            batch_contents,
                            batch_embeddings,
                            batch_metadata
                        )
                    ],
                    return_exceptions=True
                )
                
            except Exception as e:
                logger.error(f"Error adding batch {batch_num} to vector store: {str(e)}")
                raise
        
        logger.info(f"Batch adding vectors completed: {len(chunk_ids)} vectors added")
    
    async def batch_delete_vectors(
        self,
        kb_id: str,
        chunk_ids: List[str],
        vector_store
    ) -> None:
        """
        Delete vectors from vector store in batches.
        
        Args:
            kb_id: Knowledge base ID
            chunk_ids: List of chunk IDs to delete
            vector_store: Vector store instance
        """
        logger.info(f"Batch deleting {len(chunk_ids)} vectors from vector store")
        
        total_batches = (len(chunk_ids) + self.batch_size - 1) // self.batch_size
        
        for batch_idx in range(0, len(chunk_ids), self.batch_size):
            batch_num = batch_idx // self.batch_size + 1
            
            logger.debug(f"Deleting batch {batch_num}/{total_batches} from vector store")
            
            try:
                batch_chunk_ids = chunk_ids[batch_idx:batch_idx + self.batch_size]
                
                # Delete batch from vector store
                await asyncio.gather(
                    *[
                        vector_store.delete_vector(kb_id=kb_id, chunk_id=chunk_id)
                        for chunk_id in batch_chunk_ids
                    ],
                    return_exceptions=True
                )
                
            except Exception as e:
                logger.error(f"Error deleting batch {batch_num} from vector store: {str(e)}")
                raise
        
        logger.info(f"Batch deleting vectors completed: {len(chunk_ids)} vectors deleted")
