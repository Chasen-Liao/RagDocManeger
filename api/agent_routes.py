"""Agent API routes for chat and session management."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import asyncio
import json
from datetime import datetime

from logger import logger
from rag.agent_manager_core import AgentManager, AgentResult
from rag.agent_service_integration import ServiceRegistry
from core.llm_provider import LLMProvider
from core.embedding_provider import EmbeddingProvider
from core.reranker_provider import RerankerProvider
from database import get_db
from sqlalchemy.orm import Session


# Request/Response Models
class AgentRequest(BaseModel):
    """Request model for Agent chat."""
    user_input: str = Field(..., description="User input message")
    session_id: str = Field(..., description="Session ID for conversation context")
    stream: bool = Field(default=False, description="Whether to stream the response")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata")


class ToolCall(BaseModel):
    """Tool call record."""
    tool_name: str
    tool_input: Dict[str, Any]
    tool_output: Dict[str, Any]
    execution_time: float


class AgentResponse(BaseModel):
    """Response model for Agent chat."""
    success: bool
    output: str
    tool_calls: List[ToolCall] = []
    execution_time: float
    intermediate_steps: List[tuple] = []
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SessionClearResponse(BaseModel):
    """Response model for session clearing."""
    success: bool
    message: str
    session_id: str


class StreamChunk(BaseModel):
    """Streaming response chunk."""
    type: str  # "start", "tool_call", "output", "end", "error"
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Dependency injection
def get_agent_manager(db: Session = Depends(get_db)) -> AgentManager:
    """Get or create AgentManager instance.
    
    Args:
        db: Database session
        
    Returns:
        AgentManager instance
    """
    try:
        # Get providers from configuration
        from config import settings
        
        llm_provider = LLMProvider(
            provider=settings.llm_provider,
            model=settings.llm_model,
            api_key=settings.llm_api_key
        )
        
        embedding_provider = EmbeddingProvider(
            provider=settings.embedding_provider,
            model=settings.embedding_model
        )
        
        reranker_provider = None
        if settings.reranker_provider:
            reranker_provider = RerankerProvider(
                provider=settings.reranker_provider,
                model=settings.reranker_model
            )
        
        # Initialize service registry
        ServiceRegistry.initialize(
            db_session=db,
            llm_provider=llm_provider,
            embedding_provider=embedding_provider,
            reranker_provider=reranker_provider
        )
        
        # Create AgentManager
        agent_manager = AgentManager(
            llm_provider=llm_provider,
            embedding_provider=embedding_provider,
            reranker_provider=reranker_provider,
            db=db
        )
        
        return agent_manager
    
    except Exception as e:
        logger.error(f"Failed to create AgentManager: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize Agent: {str(e)}"
        )


# Router
router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


@router.post("/chat", response_model=AgentResponse)
async def chat(
    request: AgentRequest,
    agent_manager: AgentManager = Depends(get_agent_manager)
) -> AgentResponse:
    """Chat with Agent (synchronous).
    
    Args:
        request: Agent request with user input and session ID
        agent_manager: Agent manager instance
        
    Returns:
        Agent response with output and tool calls
        
    Raises:
        HTTPException: If chat fails
    """
    try:
        logger.info(f"Chat request: session_id={request.session_id}, input_length={len(request.user_input)}")
        
        # Invoke agent
        result: AgentResult = await agent_manager.ainvoke(
            user_input=request.user_input,
            session_id=request.session_id
        )
        
        # Convert tool calls to response format
        tool_calls = []
        if result.tool_calls:
            for tool_call in result.tool_calls:
                tool_calls.append(ToolCall(
                    tool_name=tool_call.tool_name,
                    tool_input=tool_call.tool_input,
                    tool_output=tool_call.tool_output.dict() if hasattr(tool_call.tool_output, 'dict') else tool_call.tool_output,
                    execution_time=tool_call.execution_time
                ))
        
        response = AgentResponse(
            success=True,
            output=result.output,
            tool_calls=tool_calls,
            execution_time=result.execution_time,
            intermediate_steps=result.intermediate_steps
        )
        
        logger.info(f"Chat completed: session_id={request.session_id}, execution_time={result.execution_time}s")
        return response
    
    except Exception as e:
        logger.error(f"Chat failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat failed: {str(e)}"
        )


@router.post("/chat/stream")
async def chat_stream(
    request: AgentRequest,
    agent_manager: AgentManager = Depends(get_agent_manager)
):
    """Chat with Agent (streaming).
    
    Args:
        request: Agent request with user input and session ID
        agent_manager: Agent manager instance
        
    Returns:
        StreamingResponse with SSE format chunks
    """
    async def generate():
        """Generate streaming response chunks."""
        try:
            logger.info(f"Stream chat request: session_id={request.session_id}")
            
            # Send start event
            yield f"data: {json.dumps({'type': 'start', 'session_id': request.session_id})}\n\n"
            
            # Stream agent response
            async for chunk in agent_manager.astream(
                user_input=request.user_input,
                session_id=request.session_id
            ):
                # Format chunk as SSE
                stream_chunk = StreamChunk(
                    type=chunk.get("type", "output"),
                    data=chunk
                )
                yield f"data: {stream_chunk.model_dump_json()}\n\n"
            
            # Send end event
            yield f"data: {json.dumps({'type': 'end', 'session_id': request.session_id})}\n\n"
            
            logger.info(f"Stream chat completed: session_id={request.session_id}")
        
        except Exception as e:
            logger.error(f"Stream chat failed: {str(e)}")
            error_chunk = StreamChunk(
                type="error",
                data={"error": str(e)}
            )
            yield f"data: {error_chunk.model_dump_json()}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")


@router.delete("/session/{session_id}", response_model=SessionClearResponse)
async def clear_session(
    session_id: str,
    agent_manager: AgentManager = Depends(get_agent_manager)
) -> SessionClearResponse:
    """Clear session history.
    
    Args:
        session_id: Session ID to clear
        agent_manager: Agent manager instance
        
    Returns:
        Confirmation response
        
    Raises:
        HTTPException: If clearing fails
    """
    try:
        logger.info(f"Clearing session: {session_id}")
        
        await agent_manager.clear_session(session_id)
        
        response = SessionClearResponse(
            success=True,
            message=f"Session {session_id} cleared successfully",
            session_id=session_id
        )
        
        logger.info(f"Session cleared: {session_id}")
        return response
    
    except Exception as e:
        logger.error(f"Failed to clear session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear session: {str(e)}"
        )


@router.get("/sessions", response_model=dict)
async def list_sessions(
    db: Session = Depends(get_db)
):
    """List all conversation sessions.

    Returns:
        List of all unique session IDs with their metadata

    """
    try:
        from models.orm import ConversationHistory

        # Get all unique session IDs with their latest message time and message count
        sessions_data = db.query(
            ConversationHistory.session_id,
            ConversationHistory.created_at,
            ConversationHistory.content
        ).order_by(
            ConversationHistory.session_id,
            ConversationHistory.created_at.desc()
        ).all()

        # Group by session_id
        sessions_dict: Dict[str, dict] = {}
        for row in sessions_data:
            if row.session_id not in sessions_dict:
                sessions_dict[row.session_id] = {
                    "session_id": row.session_id,
                    "last_message_at": row.created_at.isoformat() if row.created_at else None,
                    "preview": row.content[:100] if row.content else "",
                    "message_count": 0
                }
            sessions_dict[row.session_id]["message_count"] += 1

        # Convert to list and sort by last message time
        sessions_list = list(sessions_dict.values())
        sessions_list.sort(
            key=lambda x: x["last_message_at"] or "",
            reverse=True
        )

        return {
            "success": True,
            "data": sessions_list,
            "message": None
        }
    except Exception as e:
        logger.error(f"Failed to list sessions: {str(e)}")
        return {
            "success": False,
            "data": [],
            "error": {
                "code": "LIST_SESSIONS_ERROR",
                "message": str(e)
            }
        }


@router.get("/sessions/{session_id}/history", response_model=dict)
async def get_session_history(
    session_id: str,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get conversation history for a specific session.

    Args:
        session_id: Session ID
        limit: Maximum number of messages to return
        db: Database session

    Returns:
        Conversation history for the session

    """
    try:
        from models.orm import ConversationHistory

        # Get messages for this session
        messages = db.query(ConversationHistory).filter(
            ConversationHistory.session_id == session_id
        ).order_by(
            ConversationHistory.created_at.asc()
        ).limit(limit).all()

        history = []
        for msg in messages:
            history.append({
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat() if msg.created_at else None
            })

        return {
            "success": True,
            "data": {
                "session_id": session_id,
                "messages": history,
                "message_count": len(history)
            },
            "message": None
        }
    except Exception as e:
        logger.error(f"Failed to get session history: {str(e)}")
        return {
            "success": False,
            "data": None,
            "error": {
                "code": "GET_HISTORY_ERROR",
                "message": str(e)
            }
        }


@router.get("/health")
async def agent_health(
    agent_manager: AgentManager = Depends(get_agent_manager)
):
    """Check Agent health status.
    
    Returns:
        Health status information
    """
    try:
        health_status = {
            "status": "healthy",
            "agent": "ready",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Get performance stats if available
        if hasattr(agent_manager, 'get_performance_stats'):
            health_status["performance"] = agent_manager.get_performance_stats()
        
        return {
            "success": True,
            "data": health_status,
            "message": None
        }
    
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "success": False,
            "data": None,
            "error": {
                "code": "HEALTH_CHECK_FAILED",
                "message": str(e)
            }
        }
