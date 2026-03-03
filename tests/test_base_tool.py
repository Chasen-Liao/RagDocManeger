"""
Tests for Base Tool Classes

This module tests the foundational tool classes:
- ToolInput
- ToolOutput
- BaseRagDocManTool
"""

import pytest
from typing import Type
from pydantic import BaseModel, Field

from tools.base import ToolInput, ToolOutput, BaseRagDocManTool


class TestToolInput:
    """Test ToolInput base model"""
    
    def test_tool_input_creation(self):
        """Test creating a basic ToolInput instance"""
        tool_input = ToolInput()
        assert isinstance(tool_input, BaseModel)
    
    def test_tool_input_inheritance(self):
        """Test that custom input models can inherit from ToolInput"""
        
        class CustomInput(ToolInput):
            param1: str = Field(description="Test parameter")
            param2: int = Field(default=10, description="Test integer")
        
        custom = CustomInput(param1="test")
        assert custom.param1 == "test"
        assert custom.param2 == 10
    
    def test_tool_input_forbids_extra_fields(self):
        """Test that ToolInput forbids extra fields"""
        
        class CustomInput(ToolInput):
            param1: str
        
        with pytest.raises(Exception):  # Pydantic validation error
            CustomInput(param1="test", extra_field="not allowed")


class TestToolOutput:
    """Test ToolOutput model"""
    
    def test_tool_output_success(self):
        """Test creating a successful ToolOutput"""
        output = ToolOutput(
            success=True,
            message="Operation successful",
            data={"result": "test"}
        )
        
        assert output.success is True
        assert output.message == "Operation successful"
        assert output.data == {"result": "test"}
        assert output.error is None
    
    def test_tool_output_error(self):
        """Test creating an error ToolOutput"""
        output = ToolOutput(
            success=False,
            message="Operation failed",
            error="Test error message"
        )
        
        assert output.success is False
        assert output.message == "Operation failed"
        assert output.data is None
        assert output.error == "Test error message"
    
    def test_tool_output_serialization(self):
        """Test that ToolOutput can be serialized to dict"""
        output = ToolOutput(
            success=True,
            message="Test",
            data={"key": "value"}
        )
        
        output_dict = output.model_dump()
        assert output_dict["success"] is True
        assert output_dict["message"] == "Test"
        assert output_dict["data"] == {"key": "value"}


class TestBaseRagDocManTool:
    """Test BaseRagDocManTool base class"""
    
    def test_base_tool_requires_implementation(self):
        """Test that BaseRagDocManTool requires _execute implementation"""
        
        class TestInput(ToolInput):
            test_param: str
        
        class IncompleteTool(BaseRagDocManTool):
            name: str = "test_tool"
            description: str = "Test tool"
            args_schema: Type[BaseModel] = TestInput
        
        tool = IncompleteTool()
        
        # With error handling enabled (default), should return error output
        result = tool._run(test_param="test")
        assert result.success is False
        assert "must implement _execute method" in result.error
    
    @pytest.mark.asyncio
    async def test_base_tool_async_requires_implementation(self):
        """Test that BaseRagDocManTool requires _aexecute implementation"""
        
        class TestInput(ToolInput):
            test_param: str
        
        class IncompleteTool(BaseRagDocManTool):
            name: str = "test_tool"
            description: str = "Test tool"
            args_schema: Type[BaseModel] = TestInput
        
        tool = IncompleteTool()
        
        # With error handling enabled (default), should return error output
        result = await tool._arun(test_param="test")
        assert result.success is False
        assert "must implement _aexecute method" in result.error
    
    def test_complete_tool_implementation(self):
        """Test a complete tool implementation"""
        
        class TestInput(ToolInput):
            value: int
        
        class CompleteTool(BaseRagDocManTool):
            name: str = "complete_tool"
            description: str = "A complete test tool"
            args_schema: Type[BaseModel] = TestInput
            
            def _execute(self, value: int) -> ToolOutput:
                return self._create_success_output(
                    message=f"Processed value: {value}",
                    data={"result": value * 2}
                )
        
        tool = CompleteTool()
        result = tool._run(value=5)
        
        assert result.success is True
        assert result.message == "Processed value: 5"
        assert result.data == {"result": 10}
        assert result.error is None
    
    @pytest.mark.asyncio
    async def test_complete_async_tool_implementation(self):
        """Test a complete async tool implementation"""
        
        class TestInput(ToolInput):
            value: int
        
        class CompleteAsyncTool(BaseRagDocManTool):
            name: str = "complete_async_tool"
            description: str = "A complete async test tool"
            args_schema: Type[BaseModel] = TestInput
            
            async def _aexecute(self, value: int) -> ToolOutput:
                return self._create_success_output(
                    message=f"Async processed value: {value}",
                    data={"result": value * 3}
                )
        
        tool = CompleteAsyncTool()
        result = await tool._arun(value=5)
        
        assert result.success is True
        assert result.message == "Async processed value: 5"
        assert result.data == {"result": 15}
        assert result.error is None
    
    def test_tool_error_handling(self):
        """Test that tool errors are handled gracefully"""
        
        class TestInput(ToolInput):
            value: int
        
        class ErrorTool(BaseRagDocManTool):
            name: str = "error_tool"
            description: str = "A tool that raises errors"
            args_schema: Type[BaseModel] = TestInput
            
            def _execute(self, value: int) -> ToolOutput:
                raise ValueError("Test error")
        
        tool = ErrorTool()
        result = tool._run(value=5)
        
        assert result.success is False
        assert "error_tool" in result.message
        assert "Test error" in result.error
    
    @pytest.mark.asyncio
    async def test_async_tool_error_handling(self):
        """Test that async tool errors are handled gracefully"""
        
        class TestInput(ToolInput):
            value: int
        
        class AsyncErrorTool(BaseRagDocManTool):
            name: str = "async_error_tool"
            description: str = "An async tool that raises errors"
            args_schema: Type[BaseModel] = TestInput
            
            async def _aexecute(self, value: int) -> ToolOutput:
                raise ValueError("Async test error")
        
        tool = AsyncErrorTool()
        result = await tool._arun(value=5)
        
        assert result.success is False
        assert "async_error_tool" in result.message
        assert "Async test error" in result.error
    
    def test_tool_error_handling_disabled(self):
        """Test that errors are raised when error handling is disabled"""
        
        class TestInput(ToolInput):
            value: int
        
        class ErrorTool(BaseRagDocManTool):
            name: str = "error_tool"
            description: str = "A tool that raises errors"
            args_schema: Type[BaseModel] = TestInput
            handle_tool_error: bool = False
            
            def _execute(self, value: int) -> ToolOutput:
                raise ValueError("Test error")
        
        tool = ErrorTool()
        
        with pytest.raises(ValueError, match="Test error"):
            tool._run(value=5)
    
    def test_create_success_output_helper(self):
        """Test the _create_success_output helper method"""
        
        class TestInput(ToolInput):
            pass
        
        class TestTool(BaseRagDocManTool):
            name: str = "test_tool"
            description: str = "Test tool"
            args_schema: Type[BaseModel] = TestInput
        
        tool = TestTool()
        output = tool._create_success_output(
            message="Success",
            data={"key": "value"}
        )
        
        assert output.success is True
        assert output.message == "Success"
        assert output.data == {"key": "value"}
        assert output.error is None
    
    def test_create_error_output_helper(self):
        """Test the _create_error_output helper method"""
        
        class TestInput(ToolInput):
            pass
        
        class TestTool(BaseRagDocManTool):
            name: str = "test_tool"
            description: str = "Test tool"
            args_schema: Type[BaseModel] = TestInput
        
        tool = TestTool()
        output = tool._create_error_output(
            message="Failed",
            error="Error details"
        )
        
        assert output.success is False
        assert output.message == "Failed"
        assert output.data is None
        assert output.error == "Error details"
