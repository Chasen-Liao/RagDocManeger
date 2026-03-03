"""
Tests for Performance Monitor Module

Tests for Agent execution performance monitoring, resource usage tracking,
metrics collection, and debug mode functionality.

Requirements: 20.1, 20.2, 20.3, 20.4, 20.5
"""

import pytest
import time
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

from core.performance_monitor import (
    PerformanceMonitor,
    MetricType,
    ResourceSnapshot,
    PerformanceMetric,
    AgentExecutionProfile,
    get_performance_monitor,
    set_performance_monitor
)


class TestResourceSnapshot:
    """Tests for ResourceSnapshot data class."""
    
    def test_resource_snapshot_creation(self):
        """Test creating a resource snapshot."""
        snapshot = ResourceSnapshot(
            timestamp=datetime.utcnow().isoformat(),
            memory_mb=512.5,
            memory_percent=25.0,
            cpu_percent=15.5,
            process_memory_mb=128.3
        )
        
        assert snapshot.memory_mb == 512.5
        assert snapshot.memory_percent == 25.0
        assert snapshot.cpu_percent == 15.5
        assert snapshot.process_memory_mb == 128.3
    
    def test_resource_snapshot_to_dict(self):
        """Test converting resource snapshot to dictionary."""
        snapshot = ResourceSnapshot(
            timestamp="2024-01-01T00:00:00",
            memory_mb=512.5,
            memory_percent=25.0,
            cpu_percent=15.5,
            process_memory_mb=128.3
        )
        
        data = snapshot.to_dict()
        assert data['memory_mb'] == 512.5
        assert data['memory_percent'] == 25.0
        assert data['cpu_percent'] == 15.5
        assert data['process_memory_mb'] == 128.3


class TestPerformanceMetric:
    """Tests for PerformanceMetric data class."""
    
    def test_metric_creation(self):
        """Test creating a performance metric."""
        metric = PerformanceMetric(
            metric_type=MetricType.EXECUTION_TIME,
            timestamp=datetime.utcnow().isoformat(),
            value=2.5,
            unit="seconds"
        )
        
        assert metric.metric_type == MetricType.EXECUTION_TIME
        assert metric.value == 2.5
        assert metric.unit == "seconds"
    
    def test_metric_to_dict(self):
        """Test converting metric to dictionary."""
        metric = PerformanceMetric(
            metric_type=MetricType.MEMORY_USAGE,
            timestamp="2024-01-01T00:00:00",
            value=512.5,
            unit="MB"
        )
        
        data = metric.to_dict()
        assert data['metric_type'] == "memory_usage"
        assert data['value'] == 512.5
        assert data['unit'] == "MB"


class TestAgentExecutionProfile:
    """Tests for AgentExecutionProfile data class."""
    
    def test_profile_creation(self):
        """Test creating an execution profile."""
        profile = AgentExecutionProfile(
            session_id="session_123",
            user_input="What is the capital of France?",
            start_time=datetime.utcnow().isoformat(),
            total_execution_time=2.5
        )
        
        assert profile.session_id == "session_123"
        assert profile.user_input == "What is the capital of France?"
        assert profile.total_execution_time == 2.5
    
    def test_profile_to_json(self):
        """Test converting profile to JSON."""
        profile = AgentExecutionProfile(
            session_id="session_123",
            user_input="Test query",
            start_time="2024-01-01T00:00:00",
            total_execution_time=1.5
        )
        
        json_str = profile.to_json()
        data = json.loads(json_str)
        
        assert data['session_id'] == "session_123"
        assert data['user_input'] == "Test query"
        assert data['total_execution_time'] == 1.5


class TestPerformanceMonitor:
    """Tests for PerformanceMonitor class.
    
    **Validates: Requirements 20.1, 20.2, 20.3, 20.4, 20.5**
    """
    
    @pytest.fixture
    def monitor(self):
        """Create a performance monitor for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = PerformanceMonitor(
                max_profiles=10,
                log_dir=tmpdir,
                enable_debug=True,
                enable_resource_monitoring=True
            )
            yield monitor
    
    def test_monitor_initialization(self, monitor):
        """Test monitor initialization.
        
        **Validates: Requirement 20.1**
        """
        assert monitor.max_profiles == 10
        assert monitor.enable_debug is True
        assert monitor.enable_resource_monitoring is True
        assert monitor.log_dir.exists()
    
    def test_start_execution(self, monitor):
        """Test starting execution tracking.
        
        **Validates: Requirement 20.1**
        """
        execution_id = monitor.start_execution(
            session_id="session_123",
            user_input="Test query"
        )
        
        assert execution_id is not None
        assert "session_123" in execution_id
    
    def test_record_tool_call(self, monitor):
        """Test recording tool calls.
        
        **Validates: Requirement 20.1, 20.3**
        """
        execution_id = monitor.start_execution(
            session_id="session_123",
            user_input="Test query"
        )
        
        monitor.record_tool_call(execution_id, "search_tool", 1.5)
        monitor.record_tool_call(execution_id, "rag_tool", 2.0)
        
        profile = monitor.end_execution(execution_id)
        
        assert len(profile.tool_calls) == 2
        assert "search_tool" in profile.tool_calls
        assert "rag_tool" in profile.tool_calls
        assert profile.tool_execution_times["search_tool"] == 1.5
        assert profile.tool_execution_times["rag_tool"] == 2.0
    
    def test_record_metric(self, monitor):
        """Test recording performance metrics.
        
        **Validates: Requirement 20.3, 20.4**
        """
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
        
        monitor.record_metric(
            execution_id,
            MetricType.TOOL_CALL_COUNT,
            3,
            "count"
        )
        
        profile = monitor.end_execution(execution_id)
        
        assert len(profile.metrics) == 2
        assert profile.metrics[0].metric_type == MetricType.EXECUTION_TIME
        assert profile.metrics[0].value == 2.5
        assert profile.metrics[1].metric_type == MetricType.TOOL_CALL_COUNT
        assert profile.metrics[1].value == 3
    
    def test_add_debug_info(self, monitor):
        """Test adding debug information.
        
        **Validates: Requirement 20.5**
        """
        execution_id = monitor.start_execution(
            session_id="session_123",
            user_input="Test query"
        )
        
        monitor.add_debug_info(execution_id, "step_1", "initialized")
        monitor.add_debug_info(execution_id, "step_2", "processing")
        
        profile = monitor.end_execution(execution_id)
        
        assert profile.debug_info is not None
        assert profile.debug_info["step_1"] == "initialized"
        assert profile.debug_info["step_2"] == "processing"
    
    def test_execution_time_tracking(self, monitor):
        """Test execution time tracking.
        
        **Validates: Requirement 20.1**
        """
        execution_id = monitor.start_execution(
            session_id="session_123",
            user_input="Test query"
        )
        
        # Simulate some work
        time.sleep(0.1)
        
        profile = monitor.end_execution(execution_id)
        
        assert profile.total_execution_time >= 0.1
        assert profile.total_execution_time < 1.0  # Should be quick
    
    def test_resource_monitoring(self, monitor):
        """Test resource usage monitoring.
        
        **Validates: Requirement 20.2**
        """
        execution_id = monitor.start_execution(
            session_id="session_123",
            user_input="Test query"
        )
        
        profile = monitor.end_execution(execution_id)
        
        # Should have at least initial and final snapshots
        assert len(profile.resource_snapshots) >= 1
        
        # Check snapshot structure
        snapshot = profile.resource_snapshots[0]
        assert snapshot.memory_mb > 0
        assert 0 <= snapshot.memory_percent <= 100
        assert 0 <= snapshot.cpu_percent <= 100
        assert snapshot.process_memory_mb > 0
    
    def test_get_profiles(self, monitor):
        """Test retrieving execution profiles.
        
        **Validates: Requirement 20.1, 20.3**
        """
        # Create multiple executions
        for i in range(3):
            execution_id = monitor.start_execution(
                session_id=f"session_{i}",
                user_input=f"Query {i}"
            )
            time.sleep(0.05)
            monitor.end_execution(execution_id)
        
        # Get all profiles
        all_profiles = monitor.get_profiles()
        assert len(all_profiles) == 3
        
        # Get profiles for specific session
        session_profiles = monitor.get_profiles(session_id="session_0")
        assert len(session_profiles) == 1
        assert session_profiles[0].session_id == "session_0"
    
    def test_get_execution_stats(self, monitor):
        """Test getting execution statistics.
        
        **Validates: Requirement 20.1, 20.3**
        """
        # Create executions
        for i in range(3):
            execution_id = monitor.start_execution(
                session_id="session_123",
                user_input=f"Query {i}"
            )
            monitor.record_tool_call(execution_id, "tool_1", 0.5)
            monitor.record_tool_call(execution_id, "tool_2", 0.3)
            monitor.end_execution(execution_id)
        
        stats = monitor.get_execution_stats()
        
        assert stats['total_executions'] == 3
        assert stats['successful_executions'] == 3
        assert stats['failed_executions'] == 0
        assert stats['success_rate'] == 1.0
        assert stats['total_tool_calls'] == 6
        assert stats['average_tool_calls_per_execution'] == 2.0
        assert stats['average_execution_time'] > 0
    
    def test_execution_with_error(self, monitor):
        """Test tracking execution with error.
        
        **Validates: Requirement 20.1, 20.2**
        """
        execution_id = monitor.start_execution(
            session_id="session_123",
            user_input="Test query"
        )
        
        profile = monitor.end_execution(
            execution_id,
            error="Test error occurred"
        )
        
        assert profile.error == "Test error occurred"
        
        # Check stats
        stats = monitor.get_execution_stats()
        assert stats['failed_executions'] == 1
        assert stats['success_rate'] == 0.0
    
    def test_export_profiles(self, monitor):
        """Test exporting profiles to file.
        
        **Validates: Requirement 20.4**
        """
        # Create execution
        execution_id = monitor.start_execution(
            session_id="session_123",
            user_input="Test query"
        )
        monitor.record_tool_call(execution_id, "tool_1", 1.0)
        monitor.end_execution(execution_id)
        
        # Export
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            export_file = f.name
        
        try:
            count = monitor.export_profiles(export_file)
            assert count == 1
            
            # Verify file content
            with open(export_file, 'r') as f:
                data = json.load(f)
            
            assert data['total_profiles'] == 1
            assert len(data['profiles']) == 1
            assert data['profiles'][0]['session_id'] == "session_123"
        finally:
            Path(export_file).unlink()
    
    def test_clear_profiles(self, monitor):
        """Test clearing profiles.
        
        **Validates: Requirement 20.4**
        """
        # Create executions
        for i in range(3):
            execution_id = monitor.start_execution(
                session_id=f"session_{i}",
                user_input=f"Query {i}"
            )
            monitor.end_execution(execution_id)
        
        # Clear specific session
        cleared = monitor.clear_profiles(session_id="session_0")
        assert cleared == 1
        
        # Verify
        remaining = monitor.get_profiles()
        assert len(remaining) == 2
        
        # Clear all
        cleared = monitor.clear_profiles()
        assert cleared == 2
        
        remaining = monitor.get_profiles()
        assert len(remaining) == 0
    
    def test_debug_mode_disabled(self):
        """Test that debug info is not collected when debug mode is off."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = PerformanceMonitor(
                log_dir=tmpdir,
                enable_debug=False
            )
            
            execution_id = monitor.start_execution(
                session_id="session_123",
                user_input="Test query"
            )
            
            monitor.add_debug_info(execution_id, "step_1", "value")
            
            profile = monitor.end_execution(execution_id)
            
            # Debug info should be None when debug mode is off
            assert profile.debug_info is None
    
    def test_resource_monitoring_disabled(self):
        """Test that resource monitoring can be disabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = PerformanceMonitor(
                log_dir=tmpdir,
                enable_resource_monitoring=False
            )
            
            execution_id = monitor.start_execution(
                session_id="session_123",
                user_input="Test query"
            )
            
            profile = monitor.end_execution(execution_id)
            
            # Should have no resource snapshots
            assert len(profile.resource_snapshots) == 0
    
    def test_max_profiles_limit(self):
        """Test that max_profiles limit is enforced.
        
        **Validates: Requirement 20.4**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = PerformanceMonitor(
                max_profiles=5,
                log_dir=tmpdir
            )
            
            # Create more than max_profiles
            for i in range(10):
                execution_id = monitor.start_execution(
                    session_id="session_123",
                    user_input=f"Query {i}"
                )
                monitor.end_execution(execution_id)
            
            profiles = monitor.get_profiles()
            assert len(profiles) == 5  # Should be limited to max_profiles
    
    def test_global_monitor_instance(self):
        """Test global monitor instance management."""
        # Get default instance
        monitor1 = get_performance_monitor()
        monitor2 = get_performance_monitor()
        
        # Should be same instance
        assert monitor1 is monitor2
        
        # Set new instance
        with tempfile.TemporaryDirectory() as tmpdir:
            new_monitor = PerformanceMonitor(log_dir=tmpdir)
            set_performance_monitor(new_monitor)
            
            monitor3 = get_performance_monitor()
            assert monitor3 is new_monitor
            assert monitor3 is not monitor1


class TestPerformanceMonitorIntegration:
    """Integration tests for PerformanceMonitor.
    
    **Validates: Requirements 20.1, 20.2, 20.3, 20.4, 20.5**
    """
    
    def test_complete_execution_workflow(self):
        """Test complete execution workflow with all features."""
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
            
            # Simulate tool calls
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
            
            # Add debug info
            monitor.add_debug_info(execution_id, "intent", "query")
            monitor.add_debug_info(execution_id, "entities", ["France", "capital"])
            
            # End execution
            profile = monitor.end_execution(execution_id)
            
            # Verify profile
            assert profile.session_id == "session_123"
            assert profile.user_input == "What is the capital of France?"
            assert len(profile.tool_calls) == 2
            assert len(profile.metrics) == 2
            assert len(profile.resource_snapshots) >= 1
            assert profile.debug_info is not None
            assert profile.error is None
            
            # Verify stats
            stats = monitor.get_execution_stats()
            assert stats['total_executions'] == 1
            assert stats['successful_executions'] == 1
            assert stats['total_tool_calls'] == 2
    
    def test_multiple_sessions_tracking(self):
        """Test tracking multiple sessions concurrently."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = PerformanceMonitor(log_dir=tmpdir)
            
            # Create executions for different sessions
            execution_ids = []
            for session_num in range(3):
                for query_num in range(2):
                    execution_id = monitor.start_execution(
                        session_id=f"session_{session_num}",
                        user_input=f"Query {query_num}"
                    )
                    execution_ids.append(execution_id)
                    monitor.record_tool_call(execution_id, "tool_1", 0.5)
            
            # End all executions
            for execution_id in execution_ids:
                monitor.end_execution(execution_id)
            
            # Verify
            all_profiles = monitor.get_profiles()
            assert len(all_profiles) == 6
            
            session_0_profiles = monitor.get_profiles(session_id="session_0")
            assert len(session_0_profiles) == 2
            
            session_1_profiles = monitor.get_profiles(session_id="session_1")
            assert len(session_1_profiles) == 2
