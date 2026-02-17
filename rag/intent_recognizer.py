"""Intent recognition module for understanding user commands."""

import logging
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class IntentResult:
    """Result from intent recognition."""

    intent: str  # query, manage, update, delete
    entities: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    raw_response: str = ""


class IntentRecognizer:
    """Recognizes user intent and extracts entities."""

    VALID_INTENTS = {"query", "manage", "update", "delete"}

    def __init__(self, llm_provider=None):
        """
        Initialize intent recognizer.

        Args:
            llm_provider: Provider for LLM calls
        """
        self.llm_provider = llm_provider

    async def recognize_intent(self, user_input: str) -> IntentResult:
        """
        Recognize user intent from input.

        Args:
            user_input: User input string

        Returns:
            IntentResult with intent, entities, and confidence

        Raises:
            ValueError: If user input is empty
        """
        if not user_input or not user_input.strip():
            raise ValueError("User input cannot be empty")

        if self.llm_provider is None:
            logger.warning("LLM provider not set, using default intent")
            return IntentResult(
                intent="query",
                entities={},
                confidence=0.5,
                raw_response="",
            )

        try:
            # Classify intent
            intent = await self._classify_intent(user_input)

            # Extract entities
            entities = await self._extract_entities(user_input, intent)

            # Fill slots
            filled_entities = await self._fill_slots(intent, entities)

            # Determine confidence
            confidence = self._calculate_confidence(intent, filled_entities)

            logger.info(
                f"Intent recognized: {intent} (confidence: {confidence:.2f})"
            )

            return IntentResult(
                intent=intent,
                entities=filled_entities,
                confidence=confidence,
                raw_response="",
            )

        except Exception as e:
            logger.error(f"Error recognizing intent: {str(e)}")
            # Return default intent on error
            return IntentResult(
                intent="query",
                entities={},
                confidence=0.0,
                raw_response=str(e),
            )

    async def _classify_intent(self, user_input: str) -> str:
        """
        Classify user intent.

        Args:
            user_input: User input string

        Returns:
            Intent type (query, manage, update, delete)

        Raises:
            Exception: If LLM call fails
        """
        prompt = f"""Classify the following user input into one of these categories:
- query: User wants to search or retrieve information
- manage: User wants to manage knowledge bases or documents
- update: User wants to update or modify existing data
- delete: User wants to delete data

User input: {user_input}

Respond with only the category name (query, manage, update, or delete)."""

        try:
            response = await self.llm_provider.generate(prompt, max_tokens=10)
            intent = response.strip().lower()

            # Validate intent
            if intent not in self.VALID_INTENTS:
                logger.warning(f"Invalid intent: {intent}, defaulting to query")
                return "query"

            return intent
        except Exception as e:
            logger.error(f"Error classifying intent: {str(e)}")
            raise

    async def _extract_entities(
        self, user_input: str, intent: str
    ) -> Dict[str, Any]:
        """
        Extract entities from user input.

        Args:
            user_input: User input string
            intent: Classified intent

        Returns:
            Dictionary of extracted entities

        Raises:
            Exception: If LLM call fails
        """
        prompt = f"""Extract relevant entities from the following user input.
Return the result as a JSON object with the following possible keys:
- kb_name: Name of knowledge base
- doc_name: Name of document
- doc_type: Type of document (pdf, docx, md, txt)
- time_range: Time range mentioned
- query_text: The actual query or search text
- other_info: Any other relevant information

User input: {user_input}
Intent: {intent}

Return only valid JSON, no additional text."""

        try:
            response = await self.llm_provider.generate(prompt, max_tokens=300)
            if response and response.strip():
                try:
                    entities = json.loads(response.strip())
                    return entities
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse entities JSON: {response}")
                    return {}
            return {}
        except Exception as e:
            logger.error(f"Error extracting entities: {str(e)}")
            raise

    async def _fill_slots(
        self, intent: str, entities: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Fill missing slots in entities.

        Args:
            intent: User intent
            entities: Extracted entities

        Returns:
            Filled entities dictionary
        """
        # Add default values for missing slots
        filled = entities.copy()

        if intent == "query":
            if "query_text" not in filled:
                filled["query_text"] = ""
        elif intent == "manage":
            if "kb_name" not in filled:
                filled["kb_name"] = ""
        elif intent == "update":
            if "kb_name" not in filled:
                filled["kb_name"] = ""
            if "doc_name" not in filled:
                filled["doc_name"] = ""
        elif intent == "delete":
            if "kb_name" not in filled:
                filled["kb_name"] = ""
            if "doc_name" not in filled:
                filled["doc_name"] = ""

        return filled

    def _calculate_confidence(
        self, intent: str, entities: Dict[str, Any]
    ) -> float:
        """
        Calculate confidence score for intent recognition.

        Args:
            intent: Recognized intent
            entities: Extracted entities

        Returns:
            Confidence score between 0 and 1
        """
        # Base confidence
        confidence = 0.7

        # Increase confidence if key entities are present
        if intent == "query" and entities.get("query_text"):
            confidence = min(1.0, confidence + 0.2)
        elif intent == "manage" and entities.get("kb_name"):
            confidence = min(1.0, confidence + 0.2)
        elif intent == "update" and (
            entities.get("kb_name") or entities.get("doc_name")
        ):
            confidence = min(1.0, confidence + 0.2)
        elif intent == "delete" and (
            entities.get("kb_name") or entities.get("doc_name")
        ):
            confidence = min(1.0, confidence + 0.2)

        return confidence

    async def recognize_intent_with_fallback(
        self, user_input: str
    ) -> IntentResult:
        """
        Recognize intent with fallback to default.

        Args:
            user_input: User input string

        Returns:
            IntentResult with fallback to query intent
        """
        try:
            return await self.recognize_intent(user_input)
        except Exception as e:
            logger.warning(f"Intent recognition failed, using default: {str(e)}")
            return IntentResult(
                intent="query",
                entities={},
                confidence=0.0,
                raw_response=str(e),
            )
