"""
Agent Configuration Module

This module defines the configuration model for the AgentManager.
It provides settings for controlling agent behavior, execution parameters,
and memory management.

Requirements: 19.1, 19.2, 19.3, 19.4, 19.5
"""

from typing import Optional
from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    """
    Configuration for Agent behavior and execution.
    
    This model defines all configurable parameters for the AgentManager,
    including execution limits, error handling, logging, and memory settings.
    
    **Validates: Requirements 19.1, 19.2, 19.3, 19.4, 19.5**
    
    Attributes:
        max_iterations: Maximum number of agent iterations before stopping
        max_execution_time: Maximum execution time in seconds
        handle_parsing_errors: Whether to handle parsing errors gracefully
        verbose: Whether to enable verbose logging
        return_intermediate_steps: Whether to return intermediate execution steps
        memory_max_history: Maximum number of messages to retain in memory
        early_stopping_method: Method for early stopping ("force" or "generate")
    """
    
    max_iterations: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of agent iterations before stopping"
    )
    
    max_execution_time: int = Field(
        default=60,
        ge=1,
        le=300,
        description="Maximum execution time in seconds"
    )
    
    handle_parsing_errors: bool = Field(
        default=True,
        description="Whether to handle parsing errors gracefully"
    )
    
    verbose: bool = Field(
        default=False,
        description="Whether to enable verbose logging"
    )
    
    return_intermediate_steps: bool = Field(
        default=True,
        description="Whether to return intermediate execution steps"
    )
    
    memory_max_history: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of messages to retain in memory"
    )
    
    early_stopping_method: str = Field(
        default="force",
        description="Method for early stopping: 'force' or 'generate'"
    )
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "max_iterations": 10,
                "max_execution_time": 60,
                "handle_parsing_errors": True,
                "verbose": False,
                "return_intermediate_steps": True,
                "memory_max_history": 10,
                "early_stopping_method": "force"
            }
        }
