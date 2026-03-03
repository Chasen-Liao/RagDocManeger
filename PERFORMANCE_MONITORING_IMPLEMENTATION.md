# Performance Monitoring Implementation

## Overview

This document describes the comprehensive performance monitoring system implemented for the RagDocMan Agent system. The system tracks Agent execution time, monitors resource usage (memory, CPU), collects performance metrics, and provides debug mode for detailed logging.

**Requirements Addressed**: 20.1, 20.2, 20.3, 20.4, 20.5

## Architecture

### Components

#### 1. PerformanceMonitor Class
The core monitoring component that tracks Agent execution performance.

**Location**: `RagDocMan/core/performance_monitor.py`

**Key Features**:
- Execution time tracking for Agent calls
- Resource usage monitoring (memory, CPU)
- Performance metrics collection
- Debug mode for detailed logging
- Execution profile recording and analysis
- Profile export and persistence

#### 2. Data Models

**ResourceSnapshot**: Captures system resource state at a point in time
- `timestamp`: ISO format timestamp
- `memory_mb`: System memory usage in MB
- `memory_percent`: Memory usage as percentage
- `cpu_percent`: CPU usage as percentage
- `process_memory_mb`: Process-specific memory in MB

**PerformanceMetric**: Records individual performance measurements
- `metric_type`: Type of metric (execution_time, memory_usage, cpu_usage, tool_call_count, intermediate_steps)
- `timestamp`: When metric was recorded
- `value`: Metric value
- `unit`: Unit of measurement
- `context`: Additional context information

**AgentExecutionProfile**: Complete execution profile for an Agent invocation
- `session_id`: Session identifier
- `user_input`: User input text
- `start_time`: Execution start timestamp
- `end_time`: Execution end timestamp
- `total_execution_time`: Total execution time in seconds
- `tool_calls`: List of tool calls made
- `tool_execution_times`: Execution time for each tool
- `resource_snapshots`: Resource usage snapshots
- `metrics`: Collected performance metrics
- `debug_info`: Debug information (if debug mode enabled)
- `error`: Error message if execution failed

### Integration with AgentManager

The PerformanceMonitor is integrated into the AgentManager class to automatically track all Agent executions.

**Initialization**:
```python
agent_manager = AgentManager(
    llm_provider=llm_provider,
    tools=tools,
    memory=memory,
    config=config,
    enable_performance_monitoring=True,  # Enable monitoring
    enable_debug=True  # Enable debug mode
)
```

**Automatic Tracking**:
- Each `ainvoke()` call automatically starts performance monitoring
- Execution time is tracked from start to end
- Resource snapshots are taken at start and end
- Tool calls are recorded with their execution times
- Metrics are collected throughout execution
- Debug information is recorded if debug mode is enabled

## Features

### 1. Execution Time Tracking (Requirement 20.1)

The system tracks total execution time for each Agent invocation.

**Implementation**:
```python
execution_id = monitor.start_execution(
    session_id="session_123",
    user_input="What is the capital of France?"
)

# ... execution happens ...

profile = monitor.end_execution(execution_id)
print(f"Total execution time: {profile.total_execution_time}s")
```

**Metrics Collected**:
- Total execution time
- Individual tool execution times
- Execution time statistics (average, min, max)

### 2. Resource Usage Monitoring (Requirement 20.2)

The system monitors system and process-level resource usage.

**Monitored Resources**:
- System memory usage (MB and percentage)
- CPU usage (percentage)
- Process-specific memory usage (MB)

**Implementation**:
```python
profile = monitor.end_execution(execution_id)

for snapshot in profile.resource_snapshots:
    print(f"Memory: {snapshot.memory_mb:.1f}MB ({snapshot.memory_percent:.1f}%)")
    print(f"CPU: {snapshot.cpu_percent:.1f}%")
    print(f"Process Memory: {snapshot.process_memory_mb:.1f}MB")
```

**Resource Snapshots**:
- Initial snapshot taken at execution start
- Final snapshot taken at execution end
- Snapshots can be taken at intervals during execution

### 3. Performance Metrics Collection (Requirement 20.3)

The system collects various performance metrics during execution.

**Metric Types**:
- `EXECUTION_TIME`: Total execution time
- `MEMORY_USAGE`: Memory usage in MB
- `CPU_USAGE`: CPU usage percentage
- `TOOL_CALL_COUNT`: Number of tool calls
- `INTERMEDIATE_STEPS`: Number of intermediate steps

**Recording Metrics**:
```python
monitor.record_metric(
    execution_id,
    MetricType.EXECUTION_TIME,
    2.5,
    "seconds"
)

monitor.record_metric(
    execution_id,
    MetricType.TOOL_CALL_COUNT,
    3,
    "count"
)
```

### 4. Debug Mode (Requirement 20.5)

Debug mode enables detailed logging of intermediate steps and execution details.

**Enabling Debug Mode**:
```python
monitor = PerformanceMonitor(
    enable_debug=True
)

# Or in AgentManager
agent_manager = AgentManager(
    ...,
    enable_debug=True
)
```

**Debug Information**:
- User input details
- Tool call information
- Intermediate step details
- Resource usage details
- Custom debug info

**Recording Debug Info**:
```python
monitor.add_debug_info(execution_id, "intent", "query")
monitor.add_debug_info(execution_id, "entities", ["France", "capital"])
monitor.add_debug_info(execution_id, "step_1", "initialized")
```

### 5. Performance Statistics (Requirement 20.4)

The system provides comprehensive performance statistics.

**Statistics Available**:
```python
stats = monitor.get_execution_stats()

# Returns:
{
    'total_executions': 10,
    'successful_executions': 9,
    'failed_executions': 1,
    'success_rate': 0.9,
    'average_execution_time': 2.3,
    'min_execution_time': 1.5,
    'max_execution_time': 3.2,
    'total_tool_calls': 25,
    'average_tool_calls_per_execution': 2.5,
    'average_memory_usage_mb': 512.3,
    'average_cpu_usage_percent': 15.2
}
```

**Filtering and Retrieval**:
```python
# Get profiles for specific session
profiles = monitor.get_profiles(session_id="session_123")

# Get profiles with limit
recent_profiles = monitor.get_profiles(limit=10)

# Get statistics for specific session
session_profiles = monitor.get_profiles(session_id="session_123")
```

### 6. Profile Export and Persistence (Requirement 20.4)

Execution profiles can be exported to JSON files for analysis.

**Exporting Profiles**:
```python
# Export all profiles
count = monitor.export_profiles("performance_report.json")

# Export profiles for specific session
count = monitor.export_profiles(
    "session_report.json",
    session_id="session_123"
)
```

**Export Format**:
```json
{
  "exported_at": "2024-01-01T12:00:00",
  "total_profiles": 1,
  "profiles": [
    {
      "session_id": "session_123",
      "user_input": "What is the capital of France?",
      "start_time": "2024-01-01T12:00:00",
      "end_time": "2024-01-01T12:00:02.5",
      "total_execution_time": 2.5,
      "tool_calls": ["search_tool", "rag_tool"],
      "tool_execution_times": {
        "search_tool": 0.5,
        "rag_tool": 1.2
      },
      "resource_snapshots": [...],
      "metrics": [...],
      "debug_info": {...},
      "error": null
    }
  ]
}
```

## Usage Examples

### Basic Usage

```python
from core.performance_monitor import PerformanceMonitor, MetricType

# Create monitor
monitor = PerformanceMonitor(
    enable_debug=True,
    enable_resource_monitoring=True
)

# Start execution
execution_id = monitor.start_execution(
    session_id="user_123",
    user_input="Search for information about Python"
)

# Record tool calls
monitor.record_tool_call(execution_id, "search_tool", 0.5)
monitor.record_tool_call(execution_id, "rag_tool", 1.2)

# Record metrics
monitor.record_metric(
    execution_id,
    MetricType.EXECUTION_TIME,
    1.7,
    "seconds"
)

# Add debug info
monitor.add_debug_info(execution_id, "intent", "search")

# End execution
profile = monitor.end_execution(execution_id)

# Access results
print(f"Execution time: {profile.total_execution_time}s")
print(f"Tool calls: {profile.tool_calls}")
print(f"Memory usage: {profile.resource_snapshots[0].memory_mb}MB")
```

### Integration with AgentManager

```python
from rag.agent_manager_core import AgentManager

# Create agent manager with performance monitoring
agent_manager = AgentManager(
    llm_provider=llm_provider,
    tools=tools,
    memory=memory,
    enable_performance_monitoring=True,
    enable_debug=True
)

# Execute agent (monitoring happens automatically)
result = await agent_manager.ainvoke(
    user_input="What is the capital of France?",
    session_id="session_123"
)

# Get performance statistics
stats = agent_manager.get_performance_stats()
print(f"Average execution time: {stats['average_execution_time']:.2f}s")

# Get session profiles
profiles = agent_manager.get_session_performance_profiles("session_123")

# Export performance data
agent_manager.export_performance_data("performance_report.json")
```

### Analyzing Performance

```python
# Get all statistics
stats = monitor.get_execution_stats()

# Analyze by session
session_profiles = monitor.get_profiles(session_id="session_123")
total_time = sum(p.total_execution_time for p in session_profiles)
avg_time = total_time / len(session_profiles) if session_profiles else 0

# Analyze resource usage
all_snapshots = []
for profile in session_profiles:
    all_snapshots.extend(profile.resource_snapshots)

avg_memory = sum(s.memory_mb for s in all_snapshots) / len(all_snapshots)
avg_cpu = sum(s.cpu_percent for s in all_snapshots) / len(all_snapshots)

print(f"Session {session_id}:")
print(f"  Total executions: {len(session_profiles)}")
print(f"  Average execution time: {avg_time:.2f}s")
print(f"  Average memory: {avg_memory:.1f}MB")
print(f"  Average CPU: {avg_cpu:.1f}%")
```

## Configuration

### PerformanceMonitor Configuration

```python
monitor = PerformanceMonitor(
    max_profiles=100,              # Max profiles to keep in memory
    log_dir="logs",                # Directory for log files
    enable_debug=False,            # Enable debug mode
    enable_resource_monitoring=True,  # Monitor resource usage
    resource_sample_interval=0.5   # Resource sampling interval (seconds)
)
```

### AgentManager Configuration

```python
agent_manager = AgentManager(
    llm_provider=llm_provider,
    tools=tools,
    memory=memory,
    config=config,
    enable_performance_monitoring=True,  # Enable monitoring
    enable_debug=False                   # Enable debug mode
)
```

## Performance Considerations

### Memory Usage
- Each execution profile is stored in memory (deque with max size)
- Resource snapshots are taken at start and end by default
- Debug info is only collected when debug mode is enabled
- Profiles are automatically limited by `max_profiles` parameter

### CPU Usage
- Resource monitoring uses `psutil` library
- CPU sampling interval can be configured
- Resource monitoring can be disabled if not needed

### Optimization Tips
1. Disable debug mode in production for better performance
2. Disable resource monitoring if not needed
3. Set appropriate `max_profiles` limit
4. Export and clear old profiles periodically
5. Use session-based filtering for large datasets

## Testing

Comprehensive tests are provided in `RagDocMan/tests/test_performance_monitor.py`.

**Test Coverage**:
- Data model creation and serialization
- Execution tracking (start, record, end)
- Tool call recording
- Metric collection
- Debug info recording
- Resource monitoring
- Profile retrieval and filtering
- Statistics calculation
- Profile export
- Profile clearing
- Debug mode behavior
- Resource monitoring disable
- Max profiles limit
- Global instance management
- Integration workflows

**Running Tests**:
```bash
pytest RagDocMan/tests/test_performance_monitor.py -v
```

## Logging

The PerformanceMonitor uses Python's logging module for detailed logging.

**Log Levels**:
- `INFO`: Execution start/end, profile export
- `DEBUG`: Detailed execution info, resource snapshots, debug info
- `WARNING`: Timeouts, resource monitoring failures
- `ERROR`: Execution failures, file write failures

**Log Files**:
- `logs/agent_performance.log`: Performance profiles
- `logs/agent_metrics.log`: Performance metrics

## Future Enhancements

Potential improvements for future versions:
1. Real-time performance dashboard
2. Performance alerts and thresholds
3. Distributed tracing support
4. Performance comparison and trending
5. Automatic performance optimization suggestions
6. Integration with monitoring systems (Prometheus, Grafana)
7. Performance profiling with flame graphs
8. Cost analysis for cloud-based LLM calls

## Troubleshooting

### Resource Monitoring Not Working
- Ensure `psutil` library is installed
- Check system permissions for resource access
- Verify `enable_resource_monitoring=True`

### Debug Info Not Appearing
- Ensure `enable_debug=True` in PerformanceMonitor or AgentManager
- Check that `add_debug_info()` is being called
- Verify debug info is being added before `end_execution()`

### Performance Profiles Not Persisting
- Check that `log_dir` directory exists and is writable
- Verify `export_profiles()` is being called
- Check file system permissions

### Memory Usage Growing
- Reduce `max_profiles` limit
- Call `clear_profiles()` periodically
- Disable debug mode if not needed
- Disable resource monitoring if not needed

## References

- **Requirements**: 20.1, 20.2, 20.3, 20.4, 20.5
- **Related Components**: AgentManager, ToolMonitor
- **Dependencies**: psutil, logging, json, dataclasses
