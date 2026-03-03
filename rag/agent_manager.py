"""LangChain Agent for one-sentence management system."""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from langchain_core.tools import Tool
from langchain_core.prompts import PromptTemplate
from langchain_core.language_models.llm import LLM
from langchain_core.callbacks.base import BaseCallbackHandler

# Try to import from langchain_core first (1.x), fallback to langchain (0.x)
try:
    from langchain_core.agents import AgentExecutor, create_react_agent
except ImportError:
    try:
        from langchain.agents import AgentExecutor, create_react_agent
    except ImportError:
        # Fallback for compatibility
        AgentExecutor = None
        create_react_agent = None

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    """Result from agent execution."""

    success: bool
    action: str
    result: str
    details: Dict[str, Any]


class LangChainLLMWrapper(LLM):
    """Wrapper to adapt our LLM provider to LangChain LLM interface."""

    def __init__(self, llm_provider, model_name: str = "custom"):
        """
        Initialize LangChain LLM wrapper.

        Args:
            llm_provider: Our custom LLM provider
            model_name: Name of the model
        """
        super().__init__()
        self.llm_provider = llm_provider
        self.model_name = model_name

    @property
    def _llm_type(self) -> str:
        """Return type of LLM."""
        return self.model_name

    def _call(self, prompt: str, stop: Optional[List[str]] = None, **kwargs) -> str:
        """
        Call the LLM synchronously.

        Args:
            prompt: Input prompt
            stop: Stop sequences
            **kwargs: Additional parameters

        Returns:
            Generated text
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.llm_provider.generate(prompt, **kwargs))


class ManagementAgent:
    """Agent for managing knowledge bases and documents."""

    def __init__(self, llm_provider, kb_service=None, doc_service=None):
        """
        Initialize management agent.

        Args:
            llm_provider: LLM provider instance
            kb_service: Knowledge base service
            doc_service: Document service
        """
        self.llm_provider = llm_provider
        self.kb_service = kb_service
        self.doc_service = doc_service
        self.agent_executor = None
        self._setup_agent()

    def _setup_agent(self):
        """Setup LangChain agent with tools."""
        # Create LangChain LLM wrapper
        llm = LangChainLLMWrapper(self.llm_provider)

        # Define tools
        tools = self._create_tools()

        # Create agent prompt
        prompt = self._create_prompt()

        # Create agent using LangChain 1.0 API
        agent = create_react_agent(llm, tools, prompt)

        # Create executor with updated parameters for LangChain 1.0
        self.agent_executor = AgentExecutor.from_agent_and_tools(
            agent=agent,
            tools=tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=10,
        )

    def _create_tools(self) -> List[Tool]:
        """
        Create tools for the agent.

        Returns:
            List of Tool objects
        """
        tools = [
            Tool(
                name="create_knowledge_base",
                func=self._tool_create_kb,
                description="Create a new knowledge base. Input: knowledge base name",
            ),
            Tool(
                name="list_knowledge_bases",
                func=self._tool_list_kbs,
                description="List all knowledge bases",
            ),
            Tool(
                name="delete_knowledge_base",
                func=self._tool_delete_kb,
                description="Delete a knowledge base. Input: knowledge base name",
            ),
            Tool(
                name="upload_document",
                func=self._tool_upload_doc,
                description="Upload a document to a knowledge base. Input: kb_name|doc_path",
            ),
            Tool(
                name="list_documents",
                func=self._tool_list_docs,
                description="List documents in a knowledge base. Input: knowledge base name",
            ),
            Tool(
                name="delete_document",
                func=self._tool_delete_doc,
                description="Delete a document. Input: kb_name|doc_name",
            ),
            Tool(
                name="search_documents",
                func=self._tool_search,
                description="Search documents in a knowledge base. Input: kb_name|query",
            ),
        ]
        return tools

    def _create_prompt(self) -> PromptTemplate:
        """
        Create prompt template for the agent.

        Returns:
            PromptTemplate instance
        """
        template = """You are a helpful assistant for managing knowledge bases and documents.
You have access to tools to create, list, delete knowledge bases and manage documents.

When a user asks you to perform an action, use the appropriate tool.
Always be clear about what action you're taking and the result.

User input: {input}

{agent_scratchpad}"""

        return PromptTemplate(
            input_variables=["input", "agent_scratchpad"],
            template=template,
        )

    def _tool_create_kb(self, kb_name: str) -> str:
        """Create a knowledge base."""
        try:
            if not self.kb_service:
                return "Error: Knowledge base service not available"

            result = self.kb_service.create_knowledge_base(kb_name)
            return f"Successfully created knowledge base: {kb_name}"
        except Exception as e:
            return f"Error creating knowledge base: {str(e)}"

    def _tool_list_kbs(self, _: str = "") -> str:
        """List all knowledge bases."""
        try:
            if not self.kb_service:
                return "Error: Knowledge base service not available"

            kbs = self.kb_service.list_knowledge_bases()
            if not kbs:
                return "No knowledge bases found"

            kb_list = "\n".join([f"- {kb.name}" for kb in kbs])
            return f"Knowledge bases:\n{kb_list}"
        except Exception as e:
            return f"Error listing knowledge bases: {str(e)}"

    def _tool_delete_kb(self, kb_name: str) -> str:
        """Delete a knowledge base."""
        try:
            if not self.kb_service:
                return "Error: Knowledge base service not available"

            self.kb_service.delete_knowledge_base(kb_name)
            return f"Successfully deleted knowledge base: {kb_name}"
        except Exception as e:
            return f"Error deleting knowledge base: {str(e)}"

    def _tool_upload_doc(self, input_str: str) -> str:
        """Upload a document."""
        try:
            if not self.doc_service:
                return "Error: Document service not available"

            parts = input_str.split("|")
            if len(parts) < 2:
                return "Error: Invalid input format. Use: kb_name|doc_path"

            kb_name, doc_path = parts[0].strip(), parts[1].strip()
            result = self.doc_service.upload_document(kb_name, doc_path)
            return f"Successfully uploaded document to {kb_name}"
        except Exception as e:
            return f"Error uploading document: {str(e)}"

    def _tool_list_docs(self, kb_name: str) -> str:
        """List documents in a knowledge base."""
        try:
            if not self.doc_service:
                return "Error: Document service not available"

            docs = self.doc_service.list_documents(kb_name)
            if not docs:
                return f"No documents found in {kb_name}"

            doc_list = "\n".join([f"- {doc.name}" for doc in docs])
            return f"Documents in {kb_name}:\n{doc_list}"
        except Exception as e:
            return f"Error listing documents: {str(e)}"

    def _tool_delete_doc(self, input_str: str) -> str:
        """Delete a document."""
        try:
            if not self.doc_service:
                return "Error: Document service not available"

            parts = input_str.split("|")
            if len(parts) < 2:
                return "Error: Invalid input format. Use: kb_name|doc_name"

            kb_name, doc_name = parts[0].strip(), parts[1].strip()
            self.doc_service.delete_document(kb_name, doc_name)
            return f"Successfully deleted document: {doc_name}"
        except Exception as e:
            return f"Error deleting document: {str(e)}"

    def _tool_search(self, input_str: str) -> str:
        """Search documents."""
        try:
            if not self.doc_service:
                return "Error: Document service not available"

            parts = input_str.split("|")
            if len(parts) < 2:
                return "Error: Invalid input format. Use: kb_name|query"

            kb_name, query = parts[0].strip(), parts[1].strip()
            results = self.doc_service.search_documents(kb_name, query)
            if not results:
                return f"No results found for query: {query}"

            result_list = "\n".join([f"- {r.get('name', 'Unknown')}" for r in results])
            return f"Search results in {kb_name}:\n{result_list}"
        except Exception as e:
            return f"Error searching documents: {str(e)}"

    async def execute_command(self, user_input: str) -> AgentResult:
        """
        Execute a management command using the agent.

        Args:
            user_input: User command in natural language

        Returns:
            AgentResult with execution details
        """
        try:
            if not self.agent_executor:
                return AgentResult(
                    success=False,
                    action="",
                    result="Agent not initialized",
                    details={},
                )

            # Run agent
            result = self.agent_executor.invoke({"input": user_input})

            return AgentResult(
                success=True,
                action="execute_command",
                result=result.get("output", ""),
                details={"input": user_input},
            )

        except Exception as e:
            logger.error(f"Error executing command: {str(e)}")
            return AgentResult(
                success=False,
                action="execute_command",
                result=str(e),
                details={"input": user_input, "error": str(e)},
            )
