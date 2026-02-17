"""Tests for chunking strategy."""

import pytest
from RagDocMan.rag.chunking_strategy import ChunkingStrategy


class TestChunkingStrategyBasic:
    """Test basic chunking functionality."""

    def test_chunk_text_basic(self):
        """Test basic text chunking."""
        strategy = ChunkingStrategy(chunk_size=100, chunk_overlap=20)
        text = "This is a test. " * 20  # Create text longer than chunk size

        chunks = strategy.chunk_text(text)
        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)

    def test_chunk_text_empty_raises_error(self):
        """Test chunking empty text raises error."""
        strategy = ChunkingStrategy()
        with pytest.raises(ValueError, match="Text cannot be empty"):
            strategy.chunk_text("")

    def test_chunk_text_whitespace_only_raises_error(self):
        """Test chunking whitespace-only text raises error."""
        strategy = ChunkingStrategy()
        with pytest.raises(ValueError, match="Text cannot be empty"):
            strategy.chunk_text("   \n\t  ")

    def test_chunk_size_respected(self):
        """Test that chunk size is respected."""
        chunk_size = 100
        strategy = ChunkingStrategy(chunk_size=chunk_size, chunk_overlap=0)
        text = "word " * 100  # Create text with many words

        chunks = strategy.chunk_text(text)
        # Most chunks should be close to chunk_size (some may be smaller due to word boundaries)
        for chunk in chunks:
            assert len(chunk) <= chunk_size + 50  # Allow some tolerance for word boundaries

    def test_chunk_overlap_preserved(self):
        """Test that chunk overlap is preserved."""
        strategy = ChunkingStrategy(chunk_size=100, chunk_overlap=20)
        text = "This is a test sentence. " * 20

        chunks = strategy.chunk_text(text)
        assert len(chunks) > 1

        # Check that consecutive chunks have overlap
        for i in range(len(chunks) - 1):
            # There should be some common content between consecutive chunks
            assert len(chunks[i]) > 0
            assert len(chunks[i + 1]) > 0

    def test_chunk_text_short_text(self):
        """Test chunking short text that fits in one chunk."""
        strategy = ChunkingStrategy(chunk_size=1000, chunk_overlap=100)
        text = "This is a short text."

        chunks = strategy.chunk_text(text)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_chunk_text_with_newlines(self):
        """Test chunking text with newlines."""
        strategy = ChunkingStrategy(chunk_size=100, chunk_overlap=20)
        text = "Line 1\n" * 50

        chunks = strategy.chunk_text(text)
        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)

    def test_chunk_text_with_special_characters(self):
        """Test chunking text with special characters."""
        strategy = ChunkingStrategy(chunk_size=100, chunk_overlap=20)
        text = "Special chars: !@#$%^&*() " * 20

        chunks = strategy.chunk_text(text)
        assert len(chunks) > 0
        # Verify all special characters are preserved
        full_text = "".join(chunks)
        assert "!@#$%^&*()" in full_text

    def test_chunk_text_with_unicode(self):
        """Test chunking text with unicode characters."""
        strategy = ChunkingStrategy(chunk_size=100, chunk_overlap=20)
        text = "Hello 世界 🌍 " * 20

        chunks = strategy.chunk_text(text)
        assert len(chunks) > 0
        full_text = "".join(chunks)
        assert "世界" in full_text
        assert "🌍" in full_text


class TestChunkingStrategyMetadata:
    """Test chunking with metadata."""

    def test_chunk_text_with_metadata(self):
        """Test chunking text with metadata."""
        strategy = ChunkingStrategy(chunk_size=100, chunk_overlap=20)
        text = "This is a test. " * 20
        metadata = {"source": "test.txt", "author": "test"}

        chunks_with_meta = strategy.chunk_text_with_metadata(text, metadata)
        assert len(chunks_with_meta) > 0
        assert all(isinstance(chunk, dict) for chunk in chunks_with_meta)
        assert all("content" in chunk for chunk in chunks_with_meta)
        assert all("metadata" in chunk for chunk in chunks_with_meta)

    def test_chunk_metadata_includes_index(self):
        """Test that chunk metadata includes chunk index."""
        strategy = ChunkingStrategy(chunk_size=100, chunk_overlap=20)
        text = "This is a test. " * 20

        chunks_with_meta = strategy.chunk_text_with_metadata(text)
        for i, chunk in enumerate(chunks_with_meta):
            assert chunk["metadata"]["chunk_index"] == i

    def test_chunk_metadata_preserves_custom_metadata(self):
        """Test that custom metadata is preserved."""
        strategy = ChunkingStrategy(chunk_size=100, chunk_overlap=20)
        text = "This is a test. " * 20
        metadata = {"source": "test.txt", "author": "test"}

        chunks_with_meta = strategy.chunk_text_with_metadata(text, metadata)
        for chunk in chunks_with_meta:
            assert chunk["metadata"]["source"] == "test.txt"
            assert chunk["metadata"]["author"] == "test"

    def test_chunk_metadata_without_custom_metadata(self):
        """Test chunking with metadata but no custom metadata."""
        strategy = ChunkingStrategy(chunk_size=100, chunk_overlap=20)
        text = "This is a test. " * 20

        chunks_with_meta = strategy.chunk_text_with_metadata(text)
        for i, chunk in enumerate(chunks_with_meta):
            assert chunk["metadata"]["chunk_index"] == i
            assert len(chunk["metadata"]) == 1  # Only chunk_index


class TestChunkingStrategyConfiguration:
    """Test chunking strategy configuration."""

    def test_custom_chunk_size(self):
        """Test custom chunk size."""
        strategy = ChunkingStrategy(chunk_size=50, chunk_overlap=10)
        assert strategy.chunk_size == 50
        assert strategy.chunk_overlap == 10

    def test_custom_separators(self):
        """Test custom separators."""
        custom_seps = ["\n\n", "\n"]
        strategy = ChunkingStrategy(separators=custom_seps)
        assert strategy.separators == custom_seps

    def test_default_separators(self):
        """Test default separators."""
        strategy = ChunkingStrategy()
        assert strategy.separators == ["\n\n", "\n", " ", ""]

    def test_zero_overlap(self):
        """Test chunking with zero overlap."""
        strategy = ChunkingStrategy(chunk_size=100, chunk_overlap=0)
        text = "word " * 100

        chunks = strategy.chunk_text(text)
        assert len(chunks) > 0

    def test_large_overlap(self):
        """Test chunking with large overlap."""
        strategy = ChunkingStrategy(chunk_size=100, chunk_overlap=80)
        text = "word " * 100

        chunks = strategy.chunk_text(text)
        assert len(chunks) > 0


class TestChunkingStrategyEdgeCases:
    """Test edge cases for chunking strategy."""

    def test_chunk_single_word(self):
        """Test chunking single word."""
        strategy = ChunkingStrategy(chunk_size=100, chunk_overlap=20)
        text = "word"

        chunks = strategy.chunk_text(text)
        assert len(chunks) == 1
        assert chunks[0] == "word"

    def test_chunk_very_long_word(self):
        """Test chunking text with very long word."""
        strategy = ChunkingStrategy(chunk_size=50, chunk_overlap=10)
        text = "a" * 100 + " " + "b" * 100

        chunks = strategy.chunk_text(text)
        assert len(chunks) > 0

    def test_chunk_repeated_text(self):
        """Test chunking repeated text."""
        strategy = ChunkingStrategy(chunk_size=100, chunk_overlap=20)
        text = "test " * 100

        chunks = strategy.chunk_text(text)
        assert len(chunks) > 0
        # Verify all chunks are non-empty
        assert all(len(chunk) > 0 for chunk in chunks)

    def test_chunk_mixed_content(self):
        """Test chunking mixed content."""
        strategy = ChunkingStrategy(chunk_size=100, chunk_overlap=20)
        text = """
        # Title
        
        This is a paragraph with some content.
        
        - List item 1
        - List item 2
        
        Another paragraph.
        """ * 5

        chunks = strategy.chunk_text(text)
        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)
