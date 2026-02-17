"""Text chunking strategies for document processing."""

from typing import List
import logging

from langchain.text_splitter import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


class ChunkingStrategy:
    """Implements text chunking strategies for document processing."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: List[str] = None,
    ):
        """
        Initialize chunking strategy.

        Args:
            chunk_size: Size of each chunk in characters
            chunk_overlap: Number of overlapping characters between chunks
            separators: List of separators to use for splitting
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", " ", ""]

    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks using recursive character splitting.

        Args:
            text: Text to chunk

        Returns:
            List of text chunks

        Raises:
            ValueError: If text is empty or invalid
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        try:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                separators=self.separators,
                length_function=len,
            )

            chunks = splitter.split_text(text)

            if not chunks:
                raise ValueError("No chunks could be created from text")

            logger.info(
                f"Text chunked into {len(chunks)} chunks "
                f"(size: {self.chunk_size}, overlap: {self.chunk_overlap})"
            )

            return chunks
        except Exception as e:
            logger.error(f"Error chunking text: {str(e)}")
            raise

    def chunk_text_with_metadata(
        self, text: str, metadata: dict = None
    ) -> List[dict]:
        """
        Split text into chunks with metadata.

        Args:
            text: Text to chunk
            metadata: Optional metadata to attach to each chunk

        Returns:
            List of dicts with 'content' and 'metadata' keys
        """
        chunks = self.chunk_text(text)
        metadata = metadata or {}

        return [
            {
                "content": chunk,
                "metadata": {**metadata, "chunk_index": i},
            }
            for i, chunk in enumerate(chunks)
        ]
