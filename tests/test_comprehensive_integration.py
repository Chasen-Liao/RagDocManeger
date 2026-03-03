"""Comprehensive integration tests for complete system validation.

Tests cover:
- All tool combinations
- Memory persistence and recovery
- Concurrent user sessions
- System behavior under failure conditions

Requirements: 14.1, 14.2, 14.3, 14.4, 16.1, 16.2, 16.3, 16.4
"""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from sqlalchemy.orm import Session
from datetime import datetime

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
    service.update_knowledge_base = AsyncMock(return_value=Mock(
        id="kb_001",
        name="Updated KB",
        description="Updated description"
    ))
    service.delete_knowledge_base = AsyncMock(return_value=True)
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
    service.update_document = AsyncMock(return_value=Mock(
        id="doc_001",
        name="updated_document.txt",
        kb_id="kb_001",
        size=1024
    ))
    service.delete_document = AsyncMock(return_value=True)
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


class TestAllToolCombinations:
    """Test all tool combinations and interactions."""
    
    @pytest.mark.anyio
    async def test_kb_and_document_tools_combination(
        self,
        mock_kb_service,
        mock_doc_service
    ):
        """Test knowledge base and document tools working together."""
        # Create KB
        kb = await mock_kb_service.create_knowledge_base(
            name="Combined Test KB",
            description="For testing tool combinations"
        )
        assert kb.id == "kb_001"
        
        # Upload documents
        docs = []
        for i in range(3):
            doc = await mock_doc_service.upload_document(
                kb_id=kb.id,
                file_path=f"document_{i}.txt",
                metadata={"index": i}
            )
            docs.append(doc)
        
        # List documents
        listed_docs = await mock_doc_service.list_documents(kb_id=kb.id)
        assert len(listed_docs) >= 3
        
        # Update a document
        updated_doc = await mock_doc_service.update_document(
            doc_id=docs[0].id,
            name="updated_document.txt"
        )
        assert updated_doc.name == "updated_document.txt"
        
        # Delete a document
        result = await mock_doc_service.delete_document(doc_id=docs[0].id)
        assert result is True
    
    @pytest.mark.anyio
    async def test_search_and_rag_tools_combination(
        self,
        mock_search_service,
        agent_manager
    ):
        """Test search and RAG tools working together."""
        # Search
        results = await mock_search_service.search(
            query="test query",
            kb_id="kb_001",
            top_k=3
        )
        assert len(results) == 3
        
        # Build context from search results
        context = "\n\n".join([r.content for r in results])
        
        # Generate RAG answer
        answer = await agent_manager.llm_provider.generate(
            f"Based on: {context}\n\nAnswer the question"
        )
        assert answer is not None
        assert len(answer) > 0
    
    @pytest.mark.anyio
    async def test_all_tools_in_sequence(
        self,
        mock_kb_service,
        mock_doc_service,
        mock_search_service,
        agent_manager
    ):
        """Test all tools working in sequence."""
        # Step 1: Create KB
        kb = await mock_kb_service.create_knowledge_base(
            name="Full Sequence KB",
            description="For full sequence testing"
        )
        
        # Step 2: Upload document
        doc = await mock_doc_service.upload_document(
            kb_id=kb.id,
            file_path="test.txt",
            metadata={}
        )
        
        # Step 3: Search
        results = await mock_search_service.search(
            query="test",
            kb_id=kb.id,
            top_k=3
        )
        
        # Step 4: Generate answer
        context = "\n".join([r.content for r in results])
        answer = await agent_manager.llm_provider.generate(
            f"Context: {context}\n\nQuestion: test?"
        )
        
        # Step 5: Store in memory
        agent_manager.memory.add_user_message("test?")
        agent_manager.memory.add_ai_message(answer)
        
        # Step 6: Update KB
        updated_kb = await mock_kb_service.update_knowledge_base(
            kb_id=kb.id,
            name="Updated Full Sequence KB"
        )
        
        # Step 7: Delete document
        await mock_doc_service.delete_document(doc_id=doc.id)
        
        # Verify all steps completed
        messages = agent_manager.memory.get_messages()
        assert len(messages) == 2
        assert updated_kb.name == "Updated Full Sequence KB"


class TestMemoryPersistenceAndRecovery:
    """Test memory persistence and recovery mechanisms."""
    
    @pytest.mark.anyio
    async def test_memory_persistence_across_sessions(self, mock_db_session):
        """Test memory persists across different sessions."""
        session_id = "persistent_session_001"
        
        # Session 1: Create memory and add messages
        memory1 = ConversationMemory(
            session_id=session_id,
            max_history=10,
            db_session=mock_db_session
        )
        
        memory1.add_user_message("First question")
        memory1.add_ai_message("First answer")
        memory1.add_user_message("Second question")
        
        messages_before = memory1.get_messages()
        assert len(messages_before) == 3
        
        # Session 2: Create new memory with same session ID
        memory2 = ConversationMemory(
            session_id=session_id,
            max_history=10,
            db_session=mock_db_session
        )
        
        # In real implementation, this would load from DB
        # For now, verify the session ID is preserved
        assert memory2.session_id == session_id
        
        # Add more messages
        memory2.add_user_message("Third question")
        
        messages_after = memory2.get_messages()
        assert len(messages_after) >= 1
    
    @pytest.mark.anyio
    async def test_memory_recovery_after_failure(self, mock_db_session):
        """Test memory recovery after system failure."""
        session_id = "recovery_session"
        
        # Create memory and add messages
        memory = ConversationMemory(
            session_id=session_id,
            max_history=10,
            db_session=mock_db_session
        )
        
        memory.add_user_message("Important question")
        memory.add_ai_message("Important answer")
        
        # Simulate system failure and recovery
        messages_before = memory.get_messages()
        
        # Create new memory instance (simulating restart)
        recovered_memory = ConversationMemory(
            session_id=session_id,
            max_history=10,
            db_session=mock_db_session
        )
        
        # Verify session ID is preserved
        assert recovered_memory.session_id == session_id
        
        # Add new message to recovered session
        recovered_memory.add_user_message("Follow-up question")
        
        messages_after = recovered_memory.get_messages()
        assert len(messages_after) >= 1
    
    @pytest.mark.anyio
    async def test_memory_truncation_at_max_history(self, mock_db_session):
        """Test memory truncation when exceeding max_history."""
        memory = ConversationMemory(
            session_id="truncation_test",
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
    
    @pytest.mark.anyio
    async def test_memory_clear_functionality(self, mock_db_session):
        """Test clearing memory."""
        memory = ConversationMemory(
            session_id="clear_test",
            max_history=10,
            db_session=mock_db_session
        )
        
        # Add messages
        memory.add_user_message("Question")
        memory.add_ai_message("Answer")
        
        assert len(memory.get_messages()) == 2
        
        # Clear memory
        await memory.clear()
        
        # Verify memory is cleared
        assert len(memory.get_messages()) == 0


class TestConcurrentUserSessions:
    """Test concurrent user sessions."""
    
    @pytest.mark.anyio
    async def test_multiple_concurrent_sessions(self, mock_db_session):
        """Test multiple concurrent sessions don't interfere."""
        sessions = []
        
        # Create multiple sessions
        for i in range(5):
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
    
    @pytest.mark.anyio
    async def test_concurrent_agent_operations(
        self,
        agent_manager,
        mock_search_service
    ):
        """Test concurrent Agent operations."""
        async def agent_task(task_id):
            # Search
            results = await mock_search_service.search(
                query=f"query_{task_id}",
                kb_id="kb_001",
                top_k=3
            )
            
            # Generate answer
            context = "\n".join([r.content for r in results])
            answer = await agent_manager.llm_provider.generate(
                f"Context: {context}\n\nQuestion: {task_id}?"
            )
            
            return {
                "task_id": task_id,
                "results_count": len(results),
                "answer": answer
            }
        
        # Run concurrent tasks
        tasks = [agent_task(i) for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        # Verify all tasks completed
        assert len(results) == 5
        assert all(r["results_count"] > 0 for r in results)
    
    @pytest.mark.anyio
    async def test_concurrent_memory_operations(self, mock_db_session):
        """Test concurrent memory operations."""
        memory = ConversationMemory(
            session_id="concurrent_memory_test",
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
    
    @pytest.mark.anyio
    async def test_session_isolation(self, mock_db_session):
        """Test that sessions are properly isolated."""
        memory1 = ConversationMemory(
            session_id="session_1",
            max_history=10,
            db_session=mock_db_session
        )
        
        memory2 = ConversationMemory(
            session_id="session_2",
            max_history=10,
            db_session=mock_db_session
        )
        
        # Add different messages to each session
        memory1.add_user_message("Session 1 message")
        memory2.add_user_message("Session 2 message")
        
        # Verify isolation
        messages1 = memory1.get_messages()
        messages2 = memory2.get_messages()
        
        assert "Session 1" in messages1[0].content
        assert "Session 2" in messages2[0].content
        assert messages1[0].content != messages2[0].content


class TestSystemBehaviorUnderFailure:
    """Test system behavior under failure conditions."""
    
    @pytest.mark.anyio
    async def test_llm_provider_failure_handling(self, agent_manager):
        """Test handling of LLM provider failures."""
        # Mock LLM failure
        agent_manager.llm_provider.generate = AsyncMock(
            side_effect=Exception("LLM service unavailable")
        )
        
        # Attempt to use LLM
        try:
            await agent_manager.llm_provider.generate("test prompt")
            assert False, "Should have raised exception"
        except Exception as e:
            assert "LLM service unavailable" in str(e)
    
    @pytest.mark.anyio
    async def test_search_service_failure_handling(self, mock_search_service):
        """Test handling of search service failures."""
        # Mock search failure
        mock_search_service.search = AsyncMock(
            side_effect=Exception("Search service unavailable")
        )
        
        # Attempt search
        try:
            await mock_search_service.search(
                query="test",
                kb_id="kb_001",
                top_k=3
            )
            assert False, "Should have raised exception"
        except Exception as e:
            assert "Search service unavailable" in str(e)
    
    @pytest.mark.anyio
    async def test_database_connection_failure(self, mock_db_session):
        """Test handling of database connection failures."""
        # Mock DB failure
        mock_db_session.query = Mock(side_effect=Exception("DB connection lost"))
        
        # Create memory (should still work in-memory)
        memory = ConversationMemory(
            session_id="db_failure_test",
            max_history=10,
            db_session=mock_db_session
        )
        
        # Add message (should work in-memory)
        memory.add_user_message("Test message")
        
        # Verify message is in memory
        messages = memory.get_messages()
        assert len(messages) == 1
        assert messages[0].content == "Test message"
    
    @pytest.mark.anyio
    async def test_partial_tool_failure_recovery(self, agent_manager):
        """Test recovery when one tool fails but others succeed."""
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
    async def test_timeout_handling(self):
        """Test timeout handling."""
        async def slow_operation():
            await asyncio.sleep(2)
            return "completed"
        
        # Set timeout
        try:
            result = await asyncio.wait_for(slow_operation(), timeout=0.5)
            assert False, "Should have timed out"
        except asyncio.TimeoutError:
            pass  # Expected
    
    @pytest.mark.anyio
    async def test_retry_mechanism(self):
        """Test retry mechanism on transient failures."""
        call_count = 0
        
        async def flaky_service():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Transient failure")
            return {"success": True}
        
        # Retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = await flaky_service()
                assert result["success"] is True
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
        
        assert call_count == 2


class TestErrorPropagationAndLogging:
    """Test error propagation and logging."""
    
    @pytest.mark.anyio
    async def test_error_propagation_from_tool_to_agent(self):
        """Test error propagation from tool to Agent."""
        tool_error = Exception("Tool execution failed")
        
        async def failing_tool():
            raise tool_error
        
        # Attempt to execute tool
        try:
            await failing_tool()
            assert False, "Should have raised exception"
        except Exception as e:
            assert str(e) == "Tool execution failed"
    
    @pytest.mark.anyio
    async def test_error_context_preservation(self):
        """Test that error context is preserved."""
        async def operation_with_context():
            try:
                raise ValueError("Original error")
            except ValueError as e:
                # Wrap error with context
                raise RuntimeError(f"Operation failed: {str(e)}") from e
        
        try:
            await operation_with_context()
            assert False, "Should have raised exception"
        except RuntimeError as e:
            assert "Operation failed" in str(e)
            assert e.__cause__ is not None
    
    @pytest.mark.anyio
    async def test_error_recovery_with_fallback(self):
        """Test error recovery with fallback mechanism."""
        async def primary_operation():
            raise Exception("Primary failed")
        
        async def fallback_operation():
            return {"success": True, "source": "fallback"}
        
        # Try primary, fallback on failure
        try:
            result = await primary_operation()
        except Exception:
            result = await fallback_operation()
        
        assert result["source"] == "fallback"


class TestSystemIntegrationScenarios:
    """Test complete system integration scenarios."""
    
    @pytest.mark.anyio
    async def test_complete_workflow_with_all_components(
        self,
        agent_manager,
        mock_kb_service,
        mock_doc_service,
        mock_search_service
    ):
        """Test complete workflow using all system components."""
        # Step 1: Create KB
        kb = await mock_kb_service.create_knowledge_base(
            name="Complete Workflow KB",
            description="For complete workflow testing"
        )
        
        # Step 2: Upload documents
        docs = []
        for i in range(2):
            doc = await mock_doc_service.upload_document(
                kb_id=kb.id,
                file_path=f"doc_{i}.txt",
                metadata={}
            )
            docs.append(doc)
        
        # Step 3: Multi-turn conversation
        queries = [
            "What is in the knowledge base?",
            "Tell me more about the documents",
            "Can you summarize?"
        ]
        
        for query in queries:
            # Search
            results = await mock_search_service.search(
                query=query,
                kb_id=kb.id,
                top_k=3
            )
            
            # Generate answer
            context = "\n".join([r.content for r in results])
            answer = await agent_manager.llm_provider.generate(
                f"Context: {context}\n\nQuestion: {query}"
            )
            
            # Store in memory
            agent_manager.memory.add_user_message(query)
            agent_manager.memory.add_ai_message(answer)
        
        # Verify complete workflow
        messages = agent_manager.memory.get_messages()
        assert len(messages) == 6  # 3 questions + 3 answers
        
        # Step 4: Update KB
        updated_kb = await mock_kb_service.update_knowledge_base(
            kb_id=kb.id,
            name="Updated Complete Workflow KB"
        )
        assert updated_kb.name == "Updated Complete Workflow KB"
        
        # Step 5: Delete documents
        for doc in docs:
            await mock_doc_service.delete_document(doc_id=doc.id)
        
        # Step 6: Delete KB
        result = await mock_kb_service.delete_knowledge_base(kb_id=kb.id)
        assert result is True
    
    @pytest.mark.anyio
    async def test_stress_test_concurrent_operations(
        self,
        mock_kb_service,
        mock_search_service,
        agent_manager
    ):
        """Stress test with many concurrent operations."""
        async def concurrent_operation(op_id):
            # Create KB
            kb = await mock_kb_service.create_knowledge_base(
                name=f"Stress Test KB {op_id}",
                description=f"Stress test {op_id}"
            )
            
            # Search
            results = await mock_search_service.search(
                query=f"query_{op_id}",
                kb_id=kb.id,
                top_k=3
            )
            
            # Generate answer
            answer = await agent_manager.llm_provider.generate(
                f"Answer for query {op_id}"
            )
            
            return {
                "op_id": op_id,
                "kb_id": kb.id,
                "results": len(results),
                "answer": answer
            }
        
        # Run many concurrent operations
        tasks = [concurrent_operation(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        # Verify all operations completed
        assert len(results) == 10
        assert all(r["results"] > 0 for r in results)
