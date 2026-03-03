"""Parallel tool execution for Agent optimization."""

import asyncio
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ToolExecutionTask:
    """Represents a tool execution task."""
    tool_name: str
    tool_func: Callable
    tool_input: Dict[str, Any]
    dependencies: Optional[List[str]] = None


@dataclass
class ToolExecutionResult:
    """Result of tool execution."""
    tool_name: str
    success: bool
    result: Any = None
    error: Optional[str] = None


class ParallelToolExecutor:
    """Executes tools in parallel with dependency management."""
    
    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
    
    async def execute_tasks(self, tasks: List[ToolExecutionTask]) -> Dict[str, ToolExecutionResult]:
        """Execute tasks with dependency management."""
        results = {}
        completed = set()
        
        # Build dependency graph
        task_map = {t.tool_name: t for t in tasks}
        
        while len(completed) < len(tasks):
            # Find tasks ready to execute
            ready_tasks = []
            for task in tasks:
                if task.tool_name not in completed:
                    deps = task.dependencies or []
                    if all(d in completed for d in deps):
                        ready_tasks.append(task)
            
            if not ready_tasks:
                break
            
            # Execute ready tasks concurrently
            semaphore = asyncio.Semaphore(self.max_concurrent)
            
            async def execute_with_semaphore(task):
                async with semaphore:
                    try:
                        result = await task.tool_func(**task.tool_input)
                        return ToolExecutionResult(
                            tool_name=task.tool_name,
                            success=True,
                            result=result
                        )
                    except Exception as e:
                        return ToolExecutionResult(
                            tool_name=task.tool_name,
                            success=False,
                            error=str(e)
                        )
            
            # Run tasks
            task_results = await asyncio.gather(
                *[execute_with_semaphore(t) for t in ready_tasks]
            )
            
            for result in task_results:
                results[result.tool_name] = result
                completed.add(result.tool_name)
        
        return results


class IndependentToolDetector:
    """Detects independent tools that can run in parallel."""
    
    def detect_independent_tools(self, tool_calls: List[Dict]) -> List[List[str]]:
        """Detect groups of independent tools."""
        groups = []
        current_group = []
        
        for tool_call in tool_calls:
            deps = tool_call.get("dependencies", [])
            if not deps:
                current_group.append(tool_call["tool_name"])
            else:
                if current_group:
                    groups.append(current_group)
                    current_group = []
                groups.append([tool_call["tool_name"]])
        
        if current_group:
            groups.append(current_group)
        
        return groups
