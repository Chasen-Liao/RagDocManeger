"""LangChain 1.x LLM wrapper for LLM Provider."""

import logging
from typing import Optional, List, Any, Iterator, AsyncIterator
from langchain_core.language_models.llms import LLM
from langchain_core.callbacks.manager import CallbackManagerForLLMRun, AsyncCallbackManagerForLLMRun
from langchain_core.outputs import GenerationChunk
from pydantic import Field
from .llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class LangChainLLMWrapper(LLM):
    """
    LangChain 1.x compatible wrapper for LLM Provider.
    
    This wrapper adapts our custom LLM Provider to the LangChain 1.x LLM interface,
    supporting synchronous, asynchronous, and streaming execution.
    
    Attributes:
        llm_provider: The underlying LLM provider instance
        model_name: Name of the model for identification
    """

    llm_provider: Any = Field(description="The underlying LLM provider instance")
    model_name: str = Field(default="custom", description="Name of the model for identification")

    def __init__(self, llm_provider: LLMProvider, model_name: str = "custom", **kwargs):
        """
        Initialize LangChain LLM wrapper.

        Args:
            llm_provider: Our custom LLM provider instance
            model_name: Name of the model for identification
            **kwargs: Additional keyword arguments
        """
        super().__init__(llm_provider=llm_provider, model_name=model_name, **kwargs)

    @property
    def _llm_type(self) -> str:
        """
        Return type of LLM.
        
        Returns:
            String identifier for the LLM type
        """
        return self.model_name

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any
    ) -> str:
        """
        Call the LLM synchronously.
        
        This method wraps the async generate method to provide synchronous execution.

        Args:
            prompt: Input prompt
            stop: Stop sequences (not currently used)
            run_manager: Callback manager for LLM run
            **kwargs: Additional parameters to pass to the LLM

        Returns:
            Generated text string
            
        Raises:
            Exception: If LLM generation fails
        """
        import asyncio

        try:
            # Get or create event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    raise RuntimeError("Event loop is closed")
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Run async generation in sync context
            result = loop.run_until_complete(
                self.llm_provider.generate(prompt, **kwargs)
            )
            
            logger.debug(f"LLM generation completed: {len(result)} characters")
            return result

        except Exception as e:
            logger.error(f"Error in synchronous LLM call: {str(e)}")
            raise

    async def _acall(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any
    ) -> str:
        """
        Call the LLM asynchronously.
        
        This method provides native async execution for better performance
        in async contexts.

        Args:
            prompt: Input prompt
            stop: Stop sequences (not currently used)
            run_manager: Async callback manager for LLM run
            **kwargs: Additional parameters to pass to the LLM

        Returns:
            Generated text string
            
        Raises:
            Exception: If LLM generation fails
        """
        try:
            result = await self.llm_provider.generate(prompt, **kwargs)
            logger.debug(f"Async LLM generation completed: {len(result)} characters")
            return result

        except Exception as e:
            logger.error(f"Error in asynchronous LLM call: {str(e)}")
            raise

    def _stream(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any
    ) -> Iterator[GenerationChunk]:
        """
        Stream the LLM output synchronously.
        
        This method provides streaming support for real-time text generation.

        Args:
            prompt: Input prompt
            stop: Stop sequences (not currently used)
            run_manager: Callback manager for LLM run
            **kwargs: Additional parameters to pass to the LLM

        Yields:
            GenerationChunk objects containing generated text
            
        Raises:
            Exception: If streaming fails
        """
        import asyncio

        try:
            # Get or create event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    raise RuntimeError("Event loop is closed")
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Check if provider supports streaming
            if not hasattr(self.llm_provider, 'generate_stream'):
                # Fallback: generate full response and yield it
                logger.warning("Provider does not support streaming, falling back to full generation")
                result = loop.run_until_complete(
                    self.llm_provider.generate(prompt, **kwargs)
                )
                chunk = GenerationChunk(text=result)
                if run_manager:
                    run_manager.on_llm_new_token(result)
                yield chunk
                return

            # Stream generation
            async_gen = self.llm_provider.generate_stream(prompt, **kwargs)
            
            while True:
                try:
                    text = loop.run_until_complete(async_gen.__anext__())
                    chunk = GenerationChunk(text=text)
                    if run_manager:
                        run_manager.on_llm_new_token(text)
                    yield chunk
                except StopAsyncIteration:
                    break

        except Exception as e:
            logger.error(f"Error in synchronous streaming: {str(e)}")
            raise

    async def _astream(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any
    ) -> AsyncIterator[GenerationChunk]:
        """
        Stream the LLM output asynchronously.
        
        This method provides native async streaming for better performance.

        Args:
            prompt: Input prompt
            stop: Stop sequences (not currently used)
            run_manager: Async callback manager for LLM run
            **kwargs: Additional parameters to pass to the LLM

        Yields:
            GenerationChunk objects containing generated text
            
        Raises:
            Exception: If streaming fails
        """
        try:
            # Check if provider supports streaming
            if not hasattr(self.llm_provider, 'generate_stream'):
                # Fallback: generate full response and yield it
                logger.warning("Provider does not support streaming, falling back to full generation")
                result = await self.llm_provider.generate(prompt, **kwargs)
                chunk = GenerationChunk(text=result)
                if run_manager:
                    await run_manager.on_llm_new_token(result)
                yield chunk
                return

            # Stream generation
            async for text in self.llm_provider.generate_stream(prompt, **kwargs):
                chunk = GenerationChunk(text=text)
                if run_manager:
                    await run_manager.on_llm_new_token(text)
                yield chunk

        except Exception as e:
            logger.error(f"Error in asynchronous streaming: {str(e)}")
            raise

    @property
    def _identifying_params(self) -> dict:
        """
        Get identifying parameters for the LLM.
        
        Returns:
            Dictionary of identifying parameters
        """
        return {
            "model_name": self.model_name,
            "llm_type": self._llm_type,
        }
