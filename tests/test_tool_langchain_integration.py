"""
Integration tests for tool system with LangChain

This module tests the integration of RagDocMan tools with LangChain's agent system.
"""

import pytest
from typing import Type
from pydantic import BaseModel, Field

from tools.base import ToolInput, ToolOutput, BaseRagDocManTool


class TestLangChainIntegration:
    """Test integration with LangChain"""
    
    def test_tool_has_langchain_attributes(self):
        """Test that tools have required LangChain attributes"""
        
        class TestInput(ToolInput):
            value: int
        
        class TestTool(BaseRagDocManTool):
            name: str = "test_tool"
            description: str = "A test tool"
            args_schema: Type[BaseModel] = TestInput
            
            def _execute(self, value: int) -> ToolOutput:
                return self._create_success_output(
                    message="Success",
                    data={"result": value}
                )
        
        tool = TestTool()
        
        # Check LangChain required attributes
        assert hasattr(tool, 'name')
        assert hasattr(tool, 'description')
        assert hasattr(tool, 'args_schema')
        assert hasattr(tool, '_run')
        assert hasattr(tool, '_arun')
        
        # Verify attribute values
        assert tool.name == "test_tool"
        assert tool.description == "A test tool"
        assert tool.args_schema == TestInput
    
    def test_tool_schema_generation(self):
        """Test that tool schema can be generated for LangChain"""
        
        class TestInput(ToolInput):
            query: str = Field(description="Search query")
            limit: int = Field(default=10, description="Result limit")
        
        class TestTool(BaseRagDocManTool):
            name: str = "search_tool"
            description: str = "Search for documents"
            args_schema: Type[BaseModel] = TestInput
            
            def _execute(self, query: str, limit: int = 10) -> ToolOutput:
                return self._create_success_output("Done")
        
        tool = TestTool()
        
        # LangChain uses args_schema to generate input schema
        schema = tool.args_schema.model_json_schema()
        
        assert "properties" in schema
        assert "query" in schema["properties"]
        assert "limit" in schema["properties"]
        assert schema["properties"]["query"]["description"] == "Search query"
        assert schema["properties"]["limit"]["default"] == 10
    
    def test_tool_invocation_interface(self):
        """Test that tools can be invoked using LangChain's interface"""
        
        class TestInput(ToolInput):
            x: int
            y: int
        
        class CalculatorTool(BaseRagDocManTool):
            name: str = "calculator"
            description: str = "Add two numbers"
            args_schema: Type[BaseModel] = TestInput
            
            def _execute(self, x: int, y: int) -> ToolOutput:
                return self._create_success_output(
                    message=f"Calculated {x} + {y}",
                    data={"result": x + y}
                )
        
        tool = CalculatorTool()
        
        # Test direct invocation (how LangChain calls tools)
        result = tool._run(x=5, y=3)
        
        assert isinstance(result, ToolOutput)
        assert result.success is True
        assert result.data["result"] == 8
    
    @pytest.mark.asyncio
    async def test_async_tool_invocation_interface(self):
        """Test that async tools can be invoked using LangChain's async interface"""
        
        class TestInput(ToolInput):
            text: str
        
        class AsyncProcessorTool(BaseRagDocManTool):
            name: str = "async_processor"
            description: str = "Process text asynchronously"
            args_schema: Type[BaseModel] = TestInput
            
            async def _aexecute(self, text: str) -> ToolOutput:
                processed = text.upper()
                return self._create_success_output(
                    message="Processed text",
                    data={"result": processed}
                )
        
        tool = AsyncProcessorTool()
        
        # Test async invocation (how LangChain calls async tools)
        result = await tool._arun(text="hello")
        
        assert isinstance(result, ToolOutput)
        assert result.success is True
        assert result.data["result"] == "HELLO"
    
    def test_tool_error_handling_for_agents(self):
        """Test that tool errors are handled gracefully for agent use"""
        
        class TestInput(ToolInput):
            value: int
        
        class ErrorProneTool(BaseRagDocManTool):
            name: str = "error_tool"
            description: str = "A tool that may fail"
            args_schema: Type[BaseModel] = TestInput
            
            def _execute(self, value: int) -> ToolOutput:
                if value < 0:
                    raise ValueError("Value must be positive")
                return self._create_success_output("Success")
        
        tool = ErrorProneTool()
        
        # Test error handling - should not raise, return error output
        result = tool._run(value=-1)
        
        assert isinstance(result, ToolOutput)
        assert result.success is False
        assert result.error is not None
        assert "Value must be positive" in result.error
    
    def test_multiple_tools_can_coexist(self):
        """Test that multiple tools can be created and used together"""
        
        class Input1(ToolInput):
            text: str
        
        class Input2(ToolInput):
            number: int
        
        class Tool1(BaseRagDocManTool):
            name: str = "tool1"
            description: str = "First tool"
            args_schema: Type[BaseModel] = Input1
            
            def _execute(self, text: str) -> ToolOutput:
                return self._create_success_output("Tool1", data={"text": text})
        
        class Tool2(BaseRagDocManTool):
            name: str = "tool2"
            description: str = "Second tool"
            args_schema: Type[BaseModel] = Input2
            
            def _execute(self, number: int) -> ToolOutput:
                return self._create_success_output("Tool2", data={"number": number})
        
        # Create multiple tool instances
        tools = [Tool1(), Tool2()]
        
        # Verify they work independently
        result1 = tools[0]._run(text="test")
        result2 = tools[1]._run(number=42)
        
        assert result1.success is True
        assert result1.data["text"] == "test"
        assert result2.success is True
        assert result2.data["number"] == 42
