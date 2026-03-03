"""
Tests for Knowledge Base Management Tools

This module tests the knowledge base management tools:
- CreateKnowledgeBaseTool
- ListKnowledgeBasesTool
- GetKnowledgeBaseTool
- UpdateKnowledgeBaseTool
- DeleteKnowledgeBaseTool
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from tools.knowledge_base_tools import (
    CreateKnowledgeBaseTool,
    ListKnowledgeBasesTool,
    GetKnowledgeBaseTool,
    UpdateKnowledgeBaseTool,
    DeleteKnowledgeBaseTool,
)
from models.schemas import KnowledgeBaseResponse
from exceptions import ResourceNotFoundError, ConflictError


@pytest.fixture
def mock_db_session():
    """Create a mock database session"""
    return MagicMock()


@pytest.fixture
def sample_kb_response():
    """Create a sample knowledge base response"""
    return KnowledgeBaseResponse(
        id="kb_test123",
        name="Test KB",
        description="Test description",
        document_count=5,
        total_size=1024,
        created_at=datetime(2024, 1, 1, 12, 0, 0),
        updated_at=datetime(2024, 1, 1, 12, 0, 0)
    )


class TestCreateKnowledgeBaseTool:
    """Test CreateKnowledgeBaseTool"""
    
    @pytest.mark.asyncio
    async def test_create_knowledge_base_success(self, mock_db_session, sample_kb_response):
        """Test successful knowledge base creation"""
        tool = CreateKnowledgeBaseTool(db_session=mock_db_session)
        
        with patch(
            'tools.knowledge_base_tools.KnowledgeBaseService.create_knowledge_base',
            new_callable=AsyncMock,
            return_value=sample_kb_response
        ):
            result = await tool._aexecute(
                kb_name="Test KB",
                description="Test description"
            )
        
        assert result.success is True
        assert "Successfully created knowledge base" in result.message
        assert result.data["kb_id"] == "kb_test123"
        assert result.data["kb_name"] == "Test KB"
        assert result.error is None
    
    @pytest.mark.asyncio
    async def test_create_knowledge_base_without_description(self, mock_db_session, sample_kb_response):
        """Test creating knowledge base without description"""
        tool = CreateKnowledgeBaseTool(db_session=mock_db_session)
        
        with patch(
            'tools.knowledge_base_tools.KnowledgeBaseService.create_knowledge_base',
            new_callable=AsyncMock,
            return_value=sample_kb_response
        ):
            result = await tool._aexecute(kb_name="Test KB")
        
        assert result.success is True
        assert result.data["kb_name"] == "Test KB"
    
    @pytest.mark.asyncio
    async def test_create_knowledge_base_conflict(self, mock_db_session):
        """Test creating knowledge base with duplicate name"""
        tool = CreateKnowledgeBaseTool(db_session=mock_db_session)
        
        with patch(
            'tools.knowledge_base_tools.KnowledgeBaseService.create_knowledge_base',
            new_callable=AsyncMock,
            side_effect=ConflictError("Knowledge base with name 'Test KB' already exists")
        ):
            result = await tool._aexecute(kb_name="Test KB")
        
        assert result.success is False
        assert "name already exists" in result.message
        assert "already exists" in result.error
    
    @pytest.mark.asyncio
    async def test_create_knowledge_base_generic_error(self, mock_db_session):
        """Test handling generic errors during creation"""
        tool = CreateKnowledgeBaseTool(db_session=mock_db_session)
        
        with patch(
            'tools.knowledge_base_tools.KnowledgeBaseService.create_knowledge_base',
            new_callable=AsyncMock,
            side_effect=Exception("Database error")
        ):
            result = await tool._aexecute(kb_name="Test KB")
        
        assert result.success is False
        assert "Failed to create knowledge base" in result.message
        assert "Database error" in result.error
    
    def test_tool_metadata(self, mock_db_session):
        """Test tool metadata is correctly set"""
        tool = CreateKnowledgeBaseTool(db_session=mock_db_session)
        
        assert tool.name == "create_knowledge_base"
        assert "Create a new knowledge base" in tool.description
        assert tool.args_schema is not None


class TestListKnowledgeBasesTool:
    """Test ListKnowledgeBasesTool"""
    
    @pytest.mark.asyncio
    async def test_list_knowledge_bases_success(self, mock_db_session):
        """Test successful listing of knowledge bases"""
        tool = ListKnowledgeBasesTool(db_session=mock_db_session)
        
        kb_list = [
            KnowledgeBaseResponse(
                id=f"kb_test{i}",
                name=f"Test KB {i}",
                description=f"Description {i}",
                document_count=i,
                total_size=1024 * i,
                created_at=datetime(2024, 1, 1, 12, 0, 0),
                updated_at=datetime(2024, 1, 1, 12, 0, 0)
            )
            for i in range(1, 4)
        ]
        
        with patch(
            'tools.knowledge_base_tools.KnowledgeBaseService.get_knowledge_bases',
            new_callable=AsyncMock,
            return_value=(kb_list, 3)
        ):
            result = await tool._aexecute(skip=0, limit=20)
        
        assert result.success is True
        assert "Found 3 knowledge base(s)" in result.message
        assert len(result.data["knowledge_bases"]) == 3
        assert result.data["total"] == 3
        assert result.data["skip"] == 0
        assert result.data["limit"] == 20
    
    @pytest.mark.asyncio
    async def test_list_knowledge_bases_empty(self, mock_db_session):
        """Test listing when no knowledge bases exist"""
        tool = ListKnowledgeBasesTool(db_session=mock_db_session)
        
        with patch(
            'tools.knowledge_base_tools.KnowledgeBaseService.get_knowledge_bases',
            new_callable=AsyncMock,
            return_value=([], 0)
        ):
            result = await tool._aexecute()
        
        assert result.success is True
        assert "No knowledge bases found" in result.message
        assert len(result.data["knowledge_bases"]) == 0
        assert result.data["total"] == 0
    
    @pytest.mark.asyncio
    async def test_list_knowledge_bases_with_pagination(self, mock_db_session):
        """Test listing with pagination parameters"""
        tool = ListKnowledgeBasesTool(db_session=mock_db_session)
        
        kb_list = [
            KnowledgeBaseResponse(
                id="kb_test1",
                name="Test KB 1",
                description="Description 1",
                document_count=1,
                total_size=1024,
                created_at=datetime(2024, 1, 1, 12, 0, 0),
                updated_at=datetime(2024, 1, 1, 12, 0, 0)
            )
        ]
        
        with patch(
            'tools.knowledge_base_tools.KnowledgeBaseService.get_knowledge_bases',
            new_callable=AsyncMock,
            return_value=(kb_list, 10)
        ):
            result = await tool._aexecute(skip=5, limit=5)
        
        assert result.success is True
        assert result.data["skip"] == 5
        assert result.data["limit"] == 5
        assert result.data["total"] == 10
    
    @pytest.mark.asyncio
    async def test_list_knowledge_bases_error(self, mock_db_session):
        """Test handling errors during listing"""
        tool = ListKnowledgeBasesTool(db_session=mock_db_session)
        
        with patch(
            'tools.knowledge_base_tools.KnowledgeBaseService.get_knowledge_bases',
            new_callable=AsyncMock,
            side_effect=Exception("Database error")
        ):
            result = await tool._aexecute()
        
        assert result.success is False
        assert "Failed to list knowledge bases" in result.message
        assert "Database error" in result.error


class TestGetKnowledgeBaseTool:
    """Test GetKnowledgeBaseTool"""
    
    @pytest.mark.asyncio
    async def test_get_knowledge_base_success(self, mock_db_session, sample_kb_response):
        """Test successful retrieval of knowledge base"""
        tool = GetKnowledgeBaseTool(db_session=mock_db_session)
        
        with patch(
            'tools.knowledge_base_tools.KnowledgeBaseService.get_knowledge_base',
            new_callable=AsyncMock,
            return_value=sample_kb_response
        ):
            result = await tool._aexecute(kb_id="kb_test123")
        
        assert result.success is True
        assert "Successfully retrieved knowledge base" in result.message
        assert result.data["kb_id"] == "kb_test123"
        assert result.data["kb_name"] == "Test KB"
        assert result.data["document_count"] == 5
        assert result.data["total_size"] == 1024
    
    @pytest.mark.asyncio
    async def test_get_knowledge_base_not_found(self, mock_db_session):
        """Test getting non-existent knowledge base"""
        tool = GetKnowledgeBaseTool(db_session=mock_db_session)
        
        with patch(
            'tools.knowledge_base_tools.KnowledgeBaseService.get_knowledge_base',
            new_callable=AsyncMock,
            side_effect=ResourceNotFoundError("Knowledge base not found: kb_invalid")
        ):
            result = await tool._aexecute(kb_id="kb_invalid")
        
        assert result.success is False
        assert "Knowledge base not found" in result.message
        assert "not found" in result.error
    
    @pytest.mark.asyncio
    async def test_get_knowledge_base_error(self, mock_db_session):
        """Test handling generic errors during retrieval"""
        tool = GetKnowledgeBaseTool(db_session=mock_db_session)
        
        with patch(
            'tools.knowledge_base_tools.KnowledgeBaseService.get_knowledge_base',
            new_callable=AsyncMock,
            side_effect=Exception("Database error")
        ):
            result = await tool._aexecute(kb_id="kb_test123")
        
        assert result.success is False
        assert "Failed to get knowledge base" in result.message
        assert "Database error" in result.error


class TestUpdateKnowledgeBaseTool:
    """Test UpdateKnowledgeBaseTool"""
    
    @pytest.mark.asyncio
    async def test_update_knowledge_base_name(self, mock_db_session, sample_kb_response):
        """Test updating knowledge base name"""
        tool = UpdateKnowledgeBaseTool(db_session=mock_db_session)
        
        updated_response = KnowledgeBaseResponse(
            id="kb_test123",
            name="Updated KB",
            description="Test description",
            document_count=5,
            total_size=1024,
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            updated_at=datetime(2024, 1, 2, 12, 0, 0)
        )
        
        with patch(
            'tools.knowledge_base_tools.KnowledgeBaseService.update_knowledge_base',
            new_callable=AsyncMock,
            return_value=updated_response
        ):
            result = await tool._aexecute(
                kb_id="kb_test123",
                kb_name="Updated KB"
            )
        
        assert result.success is True
        assert "Successfully updated knowledge base" in result.message
        assert result.data["kb_name"] == "Updated KB"
    
    @pytest.mark.asyncio
    async def test_update_knowledge_base_description(self, mock_db_session, sample_kb_response):
        """Test updating knowledge base description"""
        tool = UpdateKnowledgeBaseTool(db_session=mock_db_session)
        
        updated_response = KnowledgeBaseResponse(
            id="kb_test123",
            name="Test KB",
            description="Updated description",
            document_count=5,
            total_size=1024,
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            updated_at=datetime(2024, 1, 2, 12, 0, 0)
        )
        
        with patch(
            'tools.knowledge_base_tools.KnowledgeBaseService.update_knowledge_base',
            new_callable=AsyncMock,
            return_value=updated_response
        ):
            result = await tool._aexecute(
                kb_id="kb_test123",
                description="Updated description"
            )
        
        assert result.success is True
        assert result.data["description"] == "Updated description"
    
    @pytest.mark.asyncio
    async def test_update_knowledge_base_both_fields(self, mock_db_session):
        """Test updating both name and description"""
        tool = UpdateKnowledgeBaseTool(db_session=mock_db_session)
        
        updated_response = KnowledgeBaseResponse(
            id="kb_test123",
            name="Updated KB",
            description="Updated description",
            document_count=5,
            total_size=1024,
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            updated_at=datetime(2024, 1, 2, 12, 0, 0)
        )
        
        with patch(
            'tools.knowledge_base_tools.KnowledgeBaseService.update_knowledge_base',
            new_callable=AsyncMock,
            return_value=updated_response
        ):
            result = await tool._aexecute(
                kb_id="kb_test123",
                kb_name="Updated KB",
                description="Updated description"
            )
        
        assert result.success is True
        assert result.data["kb_name"] == "Updated KB"
        assert result.data["description"] == "Updated description"
    
    @pytest.mark.asyncio
    async def test_update_knowledge_base_no_fields(self, mock_db_session):
        """Test updating with no fields provided"""
        tool = UpdateKnowledgeBaseTool(db_session=mock_db_session)
        
        result = await tool._aexecute(kb_id="kb_test123")
        
        assert result.success is False
        assert "No fields to update" in result.message
    
    @pytest.mark.asyncio
    async def test_update_knowledge_base_not_found(self, mock_db_session):
        """Test updating non-existent knowledge base"""
        tool = UpdateKnowledgeBaseTool(db_session=mock_db_session)
        
        with patch(
            'tools.knowledge_base_tools.KnowledgeBaseService.update_knowledge_base',
            new_callable=AsyncMock,
            side_effect=ResourceNotFoundError("Knowledge base not found: kb_invalid")
        ):
            result = await tool._aexecute(
                kb_id="kb_invalid",
                kb_name="New Name"
            )
        
        assert result.success is False
        assert "Knowledge base not found" in result.message
    
    @pytest.mark.asyncio
    async def test_update_knowledge_base_name_conflict(self, mock_db_session):
        """Test updating to a name that already exists"""
        tool = UpdateKnowledgeBaseTool(db_session=mock_db_session)
        
        with patch(
            'tools.knowledge_base_tools.KnowledgeBaseService.update_knowledge_base',
            new_callable=AsyncMock,
            side_effect=ConflictError("Knowledge base with name 'Existing KB' already exists")
        ):
            result = await tool._aexecute(
                kb_id="kb_test123",
                kb_name="Existing KB"
            )
        
        assert result.success is False
        assert "name already exists" in result.message


class TestDeleteKnowledgeBaseTool:
    """Test DeleteKnowledgeBaseTool"""
    
    @pytest.mark.asyncio
    async def test_delete_knowledge_base_success(self, mock_db_session):
        """Test successful deletion of knowledge base"""
        tool = DeleteKnowledgeBaseTool(db_session=mock_db_session)
        
        with patch(
            'tools.knowledge_base_tools.KnowledgeBaseService.delete_knowledge_base',
            new_callable=AsyncMock,
            return_value=None
        ):
            result = await tool._aexecute(kb_id="kb_test123")
        
        assert result.success is True
        assert "Successfully deleted knowledge base" in result.message
        assert result.data["kb_id"] == "kb_test123"
        assert result.data["deleted"] is True
    
    @pytest.mark.asyncio
    async def test_delete_knowledge_base_not_found(self, mock_db_session):
        """Test deleting non-existent knowledge base"""
        tool = DeleteKnowledgeBaseTool(db_session=mock_db_session)
        
        with patch(
            'tools.knowledge_base_tools.KnowledgeBaseService.delete_knowledge_base',
            new_callable=AsyncMock,
            side_effect=ResourceNotFoundError("Knowledge base not found: kb_invalid")
        ):
            result = await tool._aexecute(kb_id="kb_invalid")
        
        assert result.success is False
        assert "Knowledge base not found" in result.message
    
    @pytest.mark.asyncio
    async def test_delete_knowledge_base_error(self, mock_db_session):
        """Test handling errors during deletion"""
        tool = DeleteKnowledgeBaseTool(db_session=mock_db_session)
        
        with patch(
            'tools.knowledge_base_tools.KnowledgeBaseService.delete_knowledge_base',
            new_callable=AsyncMock,
            side_effect=Exception("Database error")
        ):
            result = await tool._aexecute(kb_id="kb_test123")
        
        assert result.success is False
        assert "Failed to delete knowledge base" in result.message
        assert "Database error" in result.error


class TestToolIntegration:
    """Integration tests for knowledge base tools"""
    
    def test_all_tools_have_correct_metadata(self, mock_db_session):
        """Test that all tools have proper metadata"""
        tools = [
            CreateKnowledgeBaseTool(db_session=mock_db_session),
            ListKnowledgeBasesTool(db_session=mock_db_session),
            GetKnowledgeBaseTool(db_session=mock_db_session),
            UpdateKnowledgeBaseTool(db_session=mock_db_session),
            DeleteKnowledgeBaseTool(db_session=mock_db_session),
        ]
        
        for tool in tools:
            assert tool.name is not None
            assert len(tool.name) > 0
            assert tool.description is not None
            assert len(tool.description) > 0
            assert tool.args_schema is not None
    
    def test_all_tools_inherit_from_base(self, mock_db_session):
        """Test that all tools inherit from BaseRagDocManTool"""
        from tools.base import BaseRagDocManTool
        
        tools = [
            CreateKnowledgeBaseTool(db_session=mock_db_session),
            ListKnowledgeBasesTool(db_session=mock_db_session),
            GetKnowledgeBaseTool(db_session=mock_db_session),
            UpdateKnowledgeBaseTool(db_session=mock_db_session),
            DeleteKnowledgeBaseTool(db_session=mock_db_session),
        ]
        
        for tool in tools:
            assert isinstance(tool, BaseRagDocManTool)
