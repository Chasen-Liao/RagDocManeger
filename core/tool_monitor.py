"""
Tool Execution Monitor Module

This module provides comprehensive monitoring and logging for tool execution.
It tracks tool execution start/end events, records execution time, input parameters,
and output results with structured logging.

Requirements: 24.1, 24.2, 24.3, 24.4, 24.5
"""

import logging
import json
import time
from typing import Any, Dict, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import threading
from collections import deque

# Configure logger
logger = logging.getLogger(__name__)


class ExecutionStatus(str, Enum):
    """Execution status enumeration.
    
    **Validates: Requirements 24.1, 24.2**
    """
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class ToolExecutionLog:
    """Structured log entry for tool execution.
    
    **Validates: Requirements 24.1, 24.2, 24.5**
    
    Attributes:
        tool_name: Name of the tool being executed
        timestamp: ISO format timestamp when execution started
        status: Execution status (started, completed, failed, timeout)
        execution_time: Time taken to execute in seconds
        input_params: Input parameters passed to the tool
        output_result: Output result from the tool
        error_message: Error message if execution failed
        error_stack: Full error stack trace if execution failed
        context: Additional context information for debugging
    """
    tool_name: str
    timestamp: str
    status: ExecutionStatus
    execution_time: float
    input_params: Optional[Dict[str, Any]] = None
    output_result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_stack: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert log entry to dictionary."""
        data = asdict(self)
        data['status'] = self.status.value
        return data
    
    def to_json(self) -> str:
        """Convert log entry to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class ToolMonitor:
    """Monitor for tracking tool execution with structured logging.
    
    This class provides:
    - Tool execution start/end event logging
    - Execution time tracking
    - Input parameter and output result recording
    - Structured logging with tool name, timestamp, and status
    - Log filtering by tool name, time range, and status
    - Log rotation and archival support
    - Debug mode for detailed logging
    
    **Validates: Requirements 24.1, 24.2, 24.3, 24.4, 24.5**
    """
    
    def __init__(
        self,
        max_logs: int = 1000,
        log_dir: Optional[str] = None,
        enable_debug: bool = False,
        enable_file_logging: bool = True
    ):
        """Initialize ToolMonitor.
        
        Args:
            max_logs: Maximum number of logs to keep in memory
            log_dir: Directory for log files (if None, uses default logs directory)
            enable_debug: Enable debug mode for detailed logging
            enable_file_logging: Enable file-based logging
            
        **Validates: Requirements 24.1, 24.5**
        """
        self.max_logs = max_logs
        self.enable_debug = enable_debug
        self.enable_file_logging = enable_file_logging
        
        # In-memory log storage (thread-safe deque)
        self._logs: deque = deque(maxlen=max_logs)
        self._lock = threading.RLock()
        
        # Setup log directory
        if log_dir is None:
            log_dir = "logs"
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Log file paths
        self.execution_log_file = self.log_dir / "tool_execution.log"
        self.error_log_file = self.log_dir / "tool_errors.log"
        
        logger.info(
            f"ToolMonitor initialized with max_logs={max_logs}, "
            f"log_dir={self.log_dir}, debug={enable_debug}"
        )
    
    def log_execution_start(
        self,
        tool_name: str,
        input_params: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """Log the start of tool execution.
        
        Args:
            tool_name: Name of the tool
            input_params: Input parameters passed to the tool
            context: Additional context information
            
        Returns:
            Timestamp for tracking execution duration
            
        **Validates: Requirements 24.1, 24.5**
        """
        timestamp = time.time()
        iso_timestamp = datetime.utcnow().isoformat()
        
        log_entry = ToolExecutionLog(
            tool_name=tool_name,
            timestamp=iso_timestamp,
            status=ExecutionStatus.STARTED,
            execution_time=0.0,
            input_params=input_params,
            context=context
        )
        
        with self._lock:
            self._logs.append(log_entry)
        
        logger.info(
            f"[{tool_name}] Execution started at {iso_timestamp}"
        )
        
        if self.enable_debug and input_params:
            logger.debug(
                f"[{tool_name}] Input parameters: {json.dumps(input_params, ensure_ascii=False)}"
            )
        
        return timestamp
    
    def log_execution_end(
        self,
        tool_name: str,
        start_time: float,
        output_result: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log the successful end of tool execution.
        
        Args:
            tool_name: Name of the tool
            start_time: Start timestamp from log_execution_start
            output_result: Output result from the tool
            context: Additional context information
            
        **Validates: Requirements 24.1, 24.2**
        """
        execution_time = time.time() - start_time
        iso_timestamp = datetime.utcnow().isoformat()
        
        log_entry = ToolExecutionLog(
            tool_name=tool_name,
            timestamp=iso_timestamp,
            status=ExecutionStatus.COMPLETED,
            execution_time=execution_time,
            output_result=output_result,
            context=context
        )
        
        with self._lock:
            self._logs.append(log_entry)
        
        logger.info(
            f"[{tool_name}] Execution completed in {execution_time:.2f}s"
        )
        
        if self.enable_debug and output_result:
            logger.debug(
                f"[{tool_name}] Output result: {json.dumps(output_result, ensure_ascii=False)}"
            )
        
        if self.enable_file_logging:
            self._write_to_file(
                self.execution_log_file,
                log_entry
            )
    
    def log_execution_error(
        self,
        tool_name: str,
        start_time: float,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log tool execution failure.
        
        Args:
            tool_name: Name of the tool
            start_time: Start timestamp from log_execution_start
            error: The exception that occurred
            context: Additional context information
            
        **Validates: Requirements 24.2**
        """
        execution_time = time.time() - start_time
        iso_timestamp = datetime.utcnow().isoformat()
        
        import traceback
        error_stack = traceback.format_exc()
        
        log_entry = ToolExecutionLog(
            tool_name=tool_name,
            timestamp=iso_timestamp,
            status=ExecutionStatus.FAILED,
            execution_time=execution_time,
            error_message=str(error),
            error_stack=error_stack,
            context=context
        )
        
        with self._lock:
            self._logs.append(log_entry)
        
        logger.error(
            f"[{tool_name}] Execution failed after {execution_time:.2f}s: {str(error)}"
        )
        
        if self.enable_debug:
            logger.debug(
                f"[{tool_name}] Error stack:\n{error_stack}"
            )
        
        if self.enable_file_logging:
            self._write_to_file(
                self.error_log_file,
                log_entry
            )
    
    def log_execution_timeout(
        self,
        tool_name: str,
        start_time: float,
        timeout_seconds: float,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log tool execution timeout.
        
        Args:
            tool_name: Name of the tool
            start_time: Start timestamp from log_execution_start
            timeout_seconds: Timeout duration in seconds
            context: Additional context information
            
        **Validates: Requirements 24.2**
        """
        execution_time = time.time() - start_time
        iso_timestamp = datetime.utcnow().isoformat()
        
        log_entry = ToolExecutionLog(
            tool_name=tool_name,
            timestamp=iso_timestamp,
            status=ExecutionStatus.TIMEOUT,
            execution_time=execution_time,
            error_message=f"Execution timeout after {timeout_seconds}s",
            context=context
        )
        
        with self._lock:
            self._logs.append(log_entry)
        
        logger.warning(
            f"[{tool_name}] Execution timeout after {timeout_seconds}s"
        )
        
        if self.enable_file_logging:
            self._write_to_file(
                self.error_log_file,
                log_entry
            )
    
    def get_logs(
        self,
        tool_name: Optional[str] = None,
        status: Optional[ExecutionStatus] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[ToolExecutionLog]:
        """Get logs with optional filtering.
        
        Args:
            tool_name: Filter by tool name
            status: Filter by execution status
            start_time: Filter by start time (inclusive)
            end_time: Filter by end time (inclusive)
            limit: Maximum number of logs to return
            
        Returns:
            List of matching log entries
            
        **Validates: Requirements 24.3**
        """
        with self._lock:
            logs = list(self._logs)
        
        # Apply filters
        filtered_logs = logs
        
        if tool_name:
            filtered_logs = [
                log for log in filtered_logs
                if log.tool_name == tool_name
            ]
        
        if status:
            filtered_logs = [
                log for log in filtered_logs
                if log.status == status
            ]
        
        if start_time:
            start_iso = start_time.isoformat()
            filtered_logs = [
                log for log in filtered_logs
                if log.timestamp >= start_iso
            ]
        
        if end_time:
            end_iso = end_time.isoformat()
            filtered_logs = [
                log for log in filtered_logs
                if log.timestamp <= end_iso
            ]
        
        # Apply limit
        if limit:
            filtered_logs = filtered_logs[-limit:]
        
        return filtered_logs
    
    def get_tool_stats(self, tool_name: str) -> Dict[str, Any]:
        """Get execution statistics for a specific tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Dictionary containing statistics
            
        **Validates: Requirements 24.1, 24.3**
        """
        logs = self.get_logs(tool_name=tool_name)
        
        if not logs:
            return {
                "tool_name": tool_name,
                "total_executions": 0,
                "successful": 0,
                "failed": 0,
                "timeout": 0,
                "average_execution_time": 0.0,
                "min_execution_time": 0.0,
                "max_execution_time": 0.0
            }
        
        successful = [log for log in logs if log.status == ExecutionStatus.COMPLETED]
        failed = [log for log in logs if log.status == ExecutionStatus.FAILED]
        timeout = [log for log in logs if log.status == ExecutionStatus.TIMEOUT]
        
        execution_times = [log.execution_time for log in successful]
        
        # Calculate success rate based on completed + failed executions
        total_executions = len(successful) + len(failed) + len(timeout)
        success_rate = len(successful) / total_executions if total_executions > 0 else 0.0
        
        return {
            "tool_name": tool_name,
            "total_executions": len(logs),
            "successful": len(successful),
            "failed": len(failed),
            "timeout": len(timeout),
            "success_rate": success_rate,
            "average_execution_time": sum(execution_times) / len(execution_times) if execution_times else 0.0,
            "min_execution_time": min(execution_times) if execution_times else 0.0,
            "max_execution_time": max(execution_times) if execution_times else 0.0
        }
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get execution statistics for all tools.
        
        Returns:
            Dictionary mapping tool names to their statistics
            
        **Validates: Requirements 24.1, 24.3**
        """
        with self._lock:
            logs = list(self._logs)
        
        tool_names = set(log.tool_name for log in logs)
        stats = {}
        
        for tool_name in tool_names:
            stats[tool_name] = self.get_tool_stats(tool_name)
        
        return stats
    
    def clear_logs(self, tool_name: Optional[str] = None) -> int:
        """Clear logs from memory.
        
        Args:
            tool_name: If specified, only clear logs for this tool
            
        Returns:
            Number of logs cleared
            
        **Validates: Requirements 24.4**
        """
        with self._lock:
            if tool_name:
                original_count = len(self._logs)
                self._logs = deque(
                    (log for log in self._logs if log.tool_name != tool_name),
                    maxlen=self.max_logs
                )
                cleared = original_count - len(self._logs)
            else:
                cleared = len(self._logs)
                self._logs.clear()
        
        logger.info(f"Cleared {cleared} logs" + (f" for tool '{tool_name}'" if tool_name else ""))
        return cleared
    
    def export_logs(
        self,
        filepath: str,
        tool_name: Optional[str] = None,
        status: Optional[ExecutionStatus] = None
    ) -> int:
        """Export logs to a JSON file.
        
        Args:
            filepath: Path to export file
            tool_name: Optional filter by tool name
            status: Optional filter by status
            
        Returns:
            Number of logs exported
            
        **Validates: Requirements 24.4**
        """
        logs = self.get_logs(tool_name=tool_name, status=status)
        
        export_data = {
            "exported_at": datetime.utcnow().isoformat(),
            "total_logs": len(logs),
            "logs": [log.to_dict() for log in logs]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Exported {len(logs)} logs to {filepath}")
        return len(logs)
    
    def _write_to_file(
        self,
        filepath: Path,
        log_entry: ToolExecutionLog
    ) -> None:
        """Write log entry to file.
        
        Args:
            filepath: Path to log file
            log_entry: Log entry to write
            
        **Validates: Requirements 24.4**
        """
        try:
            with open(filepath, 'a', encoding='utf-8') as f:
                f.write(log_entry.to_json() + "\n")
        except Exception as e:
            logger.error(f"Failed to write log to file {filepath}: {str(e)}")
    
    def rotate_logs(self, max_file_size_mb: int = 10) -> None:
        """Rotate log files when they exceed max size.
        
        Args:
            max_file_size_mb: Maximum file size in MB before rotation
            
        **Validates: Requirements 24.4**
        """
        for log_file in [self.execution_log_file, self.error_log_file]:
            if log_file.exists():
                file_size_mb = log_file.stat().st_size / (1024 * 1024)
                
                if file_size_mb > max_file_size_mb:
                    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                    backup_file = log_file.parent / f"{log_file.stem}_{timestamp}.log"
                    log_file.rename(backup_file)
                    logger.info(f"Rotated log file {log_file} to {backup_file}")


# Global monitor instance
_tool_monitor: Optional[ToolMonitor] = None


def get_tool_monitor() -> ToolMonitor:
    """Get or create the global ToolMonitor instance.
    
    Returns:
        Global ToolMonitor instance
    """
    global _tool_monitor
    if _tool_monitor is None:
        _tool_monitor = ToolMonitor()
    return _tool_monitor


def set_tool_monitor(monitor: ToolMonitor) -> None:
    """Set the global ToolMonitor instance.
    
    Args:
        monitor: ToolMonitor instance to use globally
    """
    global _tool_monitor
    _tool_monitor = monitor
