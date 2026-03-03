# Tool Execution Monitor Implementation

## Overview

This document describes the implementation of comprehensive tool execution monitoring for the RagDocMan Agent system. The ToolMonitor class provides structured logging, execution time tracking, and detailed monitoring capabilities for all tool executions.

## Requirements Addressed

- **Requirement 24.1**: Record execution time, input parameters, and output results
- **Requirement 24.2**: Record detailed error stack and context information on failures
- **Requirement 24.3**: Support filtering logs by tool name, time range, and status
- **Requirement 24.4**: Implement log rotation and archival mechanisms
- **Requirement 24.5**: Support debug mode for detailed logging

## Architecture

### Core Components

#### 1. ExecutionStatus Enum
Defines the possible states of tool execution:
- `STARTED`: Tool execution has begun
- `COMPLETED`: Tool execution completed successfully
- `FAILED`: Tool execution failed with an error
- `TIMEOUT`: Tool execution exceeded timeout limit

#### 2. ToolExecutionLog Dataclass
Structured log entry containing:
- `tool_name`: Name of the executed tool
- `timestamp`: ISO format timestamp of execution start
- `status`: Execution status (from ExecutionStatus enum)
- `execution_time`: Time taken to execute in seconds
- `input_params`: Input parameters passed to the tool
- `output_result`: Output result from the tool
- `error_message`: Error message if execution failed
- `error_stack`: Full error stack trace if execution failed
- `context`: Additional context information for debugging

#### 3. ToolMonitor Class
Main monitoring class providing:
- **Execution Logging**: Log tool execution start, end, errors, and timeouts
- **Log Filtering**: Filter logs by tool name, status, time range, and limit
- **Statistics**: Calculate execution statistics per tool
- **Log Management**: Clear, export, and rotate logs
- **File Logging**: Write logs to files with rotation support
- **Debug Mode**: Enable detailed logging for troubleshooting

### Integration with BaseRagDocManTool

The ToolMonitor is automatically integrated into the BaseRagDocManTool class:
- Both `_run()` and `_arun()` methods automatically log execution events
- Input parameters and output results are captured
- Execution time is tracked automatically
- Errors are logged with full stack traces

## Key Features

### 1. Structured Logging
All logs are structured with:
- Tool name for identification
- ISO format timestamp for precise timing
- Execution status for quick filtering
- Execution time for performance analysis
- Input/output data for debugging

### 2. Comprehensive Error Tracking
When tool execution fails:
- Error message is captured
- Full stack trace is recorded
- Context information is preserved
- Errors are logged to separate error log file

### 3. Flexible Log Filtering
Logs can be filtered by:
- Tool name: Get logs for specific tools
- Execution status: Filter by completed, failed, or timeout
- Time range: Filter logs within a date/time range
- Limit: Restrict number of results returned

### 4. Performance Statistics
For each tool, statistics include:
- Total executions (all log entries)
- Successful executions count
- Failed executions count
- Timeout executions count
- Success rate (successful / total executions)
- Average execution time
- Min/max execution times

### 5. Log Management
- **In-Memory Storage**: Configurable max logs (default 1000)
- **File Logging**: Optional file-based logging with separate error logs
- **Log Export**: Export logs to JSON format with optional filtering
- **Log Rotation**: Automatic rotation when log files exceed size limit
- **Log Clearing**: Clear all logs or logs for specific tools

### 6. Debug Mode
When enabled:
- Logs input parameters in debug level
- Logs output results in debug level
- Provides detailed execution flow information
- Useful for troubleshooting tool behavior

## Usage Examples

### Basic Usage

```python
from core.tool_monitor import get_tool_monitor

# Get the global monitor instance
monitor = get_tool_monitor()

# Log execution start
start_time = monitor.log_execution_start(
    tool_name="search_tool",
    input_params={"query": "test"}
)

# ... tool execution ...

# Log execution end
monitor.log_execution_end(
    tool_name="search_tool",
    start_time=start_time,
    output_result={"results": [...]}
)
```

### Filtering Logs

```python
# Get all logs for a specific tool
logs = monitor.get_logs(tool_name="search_tool")

# Get only failed executions
failed_logs = monitor.get_logs(status=ExecutionStatus.FAILED)

# Get logs within time range
from datetime import datetime, timedelta
start_time = datetime.utcnow() - timedelta(hours=1)
recent_logs = monitor.get_logs(start_time=start_time)

# Get last 10 logs
recent_logs = monitor.get_logs(limit=10)
```

### Getting Statistics

```python
# Get statistics for a specific tool
stats = monitor.get_tool_stats("search_tool")
print(f"Success rate: {stats['success_rate']:.2%}")
print(f"Average execution time: {stats['average_execution_time']:.2f}s")

# Get statistics for all tools
all_stats = monitor.get_all_stats()
for tool_name, stats in all_stats.items():
    print(f"{tool_name}: {stats['successful']}/{stats['total_executions']} successful")
```

### Exporting Logs

```python
# Export all logs to JSON
count = monitor.export_logs("logs_export.json")

# Export only failed logs
count = monitor.export_logs(
    "failed_logs.json",
    status=ExecutionStatus.FAILED
)

# Export logs for specific tool
count = monitor.export_logs(
    "search_tool_logs.json",
    tool_name="search_tool"
)
```

### Log Management

```python
# Clear all logs
cleared = monitor.clear_logs()

# Clear logs for specific tool
cleared = monitor.clear_logs(tool_name="search_tool")

# Rotate log files
monitor.rotate_logs(max_file_size_mb=10)
```

## File Structure

### Log Files
- `logs/tool_execution.log`: Successful tool executions
- `logs/tool_errors.log`: Failed tool executions and errors

### Log File Format
Each log entry is a JSON object on a single line:
```json
{
  "tool_name": "search_tool",
  "timestamp": "2024-01-15T10:30:45.123456",
  "status": "completed",
  "execution_time": 1.234,
  "input_params": {"query": "test"},
  "output_result": {"results": [...]},
  "error_message": null,
  "error_stack": null,
  "context": null
}
```

## Configuration

### ToolMonitor Initialization

```python
monitor = ToolMonitor(
    max_logs=1000,              # Maximum logs to keep in memory
    log_dir="logs",             # Directory for log files
    enable_debug=False,         # Enable debug logging
    enable_file_logging=True    # Enable file-based logging
)
```

### Global Monitor Instance

```python
from core.tool_monitor import get_tool_monitor, set_tool_monitor

# Get global instance
monitor = get_tool_monitor()

# Set custom global instance
custom_monitor = ToolMonitor(max_logs=5000)
set_tool_monitor(custom_monitor)
```

## Testing

Comprehensive test suite included in `tests/test_tool_monitor.py`:
- 25 test cases covering all functionality
- Tests for initialization, logging, filtering, statistics, and management
- Tests for file logging and debug mode
- All tests passing

## Performance Considerations

1. **In-Memory Storage**: Uses thread-safe deque with configurable max size
2. **File I/O**: Asynchronous file writing to avoid blocking
3. **Filtering**: Efficient filtering with early termination
4. **Statistics**: Cached calculation on demand
5. **Thread Safety**: All operations protected with locks

## Future Enhancements

1. Database persistence for long-term storage
2. Real-time monitoring dashboard
3. Alert system for failed executions
4. Performance trend analysis
5. Integration with external monitoring systems
6. Metrics export (Prometheus, etc.)

## Conclusion

The ToolMonitor implementation provides comprehensive monitoring and logging capabilities for tool execution in the RagDocMan Agent system. It enables detailed tracking of tool performance, error analysis, and system debugging while maintaining high performance and thread safety.
