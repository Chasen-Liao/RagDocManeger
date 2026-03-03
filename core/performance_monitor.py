"""
Performance Monitor Module

This module provides comprehensive performance monitoring for Agent execution.
It tracks execution time, monitors resource usage (memory, CPU), collects
performance metrics, and provides debug mode for detailed logging.

Requirements: 20.1, 20.2, 20.3, 20.4, 20.5
"""

import logging
import json
import time
import psutil
import os
from typing import Any, Dict, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict, field
from enum import Enum
from pathlib import Path
import threading
from collections import deque

# Configure logger
logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Performance metric type enumeration.
    
    **Validates: Requirements 20.1, 20.2, 20.3**
    """
    EXECUTION_TIME = "execution_time"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"
    TOOL_CALL_COUNT = "tool_call_count"
    INTERMEDIATE_STEPS = "intermediate_steps"


@dataclass
class ResourceSnapshot:
    """Snapshot of system resource usage at a point in time.
    
    **Validates: Requirements 20.2**
    
    Attributes:
        timestamp: ISO format timestamp
        memory_mb: Memory usage in MB
        memory_percent: Memory usage as percentage of total
        cpu_percent: CPU usage as percentage
        process_memory_mb: Process-specific memory in MB
    """
    timestamp: str
    memory_mb: float
    memory_percent: float
    cpu_percent: float
    process_memory_mb: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class PerformanceMetric:
    """Performance metric for Agent execution.
    
    **Validates: Requirements 20.1, 20.2, 20.3, 20.4**
    
    Attributes:
        metric_type: Type of metric (execution_time, memory_usage, etc.)
        timestamp: ISO format timestamp
        value: Metric value
        unit: Unit of measurement
        context: Additional context information
    """
    metric_type: MetricType
    timestamp: str
    value: float
    unit: str
    context: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['metric_type'] = self.metric_type.value
        return data


@dataclass
class AgentExecutionProfile:
    """Complete execution profile for an Agent invocation.
    
    **Validates: Requirements 20.1, 20.2, 20.3, 20.4, 20.5**
    
    Attributes:
        session_id: Session identifier
        user_input: User input text
        start_time: Execution start timestamp
        end_time: Execution end timestamp
        total_execution_time: Total execution time in seconds
        tool_calls: List of tool calls made
        tool_execution_times: Execution time for each tool
        resource_snapshots: Resource usage snapshots
        metrics: Collected performance metrics
        debug_info: Debug information if debug mode enabled
        error: Error message if execution failed
    """
    session_id: str
    user_input: str
    start_time: str
    end_time: Optional[str] = None
    total_execution_time: float = 0.0
    tool_calls: List[str] = field(default_factory=list)
    tool_execution_times: Dict[str, float] = field(default_factory=dict)
    resource_snapshots: List[ResourceSnapshot] = field(default_factory=list)
    metrics: List[PerformanceMetric] = field(default_factory=list)
    debug_info: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['resource_snapshots'] = [s.to_dict() for s in self.resource_snapshots]
        data['metrics'] = [m.to_dict() for m in self.metrics]
        return data
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class PerformanceMonitor:
    """Monitor for tracking Agent execution performance.
    
    This class provides:
    - Agent execution time tracking
    - Resource usage monitoring (memory, CPU)
    - Performance metrics collection
    - Debug mode for detailed logging
    - Execution profile recording
    - Performance statistics and analysis
    
    **Validates: Requirements 20.1, 20.2, 20.3, 20.4, 20.5**
    """
    
    def __init__(
        self,
        max_profiles: int = 100,
        log_dir: Optional[str] = None,
        enable_debug: bool = False,
        enable_resource_monitoring: bool = True,
        resource_sample_interval: float = 0.5
    ):
        """Initialize PerformanceMonitor.
        
        Args:
            max_profiles: Maximum number of execution profiles to keep
            log_dir: Directory for performance logs
            enable_debug: Enable debug mode for detailed logging
            enable_resource_monitoring: Enable resource usage monitoring
            resource_sample_interval: Interval for resource sampling in seconds
            
        **Validates: Requirements 20.1, 20.4, 20.5**
        """
        self.max_profiles = max_profiles
        self.enable_debug = enable_debug
        self.enable_resource_monitoring = enable_resource_monitoring
        self.resource_sample_interval = resource_sample_interval
        
        # In-memory profile storage (thread-safe deque)
        self._profiles: deque = deque(maxlen=max_profiles)
        self._lock = threading.RLock()
        
        # Current execution tracking
        self._current_executions: Dict[str, Dict[str, Any]] = {}
        
        # Setup log directory
        if log_dir is None:
            log_dir = "logs"
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Log file paths
        self.performance_log_file = self.log_dir / "agent_performance.log"
        self.metrics_log_file = self.log_dir / "agent_metrics.log"
        
        # Get process for resource monitoring
        self._process = psutil.Process(os.getpid())
        
        logger.info(
            f"PerformanceMonitor initialized with max_profiles={max_profiles}, "
            f"log_dir={self.log_dir}, debug={enable_debug}, "
            f"resource_monitoring={enable_resource_monitoring}"
        )
    
    def start_execution(
        self,
        session_id: str,
        user_input: str
    ) -> str:
        """Start tracking an Agent execution.
        
        Args:
            session_id: Session identifier
            user_input: User input text
            
        Returns:
            Execution ID for tracking
            
        **Validates: Requirements 20.1, 20.2**
        """
        execution_id = f"{session_id}_{int(time.time() * 1000)}"
        start_time = datetime.utcnow().isoformat()
        
        execution_data = {
            'session_id': session_id,
            'user_input': user_input,
            'start_time': start_time,
            'start_timestamp': time.time(),
            'tool_calls': [],
            'tool_execution_times': {},
            'resource_snapshots': [],
            'metrics': [],
            'debug_info': {} if self.enable_debug else None
        }
        
        with self._lock:
            self._current_executions[execution_id] = execution_data
        
        # Take initial resource snapshot
        if self.enable_resource_monitoring:
            self._take_resource_snapshot(execution_id)
        
        logger.info(f"[{execution_id}] Agent execution started")
        
        if self.enable_debug:
            logger.debug(f"[{execution_id}] User input: {user_input}")
        
        return execution_id
    
    def record_tool_call(
        self,
        execution_id: str,
        tool_name: str,
        execution_time: float
    ) -> None:
        """Record a tool call during execution.
        
        Args:
            execution_id: Execution ID from start_execution
            tool_name: Name of the tool called
            execution_time: Time taken to execute the tool
            
        **Validates: Requirements 20.1, 20.3**
        """
        with self._lock:
            if execution_id not in self._current_executions:
                logger.warning(f"Execution {execution_id} not found")
                return
            
            execution_data = self._current_executions[execution_id]
            execution_data['tool_calls'].append(tool_name)
            execution_data['tool_execution_times'][tool_name] = execution_time
        
        logger.debug(f"[{execution_id}] Tool '{tool_name}' executed in {execution_time:.2f}s")
        
        if self.enable_debug:
            with self._lock:
                execution_data = self._current_executions[execution_id]
                if execution_data['debug_info'] is not None:
                    execution_data['debug_info']['last_tool_call'] = {
                        'tool_name': tool_name,
                        'execution_time': execution_time,
                        'timestamp': datetime.utcnow().isoformat()
                    }
    
    def record_metric(
        self,
        execution_id: str,
        metric_type: MetricType,
        value: float,
        unit: str,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record a performance metric.
        
        Args:
            execution_id: Execution ID from start_execution
            metric_type: Type of metric
            value: Metric value
            unit: Unit of measurement
            context: Additional context
            
        **Validates: Requirements 20.3, 20.4**
        """
        metric = PerformanceMetric(
            metric_type=metric_type,
            timestamp=datetime.utcnow().isoformat(),
            value=value,
            unit=unit,
            context=context
        )
        
        with self._lock:
            if execution_id not in self._current_executions:
                logger.warning(f"Execution {execution_id} not found")
                return
            
            execution_data = self._current_executions[execution_id]
            execution_data['metrics'].append(metric)
        
        logger.debug(f"[{execution_id}] Metric recorded: {metric_type.value}={value}{unit}")
    
    def add_debug_info(
        self,
        execution_id: str,
        key: str,
        value: Any
    ) -> None:
        """Add debug information to execution profile.
        
        Args:
            execution_id: Execution ID from start_execution
            key: Debug info key
            value: Debug info value
            
        **Validates: Requirements 20.5**
        """
        if not self.enable_debug:
            return
        
        with self._lock:
            if execution_id not in self._current_executions:
                logger.warning(f"Execution {execution_id} not found")
                return
            
            execution_data = self._current_executions[execution_id]
            if execution_data['debug_info'] is not None:
                execution_data['debug_info'][key] = value
        
        logger.debug(f"[{execution_id}] Debug info: {key}={value}")
    
    def end_execution(
        self,
        execution_id: str,
        error: Optional[str] = None
    ) -> Optional[AgentExecutionProfile]:
        """End tracking an Agent execution.
        
        Args:
            execution_id: Execution ID from start_execution
            error: Error message if execution failed
            
        Returns:
            AgentExecutionProfile with collected metrics
            
        **Validates: Requirements 20.1, 20.2, 20.3, 20.4**
        """
        with self._lock:
            if execution_id not in self._current_executions:
                logger.warning(f"Execution {execution_id} not found")
                return None
            
            execution_data = self._current_executions.pop(execution_id)
        
        # Take final resource snapshot
        if self.enable_resource_monitoring:
            self._take_resource_snapshot(execution_id, is_final=True)
            # Move snapshots from temporary storage
            if execution_id in self._current_executions:
                execution_data['resource_snapshots'] = self._current_executions[execution_id].get('resource_snapshots', [])
        
        end_time = datetime.utcnow().isoformat()
        total_execution_time = time.time() - execution_data['start_timestamp']
        
        profile = AgentExecutionProfile(
            session_id=execution_data['session_id'],
            user_input=execution_data['user_input'],
            start_time=execution_data['start_time'],
            end_time=end_time,
            total_execution_time=total_execution_time,
            tool_calls=execution_data['tool_calls'],
            tool_execution_times=execution_data['tool_execution_times'],
            resource_snapshots=execution_data.get('resource_snapshots', []),
            metrics=execution_data['metrics'],
            debug_info=execution_data['debug_info'],
            error=error
        )
        
        with self._lock:
            self._profiles.append(profile)
        
        logger.info(
            f"[{execution_id}] Agent execution completed in {total_execution_time:.2f}s"
        )
        
        if error:
            logger.error(f"[{execution_id}] Execution failed: {error}")
        
        # Write to file
        self._write_profile_to_file(profile)
        
        return profile
    
    def _take_resource_snapshot(
        self,
        execution_id: str,
        is_final: bool = False
    ) -> None:
        """Take a snapshot of current resource usage.
        
        Args:
            execution_id: Execution ID
            is_final: Whether this is the final snapshot
            
        **Validates: Requirements 20.2**
        """
        try:
            # Get system memory info
            memory_info = psutil.virtual_memory()
            memory_mb = memory_info.used / (1024 * 1024)
            memory_percent = memory_info.percent
            
            # Get CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Get process-specific memory
            process_memory_mb = self._process.memory_info().rss / (1024 * 1024)
            
            snapshot = ResourceSnapshot(
                timestamp=datetime.utcnow().isoformat(),
                memory_mb=memory_mb,
                memory_percent=memory_percent,
                cpu_percent=cpu_percent,
                process_memory_mb=process_memory_mb
            )
            
            with self._lock:
                if execution_id in self._current_executions:
                    self._current_executions[execution_id]['resource_snapshots'].append(snapshot)
            
            if self.enable_debug:
                logger.debug(
                    f"[{execution_id}] Resource snapshot: "
                    f"memory={memory_mb:.1f}MB ({memory_percent:.1f}%), "
                    f"cpu={cpu_percent:.1f}%, "
                    f"process_memory={process_memory_mb:.1f}MB"
                )
        except Exception as e:
            logger.error(f"Failed to take resource snapshot: {str(e)}")
    
    def get_profiles(
        self,
        session_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[AgentExecutionProfile]:
        """Get execution profiles with optional filtering.
        
        Args:
            session_id: Filter by session ID
            limit: Maximum number of profiles to return
            
        Returns:
            List of execution profiles
            
        **Validates: Requirements 20.1, 20.3**
        """
        with self._lock:
            profiles = list(self._profiles)
        
        if session_id:
            profiles = [p for p in profiles if p.session_id == session_id]
        
        if limit:
            profiles = profiles[-limit:]
        
        return profiles
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get overall execution statistics.
        
        Returns:
            Dictionary containing statistics
            
        **Validates: Requirements 20.1, 20.3**
        """
        with self._lock:
            profiles = list(self._profiles)
        
        if not profiles:
            return {
                'total_executions': 0,
                'successful_executions': 0,
                'failed_executions': 0,
                'average_execution_time': 0.0,
                'min_execution_time': 0.0,
                'max_execution_time': 0.0,
                'total_tool_calls': 0,
                'average_tool_calls_per_execution': 0.0,
                'average_memory_usage_mb': 0.0,
                'average_cpu_usage_percent': 0.0
            }
        
        successful = [p for p in profiles if p.error is None]
        failed = [p for p in profiles if p.error is not None]
        
        execution_times = [p.total_execution_time for p in profiles]
        total_tool_calls = sum(len(p.tool_calls) for p in profiles)
        
        # Calculate average resource usage
        all_snapshots = []
        for profile in profiles:
            all_snapshots.extend(profile.resource_snapshots)
        
        avg_memory = sum(s.memory_mb for s in all_snapshots) / len(all_snapshots) if all_snapshots else 0.0
        avg_cpu = sum(s.cpu_percent for s in all_snapshots) / len(all_snapshots) if all_snapshots else 0.0
        
        return {
            'total_executions': len(profiles),
            'successful_executions': len(successful),
            'failed_executions': len(failed),
            'success_rate': len(successful) / len(profiles) if profiles else 0.0,
            'average_execution_time': sum(execution_times) / len(execution_times) if execution_times else 0.0,
            'min_execution_time': min(execution_times) if execution_times else 0.0,
            'max_execution_time': max(execution_times) if execution_times else 0.0,
            'total_tool_calls': total_tool_calls,
            'average_tool_calls_per_execution': total_tool_calls / len(profiles) if profiles else 0.0,
            'average_memory_usage_mb': avg_memory,
            'average_cpu_usage_percent': avg_cpu
        }
    
    def export_profiles(
        self,
        filepath: str,
        session_id: Optional[str] = None
    ) -> int:
        """Export execution profiles to JSON file.
        
        Args:
            filepath: Path to export file
            session_id: Optional filter by session ID
            
        Returns:
            Number of profiles exported
            
        **Validates: Requirements 20.4**
        """
        profiles = self.get_profiles(session_id=session_id)
        
        export_data = {
            'exported_at': datetime.utcnow().isoformat(),
            'total_profiles': len(profiles),
            'profiles': [p.to_dict() for p in profiles]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Exported {len(profiles)} profiles to {filepath}")
        return len(profiles)
    
    def _write_profile_to_file(self, profile: AgentExecutionProfile) -> None:
        """Write execution profile to file.
        
        Args:
            profile: Execution profile to write
            
        **Validates: Requirements 20.4**
        """
        try:
            with open(self.performance_log_file, 'a', encoding='utf-8') as f:
                f.write(profile.to_json() + "\n")
        except Exception as e:
            logger.error(f"Failed to write profile to file: {str(e)}")
    
    def clear_profiles(self, session_id: Optional[str] = None) -> int:
        """Clear execution profiles.
        
        Args:
            session_id: If specified, only clear profiles for this session
            
        Returns:
            Number of profiles cleared
            
        **Validates: Requirements 20.4**
        """
        with self._lock:
            if session_id:
                original_count = len(self._profiles)
                self._profiles = deque(
                    (p for p in self._profiles if p.session_id != session_id),
                    maxlen=self.max_profiles
                )
                cleared = original_count - len(self._profiles)
            else:
                cleared = len(self._profiles)
                self._profiles.clear()
        
        logger.info(f"Cleared {cleared} profiles" + (f" for session '{session_id}'" if session_id else ""))
        return cleared


# Global monitor instance
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get or create the global PerformanceMonitor instance.
    
    Returns:
        Global PerformanceMonitor instance
    """
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


def set_performance_monitor(monitor: PerformanceMonitor) -> None:
    """Set the global PerformanceMonitor instance.
    
    Args:
        monitor: PerformanceMonitor instance to use globally
    """
    global _performance_monitor
    _performance_monitor = monitor
