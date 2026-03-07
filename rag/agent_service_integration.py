"""Agent service integration layer with dependency injection and connection pooling."""

import asyncio
from typing import Optional, Dict, Any, TYPE_CHECKING
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
from sqlalchemy.pool import QueuePool
from logger import logger

if TYPE_CHECKING:
    from services.knowledge_base_service import KnowledgeBaseService
    from services.document_service import DocumentService
    from services.search_service import SearchService
    from core.llm_provider import LLMProvider
    from core.embedding_provider import EmbeddingProvider
    from core.reranker_provider import RerankerProvider


class ServiceConnectionPool:
    """Manages connection pooling for concurrent Agent instances."""
    
    def __init__(self, max_connections: int = 10):
        """Initialize connection pool.
        
        Args:
            max_connections: Maximum number of concurrent connections
        """
        self.max_connections = max_connections
        self.active_connections = 0
        self.semaphore = asyncio.Semaphore(max_connections)
        self.lock = asyncio.Lock()
        logger.info(f"ServiceConnectionPool initialized with max_connections={max_connections}")
    
    @asynccontextmanager
    async def acquire(self):
        """Acquire a connection from the pool."""
        async with self.semaphore:
            async with self.lock:
                self.active_connections += 1
                logger.debug(f"Connection acquired. Active: {self.active_connections}/{self.max_connections}")
            
            try:
                yield
            finally:
                async with self.lock:
                    self.active_connections -= 1
                    logger.debug(f"Connection released. Active: {self.active_connections}/{self.max_connections}")
    
    def get_stats(self) -> Dict[str, int]:
        """Get connection pool statistics."""
        return {
            "active_connections": self.active_connections,
            "max_connections": self.max_connections,
            "available_connections": self.max_connections - self.active_connections
        }


class AgentServiceIntegration:
    """Integration layer for Agent with RAG services."""
    
    def __init__(
        self,
        db_session: Session,
        llm_provider: 'LLMProvider',
        embedding_provider: 'EmbeddingProvider',
        reranker_provider: Optional['RerankerProvider'] = None,
        max_concurrent_agents: int = 10
    ):
        """Initialize Agent service integration.
        
        Args:
            db_session: Database session
            llm_provider: LLM provider instance
            embedding_provider: Embedding provider instance
            reranker_provider: Optional reranker provider instance
            max_concurrent_agents: Maximum concurrent Agent instances
        """
        self.db_session = db_session
        self.llm_provider = llm_provider
        self.embedding_provider = embedding_provider
        self.reranker_provider = reranker_provider
        
        # Initialize connection pool
        self.connection_pool = ServiceConnectionPool(max_concurrent_agents)
        
        # Initialize services with dependency injection (lazy import)
        from services.knowledge_base_service import KnowledgeBaseService
        from services.document_service import DocumentService
        from services.search_service import SearchService
        from core.vector_store import VectorStore

        # Initialize vector store
        vector_store = VectorStore()

        self.knowledge_base_service = KnowledgeBaseService()
        self.document_service = DocumentService(
            db=db_session,
            vector_store=vector_store,
            embedding_provider=embedding_provider
        )
        self.search_service = SearchService(
            db=db_session,
            embedding_provider=embedding_provider,
            reranker_provider=reranker_provider,
            llm_provider=llm_provider
        )
        
        # Service cache for performance
        self._service_cache: Dict[str, Any] = {}
        
        logger.info(
            f"AgentServiceIntegration initialized with "
            f"max_concurrent_agents={max_concurrent_agents}"
        )
    
    @asynccontextmanager
    async def get_services(self):
        """Get services with connection pooling.
        
        Yields:
            Tuple of (knowledge_base_service, document_service, search_service)
        """
        async with self.connection_pool.acquire():
            yield (
                self.knowledge_base_service,
                self.document_service,
                self.search_service
            )
    
    async def get_knowledge_base_service(self) -> 'KnowledgeBaseService':
        """Get knowledge base service with connection pooling."""
        async with self.connection_pool.acquire():
            return self.knowledge_base_service
    
    async def get_document_service(self) -> 'DocumentService':
        """Get document service with connection pooling."""
        async with self.connection_pool.acquire():
            return self.document_service
    
    async def get_search_service(self) -> 'SearchService':
        """Get search service with connection pooling."""
        async with self.connection_pool.acquire():
            return self.search_service
    
    def get_shared_vector_store(self):
        """Get shared vector store instance.
        
        Returns:
            Shared vector store used by all services
        """
        return self.embedding_provider.vector_store if hasattr(self.embedding_provider, 'vector_store') else None
    
    def get_shared_database_connection(self) -> Session:
        """Get shared database connection.
        
        Returns:
            Shared database session
        """
        return self.db_session
    
    def get_connection_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics.
        
        Returns:
            Dictionary with pool statistics
        """
        return {
            "pool_stats": self.connection_pool.get_stats(),
            "services": {
                "knowledge_base_service": "initialized",
                "document_service": "initialized",
                "search_service": "initialized"
            }
        }
    
    async def validate_services(self) -> bool:
        """Validate that all services are properly initialized.
        
        Returns:
            True if all services are valid, False otherwise
        """
        try:
            async with self.get_services() as (kb_svc, doc_svc, search_svc):
                # Verify services are accessible
                if not kb_svc or not doc_svc or not search_svc:
                    logger.error("One or more services failed to initialize")
                    return False
                
                # Verify providers are accessible
                if not self.llm_provider or not self.embedding_provider:
                    logger.error("LLM or Embedding provider not initialized")
                    return False
                
                logger.info("All services validated successfully")
                return True
        except Exception as e:
            logger.error(f"Service validation failed: {str(e)}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all services.
        
        Returns:
            Dictionary with health status
        """
        health_status = {
            "status": "healthy",
            "services": {},
            "providers": {},
            "pool": self.connection_pool.get_stats()
        }
        
        try:
            # Check services
            async with self.get_services() as (kb_svc, doc_svc, search_svc):
                health_status["services"]["knowledge_base_service"] = "ok"
                health_status["services"]["document_service"] = "ok"
                health_status["services"]["search_service"] = "ok"
            
            # Check providers
            health_status["providers"]["llm_provider"] = "ok" if self.llm_provider else "missing"
            health_status["providers"]["embedding_provider"] = "ok" if self.embedding_provider else "missing"
            health_status["providers"]["reranker_provider"] = "ok" if self.reranker_provider else "missing"
            
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["error"] = str(e)
            logger.error(f"Health check failed: {str(e)}")
        
        return health_status


class ServiceRegistry:
    """Registry for managing service instances across the application."""
    
    _instance: Optional['ServiceRegistry'] = None
    _integration: Optional[AgentServiceIntegration] = None
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def initialize(
        cls,
        db_session: Session,
        llm_provider: 'LLMProvider',
        embedding_provider: 'EmbeddingProvider',
        reranker_provider: Optional['RerankerProvider'] = None,
        max_concurrent_agents: int = 10
    ) -> 'ServiceRegistry':
        """Initialize the service registry.
        
        Args:
            db_session: Database session
            llm_provider: LLM provider instance
            embedding_provider: Embedding provider instance
            reranker_provider: Optional reranker provider instance
            max_concurrent_agents: Maximum concurrent Agent instances
            
        Returns:
            ServiceRegistry instance
        """
        registry = cls()
        registry._integration = AgentServiceIntegration(
            db_session=db_session,
            llm_provider=llm_provider,
            embedding_provider=embedding_provider,
            reranker_provider=reranker_provider,
            max_concurrent_agents=max_concurrent_agents
        )
        logger.info("ServiceRegistry initialized")
        return registry
    
    @classmethod
    def get_integration(cls) -> AgentServiceIntegration:
        """Get the service integration instance.
        
        Returns:
            AgentServiceIntegration instance
            
        Raises:
            RuntimeError: If registry not initialized
        """
        registry = cls()
        if registry._integration is None:
            raise RuntimeError("ServiceRegistry not initialized. Call initialize() first.")
        return registry._integration
    
    @classmethod
    def get_knowledge_base_service(cls) -> 'KnowledgeBaseService':
        """Get knowledge base service."""
        return cls.get_integration().knowledge_base_service
    
    @classmethod
    def get_document_service(cls) -> 'DocumentService':
        """Get document service."""
        return cls.get_integration().document_service
    
    @classmethod
    def get_search_service(cls) -> 'SearchService':
        """Get search service."""
        return cls.get_integration().search_service
