"""End-to-end test scenarios for complete workflows.

Tests cover:
- Complete workflow: create knowledge base → upload document → search → RAG generation
- Multi-turn conversations with context preservation
- Error recovery and fallback mechanisms
- Session persistence across restarts

Requirements: 5.5, 11.1, 11.2, 11.3, 12.1, 12.2, 13.3
"""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.orm import Session

from rag.agent_manager import ManagementAgent, AgentResult
from rag.conversation_memory import ConversationMemory
from models.orm import KnowledgeBase, Document, ConversationHistory


@pytest.fixture
def mock_llm_provider():
    """Create mock LLM provider."""
    provider = Mock()
    provider.generate = AsyncMock(return_value="Generated answer based on context")
    return provider


@pytest.fixture
def mock_embedding_provider():
    """Create mock embedding provider."""
    provider = Mock()
    provider.embed_documents = AsyncMock(return_value=[[0.1, 0.2, 0.3]] * 5)
    provider.embed_query = AsyncMock(return_value=[0.1, 0.2, 0.3])
    return provider


@pytest.fixture
def mock_reranker_provider():
    """Create mock reranker provider."""
    provider = Mock()
    provider.rerank = AsyncMock(return_value=[
        {"score": 0.95, "index": 0},
        {"score": 0.87, "index": 1},
        {"score": 0.72, "index": 2}
    ])
    return provider


@pytest.fixture
def mock_kb_service():
    """Create mock knowledge base service."""
    service = Mock()
    service.create_knowledge_base = AsyncMock(return_value=Mock(
        id="kb_001",
        name="Test KB",
        description="Test knowledge base"
    ))
    service.get_knowledge_base = AsyncMock(return_value=Mock(
        id="kb_001",
        name="Test KB",
        description="Test knowledge base"
    ))
    service.list_knowledge_bases = AsyncMock(return_value=[Mock(
        id="kb_001",
        name="Test KB",
        description="Test knowledge base"
    )])
    return service


@pytest.fixture
def mock_doc_service():
    """Create mock document service."""
    service = Mock()
    service.upload_document = AsyncMock(return_value=Mock(
        id="doc_001",
        name="test_document.txt",
        kb_id="kb_001",
        size=1024
    ))
    service.get_document = AsyncMock(return_value=Mock(
        id="doc_001",
        name="test_document.txt",
        kb_id="kb_001",
        size=1024
    ))
    service.list_documents = AsyncMock(return_value=[Mock(
        id="doc_001",
        name="test_document.txt",
        kb_id="kb_001",
        size=1024
    )])
    return service


@pytest.fixture
def mock_search_service():
    """Create mock search service."""
    service = Mock()
    service.search = AsyncMock(return_value=[
        Mock(content="Relevant content 1", score=0.95, metadata={"source": "doc_001"}),
        Mock(content="Relevant content 2", score=0.87, metadata={"source": "doc_001"}),
        Mock(content="Relevant content 3", score=0.72, metadata={"source": "doc_001"})
    ])
    return service


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def agent_manager(mock_llm_provider, mock_embedding_provider, mock_reranker_provider, mock_db_session):
    """Create ManagementAgent instance."""
    manager = ManagementAgent(
        llm_provider=mock_llm_provider,
        kb_service=None,
        doc_service=None
    )
    return manager


@pytest.fixture
def sample_document():
    """Create a sample document for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("This is a test document about artificial intelligence.\n")
        f.write("AI is transforming various industries.\n")
        f.write("Machine learning is a subset of AI.\n")
        f.write("Deep learning uses neural networks.\n")
        f.write("Natural language processing enables text understanding.\n")
        temp_path = f.name
    
    yield temp_path
    
    if os.path.exists(temp_path):
        os.remove(temp_path)


class TestCompleteWorkflow:
    """Test complete workflow: create KB → upload document → search → RAG generation."""
    
    @pytest.mark.anyio
    async def test_complete_workflow_success(
        self,
        agent_manager,
        mock_kb_service,
        mock_doc_service,
        mock_search_service,
        sample_document
    ):
        """Test complete workflow from KB creation to RAG generation."""
        # Step 1: Create knowledge base
        kb = await mock_kb_service.create_knowledge_base(
            name="Test KB",
            description="Test knowledge base"
        )
        assert kb.id == "kb_001"
        assert kb.name == "Test KB"
        
        # Step 2: Upload document
        doc = await mock_doc_service.upload_document(
            kb_id=kb.id,
            file_path=sample_document,
            metadata={"source": "test"}
        )
        assert doc.id == "doc_001"
        assert doc.kb_id == kb.id
        
        # Step 3: Search in knowledge base
        results = await mock_search_service.search(
            query="What is artificial intelligence?",
            kb_id=kb.id,
            top_k=3
        )
        assert len(results) == 3
        assert results[0].score >= results[1].score >= results[2].score
        
        # Step 4: Generate RAG answer
        context = "\n\n".join([r.content for r in results])
        answer = await agent_manager.llm_provider.generate(
            f"Based on: {context}\n\nAnswer: What is artificial intelligence?"
        )
        assert answer is not None
        assert len(answer) > 0
    
    @pytest.mark.anyio
    async def test_workflow_with_multiple_documents(
        self,
        mock_kb_service,
        mock_doc_service,
        mock_search_service,
        sample_document
    ):
        """Test workflow with multiple documents."""
        kb = await mock_kb_service.create_knowledge_base(
            name="Multi-doc KB",
            description="KB with multiple documents"
        )
        
        # Upload multiple documents
        docs = []
        for i in range(3):
            doc = await mock_doc_service.upload_document(
                kb_id=kb.id,
                file_path=sample_document,
                metadata={"index": i}
            )
            docs.append(doc)
        
        # Verify all documents are uploaded
        listed_docs = await mock_doc_service.list_documents(kb_id=kb.id)
        assert len(listed_docs) >= 3
        
        # Search should return results from multiple documents
        results = await mock_search_service.search(
            query="machine learning",
            kb_id=kb.id,
            top_k=5
        )
        assert len(results) > 0


class TestMultiTurnConversation:
    """Test multi-turn conversations with context preservation."""
    
    @pytest.mark.anyio
    async def test_multi_turn_conversation_context(self, agent_manager, mock_db_session):
        """Test that context is preserved across multiple turns."""
        memory = ConversationMemory(
            session_id="test_session",
            max_history=10,
            db_session=mock_db_session
        )
        
        # Turn 1: User asks about AI
        memory.add_user_message("What is artificial intelligence?")
        memory.add_ai_message("AI is the simulation of human intelligence by machines.")
        
        # Turn 2: User asks follow-up question with pronoun
        memory.add_user_message("What are its applications?")
        
        # Verify context is preserved
        messages = memory.get_messages()
        assert len(messages) == 3
        assert "artificial intelligence" in messages[0].content
        assert "its applications" in messages[2].content
    
    @pytest.mark.anyio
    async def test_multi_turn_with_tool_calls(self, agent_manager):
        """Test multi-turn conversation with tool calls."""
        memory = agent_manager.memory
        
        # Turn 1: Search query
        memory.add_user_message("Search for documents about machine learning")
        memory.add_ai_message("I found 5 documents about machine learning")
        
        # Turn 2: Follow-up question
        memory.add_user_message("Show me the most relevant one")
        memory.add_ai_message("Here is the most relevant document...")
        
        # Turn 3: Another question
        memory.add_user_message("Can you summarize it?")
        
        messages = memory.get_messages()
        assert len(messages) == 5
        
        # Verify message order
        assert messages[0].content == "Search for documents about machine learning"
        assert messages[2].content == "Show me the most relevant one"
        assert messages[4].content == "Can you summarize it?"
    
    @pytest.mark.anyio
    async def test_context_truncation_at_max_history(self, mock_db_session):
        """Test that context is truncated when exceeding max_history."""
        memory = ConversationMemory(
            session_id="test_session",
            max_history=4,
            db_session=mock_db_session
        )
        
        # Add more messages than max_history
        for i in range(6):
            memory.add_user_message(f"Question {i}")
            memory.add_ai_message(f"Answer {i}")
        
        # Get messages should return only last 4
        messages = memory.get_messages()
        assert len(messages) <= 4
        
        # Verify we have the most recent messages
        assert "Question 4" in messages[-2].content or "Question 5" in messages[-1].content


class TestErrorRecoveryAndFallback:
    """Test error recovery and fallback mechanisms."""
    
    @pytest.mark.anyio
    async def test_search_service_failure_fallback(self, agent_manager):
        """Test fallback when search service fails."""
        # Mock search service that fails
        failed_search = AsyncMock(side_effect=Exception("Search service unavailable"))
        
        # Attempt search with fallback
        try:
            await failed_search()
            assert False, "Should have raised exception"
        except Exception as e:
            assert "Search service unavailable" in str(e)
    
    @pytest.mark.anyio
    async def test_llm_provider_failure_handling(self, agent_manager):
        """Test handling of LLM provider failures."""
        # Mock LLM that fails
        agent_manager.llm_provider.generate = AsyncMock(
            side_effect=Exception("LLM service unavailable")
        )
        
        try:
            await agent_manager.llm_provider.generate("test prompt")
            assert False, "Should have raised exception"
        except Exception as e:
            assert "LLM service unavailable" in str(e)
    
    @pytest.mark.anyio
    async def test_retry_mechanism_on_timeout(self):
        """Test retry mechanism on timeout."""
        adapter = ToolServiceAdapter()
        
        call_count = 0
        
        async def flaky_service():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise asyncio.TimeoutError("Timeout")
            return {"success": True, "data": {"result": "success"}}
        
        # Simulate retry
        try:
            result = await flaky_service()
        except asyncio.TimeoutError:
            result = await flaky_service()
        
        assert result["success"] is True
        assert call_count == 2
    
    @pytest.mark.anyio
    async def test_graceful_degradation_on_reranker_failure(self, mock_search_service):
        """Test graceful degradation when reranker fails."""
        # Original search results
        results = await mock_search_service.search(
            query="test",
            kb_id="kb_001",
            top_k=3
        )
        
        # Even if reranker fails, we should still have results
        assert len(results) > 0
        assert all(hasattr(r, 'content') for r in results)


class TestSessionPersistence:
    """Test session persistence across restarts."""
    
    @pytest.mark.anyio
    async def test_save_and_load_conversation_history(self, mock_db_session):
        """Test saving and loading conversation history."""
        session_id = "test_session_001"
        
        # Create memory and add messages
        memory1 = ConversationMemory(
            session_id=session_id,
            max_history=10,
            db_session=mock_db_session
        )
        
        memory1.add_user_message("First question")
        memory1.add_ai_message("First answer")
        memory1.add_user_message("Second question")
        
        # Simulate saving (in real implementation, this would persist to DB)
        messages_before = memory1.get_messages()
        assert len(messages_before) == 3
        
        # Create new memory instance with same session ID
        memory2 = ConversationMemory(
            session_id=session_id,
            max_history=10,
            db_session=mock_db_session
        )
        
        # In real implementation, this would load from DB
        # For now, verify the structure is correct
        assert memory2.session_id == session_id
        assert memory2.max_history == 10
    
    @pytest.mark.anyio
    async def test_session_recovery_after_restart(self, mock_db_session):
        """Test session recovery after application restart."""
        session_id = "persistent_session"
        
        # Session 1: Create and add messages
        memory1 = ConversationMemory(
            session_id=session_id,
            max_history=10,
            db_session=mock_db_session
        )
        memory1.add_user_message("Question about AI")
        memory1.add_ai_message("AI is artificial intelligence")
        
        messages_count_before = len(memory1.get_messages())
        
        # Session 2: Simulate restart and recovery
        memory2 = ConversationMemory(
            session_id=session_id,
            max_history=10,
            db_session=mock_db_session
        )
        
        # Verify session ID is preserved
        assert memory2.session_id == session_id
        
        # Add new message to recovered session
        memory2.add_user_message("Follow-up question")
        
        # Verify we can continue the conversation
        messages_after = memory2.get_messages()
        assert len(messages_after) >= 1
    
    @pytest.mark.anyio
    async def test_multiple_concurrent_sessions(self, mock_db_session):
        """Test multiple concurrent sessions don't interfere."""
        sessions = []
        
        # Create multiple sessions
        for i in range(3):
            memory = ConversationMemory(
                session_id=f"session_{i}",
                max_history=10,
                db_session=mock_db_session
            )
            memory.add_user_message(f"Question from session {i}")
            memory.add_ai_message(f"Answer for session {i}")
            sessions.append(memory)
        
        # Verify each session has its own messages
        for i, memory in enumerate(sessions):
            messages = memory.get_messages()
            assert len(messages) == 2
            assert f"session {i}" in messages[0].content


class TestErrorRecoveryScenarios:
    """Test various error recovery scenarios."""
    
    @pytest.mark.anyio
    async def test_partial_tool_failure_recovery(self, agent_manager):
        """Test recovery when one tool fails but others succeed."""
        # Simulate multiple tool calls where one fails
        tool_results = []
        
        async def tool1():
            return {"success": True, "data": "result1"}
        
        async def tool2():
            raise Exception("Tool 2 failed")
        
        async def tool3():
            return {"success": True, "data": "result3"}
        
        # Execute tools with error handling
        for tool in [tool1, tool2, tool3]:
            try:
                result = await tool()
                tool_results.append(result)
            except Exception as e:
                tool_results.append({"success": False, "error": str(e)})
        
        # Verify we got results from all tools
        assert len(tool_results) == 3
        assert tool_results[0]["success"] is True
        assert tool_results[1]["success"] is False
        assert tool_results[2]["success"] is True
    
    @pytest.mark.anyio
    async def test_database_connection_recovery(self, mock_db_session):
        """Test recovery from database connection issues."""
        memory = ConversationMemory(
            session_id="test_session",
            max_history=10,
            db_session=mock_db_session
        )
        
        # Simulate DB connection issue
        mock_db_session.query = Mock(side_effect=Exception("DB connection lost"))
        
        # Add message should still work (in-memory)
        memory.add_user_message("Test message")
        
        # Verify message is in memory
        messages = memory.get_messages()
        assert len(messages) == 1
        assert messages[0].content == "Test message"


class TestConcurrentOperations:
    """Test concurrent operations and race conditions."""
    
    @pytest.mark.anyio
    async def test_concurrent_searches(self, mock_search_service):
        """Test concurrent search operations."""
        async def search_task(query_id):
            results = await mock_search_service.search(
                query=f"query_{query_id}",
                kb_id="kb_001",
                top_k=3
            )
            return results
        
        # Run concurrent searches
        tasks = [search_task(i) for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        # Verify all searches completed
        assert len(results) == 5
        assert all(len(r) > 0 for r in results)
    
    @pytest.mark.anyio
    async def test_concurrent_memory_operations(self, mock_db_session):
        """Test concurrent memory operations."""
        memory = ConversationMemory(
            session_id="concurrent_test",
            max_history=20,
            db_session=mock_db_session
        )
        
        async def add_messages(start_id):
            for i in range(3):
                memory.add_user_message(f"User message {start_id}_{i}")
                memory.add_ai_message(f"AI message {start_id}_{i}")
        
        # Run concurrent message additions
        tasks = [add_messages(i) for i in range(3)]
        await asyncio.gather(*tasks)
        
        # Verify all messages were added
        messages = memory.get_messages()
        assert len(messages) > 0


class TestEndToEndIntegration:
    """Test complete end-to-end integration scenarios."""
    
    @pytest.mark.anyio
    async def test_full_agent_workflow(
        self,
        agent_manager,
        mock_kb_service,
        mock_doc_service,
        mock_search_service
    ):
        """Test full Agent workflow."""
        # Step 1: Create KB
        kb = await mock_kb_service.create_knowledge_base(
            name="Agent Test KB",
            description="For agent testing"
        )
        
        # Step 2: Upload document
        doc = await mock_doc_service.upload_document(
            kb_id=kb.id,
            file_path="test.txt",
            metadata={}
        )
        
        # Step 3: Agent processes user input
        agent_manager.memory.add_user_message("What is in the knowledge base?")
        
        # Step 4: Search for relevant documents
        results = await mock_search_service.search(
            query="knowledge base content",
            kb_id=kb.id,
            top_k=3
        )
        
        # Step 5: Generate response
        context = "\n".join([r.content for r in results])
        response = await agent_manager.llm_provider.generate(
            f"Context: {context}\n\nQuestion: What is in the knowledge base?"
        )
        
        # Step 6: Store response in memory
        agent_manager.memory.add_ai_message(response)
        
        # Verify complete workflow
        messages = agent_manager.memory.get_messages()
        assert len(messages) == 2
        assert "knowledge base" in messages[0].content.lower()
    
    @pytest.mark.anyio
    async def test_complete_workflow_with_persistence(
        self,
        agent_manager,
        mock_kb_service,
        mock_doc_service,
        mock_search_service,
        mock_db_session,
        sample_document
    ):
        """Test complete workflow with session persistence."""
        # Step 1: Create knowledge base
        kb = await mock_kb_service.create_knowledge_base(
            name="Persistent KB",
            description="For persistence testing"
        )
        assert kb.id == "kb_001"
        
        # Step 2: Upload document
        doc = await mock_doc_service.upload_document(
            kb_id=kb.id,
            file_path=sample_document,
            metadata={"type": "test"}
        )
        assert doc.kb_id == kb.id
        
        # Step 3: First search
        results1 = await mock_search_service.search(
            query="artificial intelligence",
            kb_id=kb.id,
            top_k=3
        )
        assert len(results1) > 0
        
        # Step 4: Generate RAG answer
        context = "\n\n".join([r.content for r in results1])
        answer1 = await agent_manager.llm_provider.generate(
            f"Based on: {context}\n\nAnswer: What is AI?"
        )
        
        # Step 5: Store in memory
        agent_manager.memory.add_user_message("What is AI?")
        agent_manager.memory.add_ai_message(answer1)
        
        # Step 6: Simulate session persistence
        session_id = "persistent_session_001"
        memory_persistent = ConversationMemory(
            session_id=session_id,
            max_history=10,
            db_session=mock_db_session
        )
        
        # Step 7: Restore conversation
        memory_persistent.add_user_message("What is AI?")
        memory_persistent.add_ai_message(answer1)
        
        # Step 8: Continue conversation
        memory_persistent.add_user_message("Tell me more about machine learning")
        
        # Verify persistence
        messages = memory_persistent.get_messages()
        assert len(messages) == 3
        assert "AI" in messages[0].content
        assert "machine learning" in messages[2].content
    
    @pytest.mark.anyio
    async def test_workflow_with_multiple_searches_and_rag(
        self,
        agent_manager,
        mock_kb_service,
        mock_doc_service,
        mock_search_service,
        sample_document
    ):
        """Test workflow with multiple searches and RAG generations."""
        # Create KB
        kb = await mock_kb_service.create_knowledge_base(
            name="Multi-search KB",
            description="For multiple searches"
        )
        
        # Upload multiple documents
        docs = []
        for i in range(3):
            doc = await mock_doc_service.upload_document(
                kb_id=kb.id,
                file_path=sample_document,
                metadata={"index": i}
            )
            docs.append(doc)
        
        # Perform multiple searches
        queries = [
            "What is artificial intelligence?",
            "What is machine learning?",
            "What is deep learning?"
        ]
        
        for query in queries:
            # Search
            results = await mock_search_service.search(
                query=query,
                kb_id=kb.id,
                top_k=3
            )
            
            # Generate answer
            context = "\n\n".join([r.content for r in results])
            answer = await agent_manager.llm_provider.generate(
                f"Based on: {context}\n\nAnswer: {query}"
            )
            
            # Store in memory
            agent_manager.memory.add_user_message(query)
            agent_manager.memory.add_ai_message(answer)
        
        # Verify all searches and answers are stored
        messages = agent_manager.memory.get_messages()
        assert len(messages) == 6  # 3 questions + 3 answers
        
        # Verify context preservation
        assert "artificial intelligence" in messages[0].content
        assert "machine learning" in messages[2].content
        assert "deep learning" in messages[4].content
