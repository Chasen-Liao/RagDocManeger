"""Tests for intent recognizer."""

import pytest
from RagDocMan.rag.intent_recognizer import IntentRecognizer, IntentResult


class TestIntentRecognizer:
    """Test intent recognizer."""

    def test_init_without_provider(self):
        """Test initialization without provider."""
        recognizer = IntentRecognizer()
        assert recognizer.llm_provider is None

    @pytest.mark.asyncio
    async def test_recognize_intent_without_provider(self):
        """Test recognizing intent without provider."""
        recognizer = IntentRecognizer()
        result = await recognizer.recognize_intent("search for python")
        assert isinstance(result, IntentResult)
        assert result.intent == "query"

    @pytest.mark.asyncio
    async def test_recognize_intent_with_empty_input(self):
        """Test recognizing intent with empty input."""
        recognizer = IntentRecognizer()
        with pytest.raises(ValueError, match="User input cannot be empty"):
            await recognizer.recognize_intent("")

    @pytest.mark.asyncio
    async def test_recognize_intent_with_whitespace(self):
        """Test recognizing intent with whitespace input."""
        recognizer = IntentRecognizer()
        with pytest.raises(ValueError, match="User input cannot be empty"):
            await recognizer.recognize_intent("   ")

    @pytest.mark.asyncio
    async def test_recognize_intent_with_fallback(self):
        """Test recognizing intent with fallback."""
        recognizer = IntentRecognizer()
        result = await recognizer.recognize_intent_with_fallback("search for python")
        assert isinstance(result, IntentResult)
        assert result.intent == "query"

    def test_valid_intents(self):
        """Test valid intents."""
        assert "query" in IntentRecognizer.VALID_INTENTS
        assert "manage" in IntentRecognizer.VALID_INTENTS
        assert "update" in IntentRecognizer.VALID_INTENTS
        assert "delete" in IntentRecognizer.VALID_INTENTS
