"""
Unit Tests for Logging Functionality

Tests for Agent execution logging, log output format, performance metrics collection,
and debug mode activation.

Requirements: 18.1, 18.5
"""

import pytest
import logging
import json
import tempfile
import time
from pathlib import Path
from datetime import datetime
from io import StringIO
from unittest.mock import Mock, patch, MagicMock

from core.performance_monitor import (
    PerformanceMonitor,
    MetricType,
    ResourceSnapshot,
    PerformanceMetric,
    AgentExecutionProfile,
    get_performance_monitor,
    set_performance_monitor
)


class TestLogOutputFormat:
    """Tests for log output format and content.
    
    **Validates: Requirement 18.1**
    """
    
    @pytest.fixture
    def log_capture(self):
        """Capture log output for testing."""
        logger = logging.getLogger('RagDocMan')
        handler = logging.StreamHandler(StringIO())
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        
        yield handler
        
        logger.removeHandler(handler)
    
    def test_log_format_contains_timestamp(self, log_capture):
        """Test that log output contains timestamp.
        
        **Validates: Requirement 18.1**
        """
        logger = logging.getLogger('RagDocMan')
        logger.info("Test message")
        
        log_output = log_capture.stream.getvalue()
        
        # Check that timestamp is present
        assert len(log_output) > 0
        # Timestamp should be in ISO format or similar
        assert any(char.isdigit() for char in log_output)
    
    def test_log_format_contains_level(self, log_capture):
        """Test that log output contains log level.
        
        **Validates: Requirement 18.1**
        """
        logger = logging.getLogger('RagDocMan')
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        
        log_output = log_capture.stream.getvalue()
        
        # Check that log levels are present
        assert "INFO" in log_output or "info" in log_output.lower()
        assert "WARNING" in log_output or "warning" in log_output.lower()
        assert "ERROR" in log_output or "error" in log_output.lower()
    
    def test_log_format_contains_message(self, log_capture):
        """Test that log output contains the actual message.
        
        **Validates: Requirement 18.1**
        """
        logger = logging.getLogger('RagDocMan')
        test_message = "This is a test message"
        logger.info(test_message)
        
        log_output = log_capture.stream.getvalue()
        
        assert test_message in log_output
    
    def test_execution_start_log_format(self):
        """Test execution start log format.
        
        **Validates: Requirement 18.1**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = PerformanceMonitor(log_dir=tmpdir)
            
            execution_id = monitor.start_execution(
                session_id="session_123",
                user_input="Test query"
            )
            
            # Verify execution ID format
            assert execution_id is not None
            assert "session_123" in execution_id
            assert isinstance(execution_id, str)
    
    def test_execution_end_log_format(self):
        """Test execution end log format.
        
        **Validates: Requirement 18.1**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = PerformanceMonitor(log_dir=tmpdir)
            
            execution_id = monitor.start_execution(
                session_id="session_123",
                user_input="Test query"
            )
            
            profile = monitor.end_execution(execution_id)
            
            # Verify profile contains required fields
            assert profile.session_id == "session_123"
            assert profile.user_input == "Test query"
            assert profile.start_time is not None
            assert profile.end_time is not None
            assert profile.total_execution_time >= 0
    
    def test_tool_call_log_format(self):
        """Test tool call log format.
        
        **Validates: Requirement 18.1**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = PerformanceMonitor(log_dir=tmpdir)
            
            execution_id = monitor.start_execution(
                session_id="session_123",
                user_input="Test query"
            )
            
            # Record tool calls
            monitor.record_tool_call(execution_id, "search_tool", 1.5)
            monitor.record_tool_call(execution_id, "rag_tool", 2.0)
            
            profile = monitor.end_execution(execution_id)
            
            # Verify tool call logging
            assert len(profile.tool_calls) == 2
            assert "search_tool" in profile.tool_calls
            assert "rag_tool" in profile.tool_calls
            assert profile.tool_execution_times["search_tool"] == 1.5
            assert profile.tool_execution_times["rag_tool"] == 2.0
    
    def test_error_log_format(self):
        """Test error log format.
        
        **Validates: Requirement 18.1**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = PerformanceMonitor(log_dir=tmpdir)
            
            execution_id = monitor.start_execution(
                session_id="session_123",
                user_input="Test query"
            )
            
            error_message = "Test error occurred"
            profile = monitor.end_execution(execution_id, error=error_message)
            
            # Verify error is logged
            assert profile.error == error_message
            assert profile.error is not None
    
    def test_log_json_serialization(self):
        """Test that logs can be serialized to JSON.
        
        **Validates: Requirement 18.1**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = PerformanceMonitor(log_dir=tmpdir)
            
            execution_id = monitor.start_execution(
                session_id="session_123",
                user_input="Test query"
            )
            
            monitor.record_tool_call(execution_id, "tool_1", 1.0)
            profile = monitor.end_execution(execution_id)
            
            # Verify JSON serialization
            json_str = profile.to_json()
            data = json.loads(json_str)
            
            assert data['session_id'] == "session_123"
            assert data['user_input'] == "Test query"
            assert len(data['tool_calls']) == 1


class TestPerformanceMetricsCollection:
    """Tests for performance metrics collection.
    
    **Validates: Requirement 18.1, 18.5**
    """
    
    def test_execution_time_metric_collection(self):
        """Test execution time metric collection.
        
        **Validates: Requirement 18.1**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = PerformanceMonitor(log_dir=tmpdir)
            
            execution_id = monitor.start_execution(
                session_id="session_123",
                user_input="Test query"
            )
            
            # Simulate some work
            time.sleep(0.1)
            
            profile = monitor.end_execution(execution_id)
            
            # Verify execution time is recorded
            assert profile.total_execution_time >= 0.1
            assert profile.total_execution_time < 1.0
    
    def test_tool_execution_time_metric(self):
        """Test tool execution time metric collection.
        
        **Validates: Requirement 18.1**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = PerformanceMonitor(log_dir=tmpdir)
            
            execution_id = monitor.start_execution(
                session_id="session_123",
                user_input="Test query"
            )
            
            # Record tool execution times
            monitor.record_tool_call(execution_id, "search_tool", 0.5)
            monitor.record_tool_call(execution_id, "rag_tool", 1.2)
            monitor.record_tool_call(execution_id, "format_tool", 0.3)
            
            profile = monitor.end_execution(execution_id)
            
            # Verify tool execution times
            assert profile.tool_execution_times["search_tool"] == 0.5
            assert profile.tool_execution_times["rag_tool"] == 1.2
            assert profile.tool_execution_times["format_tool"] == 0.3
            
            # Verify total tool time
            total_tool_time = sum(profile.tool_execution_times.values())
            assert total_tool_time == 2.0
    
    def test_resource_usage_metric_collection(self):
        """Test resource usage metric collection.
        
        **Validates: Requirement 18.1, 18.5**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = PerformanceMonitor(
                log_dir=tmpdir,
                enable_resource_monitoring=True
            )
            
            execution_id = monitor.start_execution(
                session_id="session_123",
                user_input="Test query"
            )
            
            profile = monitor.end_execution(execution_id)
            
            # Verify resource snapshots are collected
            assert len(profile.resource_snapshots) >= 1
            
            # Verify resource snapshot structure
            snapshot = profile.resource_snapshots[0]
            assert snapshot.memory_mb > 0
            assert 0 <= snapshot.memory_percent <= 100
            assert 0 <= snapshot.cpu_percent <= 100
            assert snapshot.process_memory_mb > 0
    
    def test_metric_type_collection(self):
        """Test different metric types collection.
        
        **Validates: Requirement 18.1**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = PerformanceMonitor(log_dir=tmpdir)
            
            execution_id = monitor.start_execution(
                session_id="session_123",
                user_input="Test query"
            )
            
            # Record different metric types
            monitor.record_metric(
                execution_id,
                MetricType.EXECUTION_TIME,
                2.5,
                "seconds"
            )
            monitor.record_metric(
                execution_id,
                MetricType.MEMORY_USAGE,
                512.5,
                "MB"
            )
            monitor.record_metric(
                execution_id,
                MetricType.CPU_USAGE,
                15.5,
                "percent"
            )
            monitor.record_metric(
                execution_id,
                MetricType.TOOL_CALL_COUNT,
                3,
                "count"
            )
            
            profile = monitor.end_execution(execution_id)
            
            # Verify all metrics are collected
            assert len(profile.metrics) == 4
            
            # Verify metric values
            metrics_by_type = {m.metric_type: m for m in profile.metrics}
            assert metrics_by_type[MetricType.EXECUTION_TIME].value == 2.5
            assert metrics_by_type[MetricType.MEMORY_USAGE].value == 512.5
            assert metrics_by_type[MetricType.CPU_USAGE].value == 15.5
            assert metrics_by_type[MetricType.TOOL_CALL_COUNT].value == 3
    
    def test_metric_aggregation(self):
        """Test metric aggregation across multiple executions.
        
        **Validates: Requirement 18.1**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = PerformanceMonitor(log_dir=tmpdir)
            
            # Create multiple executions
            for i in range(3):
                execution_id = monitor.start_execution(
                    session_id="session_123",
                    user_input=f"Query {i}"
                )
                
                monitor.record_tool_call(execution_id, "tool_1", 0.5)
                monitor.record_tool_call(execution_id, "tool_2", 0.3)
                
                monitor.end_execution(execution_id)
            
            # Get statistics
            stats = monitor.get_execution_stats()
            
            # Verify aggregated metrics
            assert stats['total_executions'] == 3
            assert stats['total_tool_calls'] == 6
            assert stats['average_tool_calls_per_execution'] == 2.0
    
    def test_metric_timestamp_recording(self):
        """Test that metrics are recorded with timestamps.
        
        **Validates: Requirement 18.1**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = PerformanceMonitor(log_dir=tmpdir)
            
            execution_id = monitor.start_execution(
                session_id="session_123",
                user_input="Test query"
            )
            
            monitor.record_metric(
                execution_id,
                MetricType.EXECUTION_TIME,
                2.5,
                "seconds"
            )
            
            profile = monitor.end_execution(execution_id)
            
            # Verify timestamp is recorded
            assert len(profile.metrics) > 0
            metric = profile.metrics[0]
            assert metric.timestamp is not None
            
            # Verify timestamp is valid ISO format
            try:
                datetime.fromisoformat(metric.timestamp)
            except ValueError:
                pytest.fail("Metric timestamp is not in valid ISO format")


class TestDebugModeActivation:
    """Tests for debug mode activation.
    
    **Validates: Requirement 18.5**
    """
    
    def test_debug_mode_enabled(self):
        """Test debug mode can be enabled.
        
        **Validates: Requirement 18.5**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = PerformanceMonitor(
                log_dir=tmpdir,
                enable_debug=True
            )
            
            assert monitor.enable_debug is True
    
    def test_debug_mode_disabled(self):
        """Test debug mode can be disabled.
        
        **Validates: Requirement 18.5**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = PerformanceMonitor(
                log_dir=tmpdir,
                enable_debug=False
            )
            
            assert monitor.enable_debug is False
    
    def test_debug_info_collection_enabled(self):
        """Test debug info is collected when debug mode is enabled.
        
        **Validates: Requirement 18.5**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = PerformanceMonitor(
                log_dir=tmpdir,
                enable_debug=True
            )
            
            execution_id = monitor.start_execution(
                session_id="session_123",
                user_input="Test query"
            )
            
            # Add debug info
            monitor.add_debug_info(execution_id, "step_1", "initialized")
            monitor.add_debug_info(execution_id, "step_2", "processing")
            monitor.add_debug_info(execution_id, "step_3", "completed")
            
            profile = monitor.end_execution(execution_id)
            
            # Verify debug info is collected
            assert profile.debug_info is not None
            assert profile.debug_info["step_1"] == "initialized"
            assert profile.debug_info["step_2"] == "processing"
            assert profile.debug_info["step_3"] == "completed"
    
    def test_debug_info_not_collected_when_disabled(self):
        """Test debug info is not collected when debug mode is disabled.
        
        **Validates: Requirement 18.5**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = PerformanceMonitor(
                log_dir=tmpdir,
                enable_debug=False
            )
            
            execution_id = monitor.start_execution(
                session_id="session_123",
                user_input="Test query"
            )
            
            # Try to add debug info
            monitor.add_debug_info(execution_id, "step_1", "value")
            
            profile = monitor.end_execution(execution_id)
            
            # Verify debug info is not collected
            assert profile.debug_info is None
    
    def test_debug_info_contains_execution_details(self):
        """Test debug info contains detailed execution information.
        
        **Validates: Requirement 18.5**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = PerformanceMonitor(
                log_dir=tmpdir,
                enable_debug=True
            )
            
            execution_id = monitor.start_execution(
                session_id="session_123",
                user_input="What is the capital of France?"
            )
            
            # Add detailed debug info
            monitor.add_debug_info(execution_id, "intent", "query")
            monitor.add_debug_info(execution_id, "entities", ["France", "capital"])
            monitor.add_debug_info(execution_id, "confidence", 0.95)
            monitor.add_debug_info(execution_id, "tools_selected", ["search_tool", "rag_tool"])
            
            profile = monitor.end_execution(execution_id)
            
            # Verify debug info contains all details
            assert profile.debug_info["intent"] == "query"
            assert profile.debug_info["entities"] == ["France", "capital"]
            assert profile.debug_info["confidence"] == 0.95
            assert profile.debug_info["tools_selected"] == ["search_tool", "rag_tool"]
    
    def test_debug_mode_with_resource_monitoring(self):
        """Test debug mode works with resource monitoring.
        
        **Validates: Requirement 18.5**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = PerformanceMonitor(
                log_dir=tmpdir,
                enable_debug=True,
                enable_resource_monitoring=True
            )
            
            execution_id = monitor.start_execution(
                session_id="session_123",
                user_input="Test query"
            )
            
            monitor.add_debug_info(execution_id, "step_1", "initialized")
            
            profile = monitor.end_execution(execution_id)
            
            # Verify both debug info and resource monitoring are active
            assert profile.debug_info is not None
            assert len(profile.resource_snapshots) >= 1
    
    def test_debug_mode_with_metrics(self):
        """Test debug mode works with metrics collection.
        
        **Validates: Requirement 18.5**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = PerformanceMonitor(
                log_dir=tmpdir,
                enable_debug=True
            )
            
            execution_id = monitor.start_execution(
                session_id="session_123",
                user_input="Test query"
            )
            
            monitor.record_metric(
                execution_id,
                MetricType.EXECUTION_TIME,
                2.5,
                "seconds"
            )
            monitor.add_debug_info(execution_id, "metric_recorded", True)
            
            profile = monitor.end_execution(execution_id)
            
            # Verify both metrics and debug info are collected
            assert len(profile.metrics) > 0
            assert profile.debug_info is not None
            assert profile.debug_info["metric_recorded"] is True
    
    def test_debug_mode_toggle(self):
        """Test debug mode can be toggled.
        
        **Validates: Requirement 18.5**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = PerformanceMonitor(
                log_dir=tmpdir,
                enable_debug=False
            )
            
            # Initially disabled
            assert monitor.enable_debug is False
            
            # Enable debug mode
            monitor.enable_debug = True
            assert monitor.enable_debug is True
            
            # Disable debug mode
            monitor.enable_debug = False
            assert monitor.enable_debug is False


class TestLoggingIntegration:
    """Integration tests for logging functionality.
    
    **Validates: Requirements 18.1, 18.5**
    """
    
    def test_complete_logging_workflow(self):
        """Test complete logging workflow with all features.
        
        **Validates: Requirements 18.1, 18.5**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = PerformanceMonitor(
                log_dir=tmpdir,
                enable_debug=True,
                enable_resource_monitoring=True
            )
            
            # Start execution
            execution_id = monitor.start_execution(
                session_id="session_123",
                user_input="What is the capital of France?"
            )
            
            # Add debug info
            monitor.add_debug_info(execution_id, "intent", "query")
            monitor.add_debug_info(execution_id, "entities", ["France"])
            
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
            monitor.record_metric(
                execution_id,
                MetricType.TOOL_CALL_COUNT,
                2,
                "count"
            )
            
            # End execution
            profile = monitor.end_execution(execution_id)
            
            # Verify complete logging
            assert profile.session_id == "session_123"
            assert profile.user_input == "What is the capital of France?"
            assert len(profile.tool_calls) == 2
            assert len(profile.metrics) == 2
            assert len(profile.resource_snapshots) >= 1
            assert profile.debug_info is not None
            assert profile.debug_info["intent"] == "query"
            assert profile.error is None
    
    def test_logging_with_error_handling(self):
        """Test logging with error handling.
        
        **Validates: Requirements 18.1, 18.5**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = PerformanceMonitor(
                log_dir=tmpdir,
                enable_debug=True
            )
            
            execution_id = monitor.start_execution(
                session_id="session_123",
                user_input="Test query"
            )
            
            # Add debug info before error
            monitor.add_debug_info(execution_id, "step_1", "started")
            
            # Record error
            error_message = "Tool execution failed"
            profile = monitor.end_execution(execution_id, error=error_message)
            
            # Verify error is logged with debug info
            assert profile.error == error_message
            assert profile.debug_info is not None
            assert profile.debug_info["step_1"] == "started"
    
    def test_logging_export_format(self):
        """Test logging export format.
        
        **Validates: Requirements 18.1, 18.5**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = PerformanceMonitor(
                log_dir=tmpdir,
                enable_debug=True
            )
            
            # Create execution
            execution_id = monitor.start_execution(
                session_id="session_123",
                user_input="Test query"
            )
            
            monitor.add_debug_info(execution_id, "step_1", "value")
            monitor.record_tool_call(execution_id, "tool_1", 1.0)
            monitor.end_execution(execution_id)
            
            # Export profiles
            export_file = Path(tmpdir) / "export.json"
            monitor.export_profiles(str(export_file))
            
            # Verify export format
            with open(export_file, 'r') as f:
                data = json.load(f)
            
            assert 'exported_at' in data
            assert 'total_profiles' in data
            assert 'profiles' in data
            assert len(data['profiles']) == 1
            
            profile_data = data['profiles'][0]
            assert profile_data['session_id'] == "session_123"
            assert profile_data['user_input'] == "Test query"
            assert 'debug_info' in profile_data
            assert 'tool_calls' in profile_data
    
    def test_multiple_sessions_logging(self):
        """Test logging for multiple concurrent sessions.
        
        **Validates: Requirements 18.1, 18.5**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = PerformanceMonitor(
                log_dir=tmpdir,
                enable_debug=True
            )
            
            # Create executions for different sessions
            execution_ids = []
            for session_num in range(3):
                for query_num in range(2):
                    execution_id = monitor.start_execution(
                        session_id=f"session_{session_num}",
                        user_input=f"Query {query_num}"
                    )
                    
                    monitor.add_debug_info(
                        execution_id,
                        "session_num",
                        session_num
                    )
                    monitor.record_tool_call(execution_id, "tool_1", 0.5)
                    
                    execution_ids.append(execution_id)
            
            # End all executions
            for execution_id in execution_ids:
                monitor.end_execution(execution_id)
            
            # Verify logging for all sessions
            all_profiles = monitor.get_profiles()
            assert len(all_profiles) == 6
            
            # Verify session-specific logging
            session_0_profiles = monitor.get_profiles(session_id="session_0")
            assert len(session_0_profiles) == 2
            
            for profile in session_0_profiles:
                assert profile.session_id == "session_0"
                assert profile.debug_info["session_num"] == 0
    
    def test_logging_performance_impact(self):
        """Test that logging doesn't significantly impact performance.
        
        **Validates: Requirements 18.1, 18.5**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Test with logging enabled
            monitor_with_logging = PerformanceMonitor(
                log_dir=tmpdir,
                enable_debug=True,
                enable_resource_monitoring=True
            )
            
            start_time = time.time()
            for i in range(10):
                execution_id = monitor_with_logging.start_execution(
                    session_id="session_123",
                    user_input=f"Query {i}"
                )
                monitor_with_logging.add_debug_info(execution_id, "step", i)
                monitor_with_logging.record_tool_call(execution_id, "tool_1", 0.1)
                monitor_with_logging.end_execution(execution_id)
            
            logging_time = time.time() - start_time
            
            # Verify logging completes in reasonable time
            # 10 executions should complete in less than 5 seconds
            assert logging_time < 5.0
