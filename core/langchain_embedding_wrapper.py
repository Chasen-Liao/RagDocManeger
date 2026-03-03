"""LangChain 1.x Embeddings wrapper for Embedding Provider."""

import logging
from typing import List
from langchain_core.embeddings import Embeddings
from .embedding_provider import EmbeddingProvider

logger = logging.getLogger(__name__)


class LangChainEmbeddingWrapper(Embeddings):
    """
    LangChain 1.x compatible wrapper for Embedding Provider.
    
    This wrapper adapts our custom Embedding Provider to the LangChain 1.x Embeddings interface,
    supporting both document and query embedding with batch processing.
    
    Attributes:
        embedding_provider: The underlying embedding provider instance
        model_name: Name of the model for identification
        batch_size: Maximum batch size for processing multiple documents
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        model_name: str = "custom",
        batch_size: int = 32
    ):
        """
        Initialize LangChain Embeddings wrapper.

        Args:
            embedding_provider: Our custom embedding provider instance
            model_name: Name of the model for identification
            batch_size: Maximum batch size for processing multiple documents
        """
        self.embedding_provider = embedding_provider
        self.model_name = model_name
        self.batch_size = batch_size

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of documents synchronously.
        
        This method processes documents in batches for efficiency.

        Args:
            texts: List of document texts to embed

        Returns:
            List of embedding vectors, one per document
            
        Raises:
            ValueError: If texts list is empty
            Exception: If embedding generation fails
        """
        import asyncio

        if not texts:
            raise ValueError("Texts list cannot be empty")

        try:
            # Get or create event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    raise RuntimeError("Event loop is closed")
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Process in batches
            all_embeddings = []
            for i in range(0, len(texts), self.batch_size):
                batch = texts[i:i + self.batch_size]
                batch_embeddings = loop.run_until_complete(
                    self.embedding_provider.embed_texts(batch)
                )
                all_embeddings.extend(batch_embeddings)
            
            logger.debug(f"Embedded {len(texts)} documents in {(len(texts) + self.batch_size - 1) // self.batch_size} batches")
            return all_embeddings

        except Exception as e:
            logger.error(f"Error in synchronous document embedding: {str(e)}")
            raise

    def embed_query(self, text: str) -> List[float]:
        """
        Embed a single query text synchronously.
        
        This method is optimized for single query embedding.

        Args:
            text: Query text to embed

        Returns:
            Embedding vector for the query
            
        Raises:
            ValueError: If text is empty
            Exception: If embedding generation fails
        """
        import asyncio

        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        try:
            # Get or create event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    raise RuntimeError("Event loop is closed")
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Generate embedding
            result = loop.run_until_complete(
                self.embedding_provider.embed_text(text)
            )
            
            logger.debug(f"Embedded query: {len(result)} dimensions")
            return result

        except Exception as e:
            logger.error(f"Error in synchronous query embedding: {str(e)}")
            raise

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of documents asynchronously.
        
        This method provides native async execution for better performance
        in async contexts. Documents are processed in batches.

        Args:
            texts: List of document texts to embed

        Returns:
            List of embedding vectors, one per document
            
        Raises:
            ValueError: If texts list is empty
            Exception: If embedding generation fails
        """
        if not texts:
            raise ValueError("Texts list cannot be empty")

        try:
            # Process in batches
            all_embeddings = []
            for i in range(0, len(texts), self.batch_size):
                batch = texts[i:i + self.batch_size]
                batch_embeddings = await self.embedding_provider.embed_texts(batch)
                all_embeddings.extend(batch_embeddings)
            
            logger.debug(f"Async embedded {len(texts)} documents in {(len(texts) + self.batch_size - 1) // self.batch_size} batches")
            return all_embeddings

        except Exception as e:
            logger.error(f"Error in asynchronous document embedding: {str(e)}")
            raise

    async def aembed_query(self, text: str) -> List[float]:
        """
        Embed a single query text asynchronously.
        
        This method provides native async execution for better performance.

        Args:
            text: Query text to embed

        Returns:
            Embedding vector for the query
            
        Raises:
            ValueError: If text is empty
            Exception: If embedding generation fails
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        try:
            result = await self.embedding_provider.embed_text(text)
            logger.debug(f"Async embedded query: {len(result)} dimensions")
            return result

        except Exception as e:
            logger.error(f"Error in asynchronous query embedding: {str(e)}")
            raise

    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings.
        
        Returns:
            Integer dimension of the embedding vectors
        """
        return self.embedding_provider.get_embedding_dimension()

    @property
    def _identifying_params(self) -> dict:
        """
        Get identifying parameters for the embeddings.
        
        Returns:
            Dictionary of identifying parameters
        """
        return {
            "model_name": self.model_name,
            "batch_size": self.batch_size,
            "embedding_dimension": self.get_embedding_dimension(),
        }
