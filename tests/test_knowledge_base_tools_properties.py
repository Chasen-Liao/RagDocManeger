"""Property-based tests for knowledge base management tools.

This module contains property-based tests using Hypothesis to verify that
the knowledge base management tools maintain correctness properties across
different inputs.

**Validates: Requirements 6.1, 6.2, 6.4**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import uuid

from tools.knowledge_base_tools import (
    CreateKnowledgeBaseTool,
    GetKnowledgeBaseTool,
    DeleteKnowledgeBaseTool,
)
from models.schemas import KnowledgeBaseResponse
from exceptions import ResourceNotFoundError


# Hypothesis strategies for generating test data
kb_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Zs")),
    min_size=1,
    max_size=100
).filter(lambda x: len(x.strip()) > 0)

kb_description_strategy = st.one_of(
    st.none(),
    st.text(min_size=0, max_size=500)
)

kb_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
    min_size=5,
    max_size=50
).map(lambda x: f"kb_{x}" if x else f"kb_{uuid.uuid4().hex[:10]}")


def create_mock_kb_response(
    kb_id: str,
    name: str,
    description: str = None,
    document_count: int = 0,
    total_size: int = 0
) -> KnowledgeBaseResponse:
    """Helper function to create mock knowledge base responses."""
    return KnowledgeBaseResponse(
        id=kb_id,
        name=name,
        description=description,
        document_count=document_count,
        total_size=total_size,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


class TestCreateThenGetConsistency:
    """
    Property 4: Create-then-Get Consistency
    
    **Validates: Requirements 6.1, 6.4**
    
    Tests that a knowledge base created with certain properties can be
    retrieved with the same properties. This verifies the consistency
    of the create and get operations.
    """

    @pytest.mark.asyncio
    @given(
        kb_name=kb_name_strategy,
        kb_description=kb_description_strategy
    )
    @settings(max_examples=50, deadline=None)
    async def test_created_kb_can_be_retrieved_with_same_properties(
        self,
        kb_name,
        kb_description
    ):
        """
        Property: Created knowledge base should be retrievable with same properties.
        
        This test verifies that after creating a knowledge base, we can retrieve
        it and the properties match what was used during creation.
        """
        assume(len(kb_name.strip()) > 0)
        
        # Generate a unique KB ID
        kb_id = f"kb_{uuid.uuid4().hex[:10]}"
        
        # Create mock database session
        mock_db = MagicMock()
        
        # Create the expected response
        expected_response = create_mock_kb_response(
            kb_id=kb_id,
            name=kb_name,
            description=kb_description
        )
        
        # Mock the service methods
        with patch(
            'tools.knowledge_base_tools.KnowledgeBaseService.create_knowledge_base',
            new_callable=AsyncMock,
            return_value=expected_response
        ) as mock_create, patch(
            'tools.knowledge_base_tools.KnowledgeBaseService.get_knowledge_base',
            new_callable=AsyncMock,
            return_value=expected_response
        ) as mock_get:
            # Create knowledge base
            create_tool = CreateKnowledgeBaseTool(db_session=mock_db)
            create_result = await create_tool._aexecute(
                kb_name=kb_name,
                description=kb_description
            )
            
            # Verify creation succeeded
            assert create_result.success is True, \
                "Knowledge base creation should succeed"
            assert create_result.data["kb_id"] == kb_id, \
                "Created KB ID should match"
            assert create_result.data["kb_name"] == kb_name, \
                "Created KB name should match input"
            
            # Get knowledge base
            get_tool = GetKnowledgeBaseTool(db_session=mock_db)
            get_result = await get_tool._aexecute(kb_id=kb_id)
            
            # Verify retrieval succeeded
            assert get_result.success is True, \
                "Knowledge base retrieval should succeed"
            
            # Verify properties match
            assert get_result.data["kb_id"] == create_result.data["kb_id"], \
                "Retrieved KB ID should match created KB ID"
            assert get_result.data["kb_name"] == create_result.data["kb_name"], \
                "Retrieved KB name should match created KB name"
            assert get_result.data["description"] == create_result.data["description"], \
                "Retrieved KB description should match created KB description"

    @pytest.mark.asyncio
    @given(kb_name=kb_name_strategy)
    @settings(max_examples=50, deadline=None)
    async def test_created_kb_without_description_can_be_retrieved(self, kb_name):
        """
        Property: Knowledge base created without description is retrievable.
        
        This verifies that optional fields (like description) don't affect
        the create-then-get consistency.
        """
        assume(len(kb_name.strip()) > 0)
        
        kb_id = f"kb_{uuid.uuid4().hex[:10]}"
        mock_db = MagicMock()
        
        # Create response without description
        expected_response = create_mock_kb_response(
            kb_id=kb_id,
            name=kb_name,
            description=None
        )
        
        with patch(
            'tools.knowledge_base_tools.KnowledgeBaseService.create_knowledge_base',
            new_callable=AsyncMock,
            return_value=expected_response
        ), patch(
            'tools.knowledge_base_tools.KnowledgeBaseService.get_knowledge_base',
            new_callable=AsyncMock,
            return_value=expected_response
        ):
            # Create without description
            create_tool = CreateKnowledgeBaseTool(db_session=mock_db)
            create_result = await create_tool._aexecute(kb_name=kb_name)
            
            assert create_result.success is True
            assert create_result.data["description"] is None
            
            # Get and verify
            get_tool = GetKnowledgeBaseTool(db_session=mock_db)
            get_result = await get_tool._aexecute(kb_id=kb_id)
            
            assert get_result.success is True
            assert get_result.data["kb_id"] == kb_id
            assert get_result.data["kb_name"] == kb_name
            assert get_result.data["description"] is None

    @pytest.mark.asyncio
    @given(
        kb_name=kb_name_strategy,
        kb_description=kb_description_strategy,
        document_count=st.integers(min_value=0, max_value=1000),
        total_size=st.integers(min_value=0, max_value=1000000)
    )
    @settings(max_examples=30, deadline=None)
    async def test_retrieved_kb_includes_all_metadata(
        self,
        kb_name,
        kb_description,
        document_count,
        total_size
    ):
        """
        Property: Retrieved knowledge base includes all metadata fields.
        
        This verifies that the get operation returns complete information
        including statistics like document count and total size.
        """
        assume(len(kb_name.strip()) > 0)
        
        kb_id = f"kb_{uuid.uuid4().hex[:10]}"
        mock_db = MagicMock()
        
        # Create response with metadata
        expected_response = create_mock_kb_response(
            kb_id=kb_id,
            name=kb_name,
            description=kb_description,
            document_count=document_count,
            total_size=total_size
        )
        
        with patch(
            'tools.knowledge_base_tools.KnowledgeBaseService.create_knowledge_base',
            new_callable=AsyncMock,
            return_value=expected_response
        ), patch(
            'tools.knowledge_base_tools.KnowledgeBaseService.get_knowledge_base',
            new_callable=AsyncMock,
            return_value=expected_response
        ):
            # Create knowledge base
            create_tool = CreateKnowledgeBaseTool(db_session=mock_db)
            create_result = await create_tool._aexecute(
                kb_name=kb_name,
                description=kb_description
            )
            
            assert create_result.success is True
            
            # Get knowledge base
            get_tool = GetKnowledgeBaseTool(db_session=mock_db)
            get_result = await get_tool._aexecute(kb_id=kb_id)
            
            # Verify all metadata is present
            assert get_result.success is True
            assert "kb_id" in get_result.data
            assert "kb_name" in get_result.data
            assert "description" in get_result.data
            assert "document_count" in get_result.data
            assert "total_size" in get_result.data
            assert "created_at" in get_result.data
            assert "updated_at" in get_result.data
            
            # Verify metadata values
            assert get_result.data["document_count"] == document_count
            assert get_result.data["total_size"] == total_size


class TestDeleteIdempotency:
    """
    Property 5: Delete Idempotency
    
    **Validates: Requirement 6.2**
    
    Tests that deleting a non-existent knowledge base does not cause errors.
    This verifies that the delete operation is idempotent and handles
    missing resources gracefully.
    """

    @pytest.mark.asyncio
    @given(kb_id=kb_id_strategy)
    @settings(max_examples=50, deadline=None)
    async def test_deleting_nonexistent_kb_does_not_error(self, kb_id):
        """
        Property: Deleting non-existent knowledge base should not raise error.
        
        This test verifies that the delete operation is idempotent - attempting
        to delete a knowledge base that doesn't exist should fail gracefully
        without raising an exception.
        """
        assume(len(kb_id.strip()) > 0)
        
        mock_db = MagicMock()
        
        # Mock the service to raise ResourceNotFoundError
        with patch(
            'tools.knowledge_base_tools.KnowledgeBaseService.delete_knowledge_base',
            new_callable=AsyncMock,
            side_effect=ResourceNotFoundError(f"Knowledge base not found: {kb_id}")
        ):
            # Attempt to delete non-existent KB
            delete_tool = DeleteKnowledgeBaseTool(db_session=mock_db)
            result = await delete_tool._aexecute(kb_id=kb_id)
            
            # Should not raise exception, but return error result
            assert result.success is False, \
                "Deleting non-existent KB should return failure"
            assert result.error is not None, \
                "Error message should be present"
            assert "not found" in result.error.lower(), \
                "Error should indicate KB was not found"
            assert "not found" in result.message.lower(), \
                "Message should indicate KB was not found"

    @pytest.mark.asyncio
    @given(kb_id=kb_id_strategy)
    @settings(max_examples=50, deadline=None)
    async def test_delete_returns_consistent_error_format(self, kb_id):
        """
        Property: Delete operation returns consistent error format.
        
        This verifies that error responses have a consistent structure
        regardless of the specific error.
        """
        assume(len(kb_id.strip()) > 0)
        
        mock_db = MagicMock()
        
        with patch(
            'tools.knowledge_base_tools.KnowledgeBaseService.delete_knowledge_base',
            new_callable=AsyncMock,
            side_effect=ResourceNotFoundError(f"Knowledge base not found: {kb_id}")
        ):
            delete_tool = DeleteKnowledgeBaseTool(db_session=mock_db)
            result = await delete_tool._aexecute(kb_id=kb_id)
            
            # Verify error response structure
            assert hasattr(result, 'success'), \
                "Result should have 'success' attribute"
            assert hasattr(result, 'message'), \
                "Result should have 'message' attribute"
            assert hasattr(result, 'error'), \
                "Result should have 'error' attribute"
            assert hasattr(result, 'data'), \
                "Result should have 'data' attribute"
            
            assert result.success is False
            assert isinstance(result.message, str)
            assert isinstance(result.error, str)

    @pytest.mark.asyncio
    @given(
        kb_name=kb_name_strategy,
        kb_description=kb_description_strategy
    )
    @settings(max_examples=30, deadline=None)
    async def test_delete_after_create_succeeds(self, kb_name, kb_description):
        """
        Property: Deleting an existing knowledge base succeeds.
        
        This verifies that delete works correctly for knowledge bases
        that actually exist.
        """
        assume(len(kb_name.strip()) > 0)
        
        kb_id = f"kb_{uuid.uuid4().hex[:10]}"
        mock_db = MagicMock()
        
        # Create response
        create_response = create_mock_kb_response(
            kb_id=kb_id,
            name=kb_name,
            description=kb_description
        )
        
        with patch(
            'tools.knowledge_base_tools.KnowledgeBaseService.create_knowledge_base',
            new_callable=AsyncMock,
            return_value=create_response
        ), patch(
            'tools.knowledge_base_tools.KnowledgeBaseService.delete_knowledge_base',
            new_callable=AsyncMock,
            return_value=None
        ):
            # Create knowledge base
            create_tool = CreateKnowledgeBaseTool(db_session=mock_db)
            create_result = await create_tool._aexecute(
                kb_name=kb_name,
                description=kb_description
            )
            
            assert create_result.success is True
            created_kb_id = create_result.data["kb_id"]
            
            # Delete knowledge base
            delete_tool = DeleteKnowledgeBaseTool(db_session=mock_db)
            delete_result = await delete_tool._aexecute(kb_id=created_kb_id)
            
            # Verify deletion succeeded
            assert delete_result.success is True, \
                "Deleting existing KB should succeed"
            assert delete_result.data["kb_id"] == created_kb_id, \
                "Deleted KB ID should match"
            assert delete_result.data["deleted"] is True, \
                "Deleted flag should be True"

    @pytest.mark.asyncio
    @given(kb_id=kb_id_strategy)
    @settings(max_examples=30, deadline=None)
    async def test_multiple_delete_attempts_are_safe(self, kb_id):
        """
        Property: Multiple delete attempts on same KB are safe.
        
        This verifies true idempotency - calling delete multiple times
        on the same (non-existent) KB should always return the same result.
        """
        assume(len(kb_id.strip()) > 0)
        
        mock_db = MagicMock()
        
        with patch(
            'tools.knowledge_base_tools.KnowledgeBaseService.delete_knowledge_base',
            new_callable=AsyncMock,
            side_effect=ResourceNotFoundError(f"Knowledge base not found: {kb_id}")
        ):
            delete_tool = DeleteKnowledgeBaseTool(db_session=mock_db)
            
            # Attempt delete multiple times
            result1 = await delete_tool._aexecute(kb_id=kb_id)
            result2 = await delete_tool._aexecute(kb_id=kb_id)
            result3 = await delete_tool._aexecute(kb_id=kb_id)
            
            # All attempts should return consistent results
            assert result1.success == result2.success == result3.success == False
            assert all("not found" in r.error.lower() for r in [result1, result2, result3])


class TestToolOutputConsistency:
    """
    Additional property tests for tool output consistency.
    
    These tests verify that tools maintain consistent output formats
    and behavior across different scenarios.
    """

    @pytest.mark.asyncio
    @given(
        kb_name=kb_name_strategy,
        kb_description=kb_description_strategy
    )
    @settings(max_examples=30, deadline=None)
    async def test_successful_operations_always_have_data(
        self,
        kb_name,
        kb_description
    ):
        """
        Property: Successful operations always include data in response.
        
        This verifies that success responses are complete and useful.
        """
        assume(len(kb_name.strip()) > 0)
        
        kb_id = f"kb_{uuid.uuid4().hex[:10]}"
        mock_db = MagicMock()
        
        create_response = create_mock_kb_response(
            kb_id=kb_id,
            name=kb_name,
            description=kb_description
        )
        
        with patch(
            'tools.knowledge_base_tools.KnowledgeBaseService.create_knowledge_base',
            new_callable=AsyncMock,
            return_value=create_response
        ), patch(
            'tools.knowledge_base_tools.KnowledgeBaseService.get_knowledge_base',
            new_callable=AsyncMock,
            return_value=create_response
        ):
            # Test create
            create_tool = CreateKnowledgeBaseTool(db_session=mock_db)
            create_result = await create_tool._aexecute(
                kb_name=kb_name,
                description=kb_description
            )
            
            assert create_result.success is True
            assert create_result.data is not None
            assert len(create_result.data) > 0
            assert create_result.error is None
            
            # Test get
            get_tool = GetKnowledgeBaseTool(db_session=mock_db)
            get_result = await get_tool._aexecute(kb_id=kb_id)
            
            assert get_result.success is True
            assert get_result.data is not None
            assert len(get_result.data) > 0
            assert get_result.error is None

    @pytest.mark.asyncio
    @given(kb_id=kb_id_strategy)
    @settings(max_examples=30, deadline=None)
    async def test_failed_operations_always_have_error_message(self, kb_id):
        """
        Property: Failed operations always include error information.
        
        This verifies that error responses are informative.
        """
        assume(len(kb_id.strip()) > 0)
        
        mock_db = MagicMock()
        
        with patch(
            'tools.knowledge_base_tools.KnowledgeBaseService.get_knowledge_base',
            new_callable=AsyncMock,
            side_effect=ResourceNotFoundError(f"Knowledge base not found: {kb_id}")
        ), patch(
            'tools.knowledge_base_tools.KnowledgeBaseService.delete_knowledge_base',
            new_callable=AsyncMock,
            side_effect=ResourceNotFoundError(f"Knowledge base not found: {kb_id}")
        ):
            # Test get failure
            get_tool = GetKnowledgeBaseTool(db_session=mock_db)
            get_result = await get_tool._aexecute(kb_id=kb_id)
            
            assert get_result.success is False
            assert get_result.error is not None
            assert len(get_result.error) > 0
            assert get_result.message is not None
            assert len(get_result.message) > 0
            
            # Test delete failure
            delete_tool = DeleteKnowledgeBaseTool(db_session=mock_db)
            delete_result = await delete_tool._aexecute(kb_id=kb_id)
            
            assert delete_result.success is False
            assert delete_result.error is not None
            assert len(delete_result.error) > 0
            assert delete_result.message is not None
            assert len(delete_result.message) > 0

    @pytest.mark.asyncio
    @given(
        kb_name=kb_name_strategy,
        kb_description=kb_description_strategy
    )
    @settings(max_examples=30, deadline=None)
    async def test_tool_output_has_consistent_structure(
        self,
        kb_name,
        kb_description
    ):
        """
        Property: All tool outputs have consistent structure.
        
        This verifies that all tools follow the same output format.
        """
        assume(len(kb_name.strip()) > 0)
        
        kb_id = f"kb_{uuid.uuid4().hex[:10]}"
        mock_db = MagicMock()
        
        create_response = create_mock_kb_response(
            kb_id=kb_id,
            name=kb_name,
            description=kb_description
        )
        
        with patch(
            'tools.knowledge_base_tools.KnowledgeBaseService.create_knowledge_base',
            new_callable=AsyncMock,
            return_value=create_response
        ), patch(
            'tools.knowledge_base_tools.KnowledgeBaseService.get_knowledge_base',
            new_callable=AsyncMock,
            return_value=create_response
        ), patch(
            'tools.knowledge_base_tools.KnowledgeBaseService.delete_knowledge_base',
            new_callable=AsyncMock,
            return_value=None
        ):
            # Test all tools
            create_tool = CreateKnowledgeBaseTool(db_session=mock_db)
            get_tool = GetKnowledgeBaseTool(db_session=mock_db)
            delete_tool = DeleteKnowledgeBaseTool(db_session=mock_db)
            
            create_result = await create_tool._aexecute(
                kb_name=kb_name,
                description=kb_description
            )
            get_result = await get_tool._aexecute(kb_id=kb_id)
            delete_result = await delete_tool._aexecute(kb_id=kb_id)
            
            # All results should have the same attributes
            for result in [create_result, get_result, delete_result]:
                assert hasattr(result, 'success')
                assert hasattr(result, 'message')
                assert hasattr(result, 'data')
                assert hasattr(result, 'error')
                assert isinstance(result.success, bool)
                assert isinstance(result.message, str)
