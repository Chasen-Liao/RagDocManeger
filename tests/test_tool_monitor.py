"""
Tests for Tool Execution Monitor

Tests the ToolMonitor class for:
- Tool execution start/end logging
- Execution time tracking
- Input parameter and output result recording
- Structured logging with tool name, timestamp, and status
- Log filtering by tool name, time range, and status
- Log rotation and archival support
- Debug mode for detailed logging

Requirements: 24.1, 24.2, 24.3, 24.4, 24.5
"""

import pytest
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import logging

from core.tool_monitor import (
    ToolMonitor,
    ToolExecutionLog,
    ExecutionStatus
)


class TestToolExecutionLog:
    """Test ToolExecutionLog data class.
    
    **Validates: Requirements 24.1, 24.2**
    """
    
    def test_log_creation(self):
        """Test creating a log entry."""
        log = ToolExecutionLog(
            tool_name="test_tool",
            timestamp=datetime.utcnow().isoformat(),
            status=ExecutionStatus.COMPLETED,
            execution_time=1.5,
            input_params={"key": "value"},
            output_result={"result": "success"}
        )
        
        assert log.tool_name == "test_tool"
        assert log.status == ExecutionStatus.COMPLETED
        assert log.execution_time == 1.5
        assert log.input_params == {"key": "value"}
        assert log.output_result == {"result": "success"}
    
    def test_log_to_dict(self):
        """Test converting log to dictionary."""
        log = ToolExecutionLog(
            tool_name="test_tool",
            timestamp="2024-01-01T00:00:00",
            status=ExecutionStatus.COMPLETED,
            execution_time=1.5
        )
        
        log_dict = log.to_dict()
        assert log_dict["tool_name"] == "test_tool"
        assert log_dict["status"] == "completed"
        assert log_dict["execution_time"] == 1.5
    
    def test_log_to_json(self):
        """Test converting log to JSON."""
        log = ToolExecutionLog(
            tool_name="test_tool",
            timestamp="2024-01-01T00:00:00",
            status=ExecutionStatus.COMPLETED,
            execution_time=1.5
        )
        
        json_str = log.to_json()
        parsed = json.loads(json_str)
        assert parsed["tool_name"] == "test_tool"
        assert parsed["status"] == "completed"


class TestToolMonitorInitialization:
    """Test ToolMonitor initialization.
    
    **Validates: Requirements 24.1, 24.4**
    """
    
    def test_initialization_with_defaults(self):
        """Test initializing with default parameters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = ToolMonitor(log_dir=tmpdir)
            
            assert monitor.max_logs == 1000
            assert monitor.enable_debug is False
            assert monitor.enable_file_logging is True
            assert monitor.log_dir == Path(tmpdir)
    
    def test_initialization_with_custom_params(self):
        """Test initializing with custom parameters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = ToolMonitor(
                max_logs=500,
                log_dir=tmpdir,
                enable_debug=True,
                enable_file_logging=False
            )
            
            assert monitor.max_logs == 500
            assert monitor.enable_debug is True
            assert monitor.enable_file_logging is False
    
    def test_log_directory_creation(self):
        """Test that log directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "logs" / "nested"
            monitor = ToolMonitor(log_dir=str(log_dir))
            
            assert log_dir.exists()


class TestExecutionLogging:
    """Test execution logging functionality.
    
    **Validates: Requirements 24.1, 24.2**
    """
    
    def test_log_execution_start(self):
        """Test logging execution start."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = ToolMonitor(log_dir=tmpdir, enable_file_logging=False)
            
            start_time = monitor.log_execution_start(
                tool_name="test_tool",
                input_params={"param": "value"}
            )
            
            assert isinstance(start_time, float)
            assert len(monitor._logs) == 1
            
            log = list(monitor._logs)[0]
            assert log.tool_name == "test_tool"
            assert log.status == ExecutionStatus.STARTED
            assert log.input_params == {"param": "value"}
    
    def test_log_execution_end(self):
        """Test logging execution end."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = ToolMonitor(log_dir=tmpdir, enable_file_logging=False)
            
            start_time = monitor.log_execution_start("test_tool")
            time.sleep(0.1)
            
            monitor.log_execution_end(
                tool_name="test_tool",
                start_time=start_time,
                output_result={"result": "success"}
            )
            
            assert len(monitor._logs) == 2
            
            logs = list(monitor._logs)
            end_log = logs[-1]
            assert end_log.tool_name == "test_tool"
            assert end_log.status == ExecutionStatus.COMPLETED
            assert end_log.execution_time >= 0.1
            assert end_log.output_result == {"result": "success"}
    
    def test_log_execution_error(self):
        """Test logging execution error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = ToolMonitor(log_dir=tmpdir, enable_file_logging=False)
            
            start_time = monitor.log_execution_start("test_tool")
            
            try:
                raise ValueError("Test error")
            except ValueError as e:
                monitor.log_execution_error(
                    tool_name="test_tool",
                    start_time=start_time,
                    error=e
                )
            
            assert len(monitor._logs) == 2
            
            logs = list(monitor._logs)
            error_log = logs[-1]
            assert error_log.tool_name == "test_tool"
            assert error_log.status == ExecutionStatus.FAILED
            assert "Test error" in error_log.error_message
            assert error_log.error_stack is not None
    
    def test_log_execution_timeout(self):
        """Test logging execution timeout."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = ToolMonitor(log_dir=tmpdir, enable_file_logging=False)
            
            start_time = monitor.log_execution_start("test_tool")
            
            monitor.log_execution_timeout(
                tool_name="test_tool",
                start_time=start_time,
                timeout_seconds=5.0
            )
            
            assert len(monitor._logs) == 2
            
            logs = list(monitor._logs)
            timeout_log = logs[-1]
            assert timeout_log.tool_name == "test_tool"
            assert timeout_log.status == ExecutionStatus.TIMEOUT
            assert "timeout" in timeout_log.error_message.lower()


class TestLogFiltering:
    """Test log filtering functionality.
    
    **Validates: Requirements 24.3**
    """
    
    def test_filter_by_tool_name(self):
        """Test filtering logs by tool name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = ToolMonitor(log_dir=tmpdir, enable_file_logging=False)
            
            # Create logs for different tools
            for i in range(3):
                start = monitor.log_execution_start("tool_a")
                monitor.log_execution_end("tool_a", start)
            
            for i in range(2):
                start = monitor.log_execution_start("tool_b")
                monitor.log_execution_end("tool_b", start)
            
            # Filter by tool_a (should get 6 logs: 3 start + 3 end)
            logs_a = monitor.get_logs(tool_name="tool_a")
            assert len(logs_a) == 6
            assert all(log.tool_name == "tool_a" for log in logs_a)
            
            # Filter by tool_b (should get 4 logs: 2 start + 2 end)
            logs_b = monitor.get_logs(tool_name="tool_b")
            assert len(logs_b) == 4
            assert all(log.tool_name == "tool_b" for log in logs_b)
    
    def test_filter_by_status(self):
        """Test filtering logs by status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = ToolMonitor(log_dir=tmpdir, enable_file_logging=False)
            
            # Create successful logs
            for i in range(2):
                start = monitor.log_execution_start("tool")
                monitor.log_execution_end("tool", start)
            
            # Create failed logs
            for i in range(1):
                start = monitor.log_execution_start("tool")
                try:
                    raise ValueError("Test")
                except ValueError as e:
                    monitor.log_execution_error("tool", start, e)
            
            # Filter by completed
            completed = monitor.get_logs(status=ExecutionStatus.COMPLETED)
            assert len(completed) == 2
            assert all(log.status == ExecutionStatus.COMPLETED for log in completed)
            
            # Filter by failed
            failed = monitor.get_logs(status=ExecutionStatus.FAILED)
            assert len(failed) == 1
            assert all(log.status == ExecutionStatus.FAILED for log in failed)
    
    def test_filter_with_limit(self):
        """Test filtering logs with limit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = ToolMonitor(log_dir=tmpdir, enable_file_logging=False)
            
            # Create multiple logs
            for i in range(10):
                start = monitor.log_execution_start("tool")
                monitor.log_execution_end("tool", start)
            
            # Get with limit
            logs = monitor.get_logs(limit=5)
            assert len(logs) == 5


class TestToolStatistics:
    """Test tool statistics functionality.
    
    **Validates: Requirements 24.1, 24.3**
    """
    
    def test_get_tool_stats(self):
        """Test getting statistics for a tool."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = ToolMonitor(log_dir=tmpdir, enable_file_logging=False)
            
            # Create successful logs
            for i in range(3):
                start = monitor.log_execution_start("test_tool")
                time.sleep(0.05)
                monitor.log_execution_end("test_tool", start)
            
            # Create failed log
            start = monitor.log_execution_start("test_tool")
            try:
                raise ValueError("Test")
            except ValueError as e:
                monitor.log_execution_error("test_tool", start, e)
            
            stats = monitor.get_tool_stats("test_tool")
            
            assert stats["tool_name"] == "test_tool"
            # 3 successful (start+end) + 1 failed (start+error) = 8 total logs
            assert stats["total_executions"] == 8
            # 3 completed + 1 failed = 4 executions, 3 successful
            assert stats["successful"] == 3
            assert stats["failed"] == 1
            assert stats["timeout"] == 0
            # Success rate is 3 successful / 4 total = 0.75
            assert stats["success_rate"] == 0.75
            assert stats["average_execution_time"] > 0
            assert stats["min_execution_time"] > 0
            assert stats["max_execution_time"] > 0
    
    def test_get_all_stats(self):
        """Test getting statistics for all tools."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = ToolMonitor(log_dir=tmpdir, enable_file_logging=False)
            
            # Create logs for multiple tools
            for tool_name in ["tool_a", "tool_b", "tool_c"]:
                for i in range(2):
                    start = monitor.log_execution_start(tool_name)
                    monitor.log_execution_end(tool_name, start)
            
            all_stats = monitor.get_all_stats()
            
            assert len(all_stats) == 3
            assert "tool_a" in all_stats
            assert "tool_b" in all_stats
            assert "tool_c" in all_stats
            
            for tool_name, stats in all_stats.items():
                # 2 executions (start+end) = 4 logs per tool
                assert stats["total_executions"] == 4
                assert stats["successful"] == 2


class TestLogManagement:
    """Test log management functionality.
    
    **Validates: Requirements 24.4**
    """
    
    def test_clear_all_logs(self):
        """Test clearing all logs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = ToolMonitor(log_dir=tmpdir, enable_file_logging=False)
            
            # Create logs
            for i in range(5):
                start = monitor.log_execution_start("tool")
                monitor.log_execution_end("tool", start)
            
            # 5 executions = 10 logs (5 start + 5 end)
            assert len(monitor._logs) == 10
            
            cleared = monitor.clear_logs()
            assert cleared == 10
            assert len(monitor._logs) == 0
    
    def test_clear_logs_by_tool(self):
        """Test clearing logs for a specific tool."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = ToolMonitor(log_dir=tmpdir, enable_file_logging=False)
            
            # Create logs for different tools
            for i in range(3):
                start = monitor.log_execution_start("tool_a")
                monitor.log_execution_end("tool_a", start)
            
            for i in range(2):
                start = monitor.log_execution_start("tool_b")
                monitor.log_execution_end("tool_b", start)
            
            # 3 + 2 executions = 10 logs
            assert len(monitor._logs) == 10
            
            cleared = monitor.clear_logs(tool_name="tool_a")
            # 3 executions for tool_a = 6 logs
            assert cleared == 6
            assert len(monitor._logs) == 4
            
            remaining_logs = list(monitor._logs)
            assert all(log.tool_name == "tool_b" for log in remaining_logs)
    
    def test_export_logs(self):
        """Test exporting logs to JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = ToolMonitor(log_dir=tmpdir, enable_file_logging=False)
            
            # Create logs
            for i in range(3):
                start = monitor.log_execution_start("tool")
                monitor.log_execution_end("tool", start)
            
            export_file = Path(tmpdir) / "export.json"
            count = monitor.export_logs(str(export_file))
            
            # 3 executions = 6 logs
            assert count == 6
            assert export_file.exists()
            
            # Verify exported data
            with open(export_file, 'r') as f:
                data = json.load(f)
            
            assert data["total_logs"] == 6
            assert len(data["logs"]) == 6
            assert all(log["tool_name"] == "tool" for log in data["logs"])
    
    def test_export_logs_with_filter(self):
        """Test exporting logs with filters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = ToolMonitor(log_dir=tmpdir, enable_file_logging=False)
            
            # Create logs for different tools
            for i in range(2):
                start = monitor.log_execution_start("tool_a")
                monitor.log_execution_end("tool_a", start)
            
            for i in range(3):
                start = monitor.log_execution_start("tool_b")
                monitor.log_execution_end("tool_b", start)
            
            export_file = Path(tmpdir) / "export.json"
            count = monitor.export_logs(
                str(export_file),
                tool_name="tool_a"
            )
            
            # 2 executions for tool_a = 4 logs
            assert count == 4
            
            with open(export_file, 'r') as f:
                data = json.load(f)
            
            assert data["total_logs"] == 4
            assert all(log["tool_name"] == "tool_a" for log in data["logs"])


class TestMaxLogsLimit:
    """Test max logs limit functionality.
    
    **Validates: Requirements 24.4**
    """
    
    def test_max_logs_limit(self):
        """Test that logs are limited to max_logs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = ToolMonitor(max_logs=5, log_dir=tmpdir, enable_file_logging=False)
            
            # Create more logs than max_logs
            for i in range(10):
                start = monitor.log_execution_start("tool")
                monitor.log_execution_end("tool", start)
            
            # Should only keep the last 5
            assert len(monitor._logs) == 5


class TestDebugMode:
    """Test debug mode functionality.
    
    **Validates: Requirements 24.5**
    """
    
    def test_debug_mode_enabled(self, caplog):
        """Test that debug mode logs additional details."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = ToolMonitor(
                log_dir=tmpdir,
                enable_debug=True,
                enable_file_logging=False
            )
            
            with caplog.at_level(logging.DEBUG):
                start = monitor.log_execution_start(
                    "test_tool",
                    input_params={"key": "value"}
                )
                monitor.log_execution_end(
                    "test_tool",
                    start,
                    output_result={"result": "success"}
                )
            
            # Check that debug logs were created
            debug_logs = [record for record in caplog.records if record.levelname == "DEBUG"]
            assert len(debug_logs) > 0
    
    def test_debug_mode_disabled(self, caplog):
        """Test that debug mode can be disabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = ToolMonitor(
                log_dir=tmpdir,
                enable_debug=False,
                enable_file_logging=False
            )
            
            with caplog.at_level(logging.DEBUG):
                start = monitor.log_execution_start(
                    "test_tool",
                    input_params={"key": "value"}
                )
                monitor.log_execution_end(
                    "test_tool",
                    start,
                    output_result={"result": "success"}
                )
            
            # Check that no debug logs were created for tool details
            debug_logs = [
                record for record in caplog.records
                if record.levelname == "DEBUG" and "Input parameters" in record.message
            ]
            assert len(debug_logs) == 0


class TestFileLogging:
    """Test file logging functionality.
    
    **Validates: Requirements 24.4**
    """
    
    def test_file_logging_enabled(self):
        """Test that logs are written to file when enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = ToolMonitor(
                log_dir=tmpdir,
                enable_file_logging=True
            )
            
            # Create successful log
            start = monitor.log_execution_start("tool")
            monitor.log_execution_end("tool", start)
            
            # Check that file was created
            assert monitor.execution_log_file.exists()
            
            # Verify content
            with open(monitor.execution_log_file, 'r') as f:
                content = f.read()
            
            assert "tool" in content
            assert "completed" in content
    
    def test_error_file_logging(self):
        """Test that errors are logged to error file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = ToolMonitor(
                log_dir=tmpdir,
                enable_file_logging=True
            )
            
            # Create error log
            start = monitor.log_execution_start("tool")
            try:
                raise ValueError("Test error")
            except ValueError as e:
                monitor.log_execution_error("tool", start, e)
            
            # Check that error file was created
            assert monitor.error_log_file.exists()
            
            # Verify content
            with open(monitor.error_log_file, 'r') as f:
                content = f.read()
            
            assert "tool" in content
            assert "failed" in content
            assert "Test error" in content
    
    def test_file_logging_disabled(self):
        """Test that logs are not written to file when disabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = ToolMonitor(
                log_dir=tmpdir,
                enable_file_logging=False
            )
            
            # Create logs
            start = monitor.log_execution_start("tool")
            monitor.log_execution_end("tool", start)
            
            # Check that file was not created
            assert not monitor.execution_log_file.exists()
