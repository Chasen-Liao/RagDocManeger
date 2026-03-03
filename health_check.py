#!/usr/bin/env python
"""Backend health check script."""

import sys
from pathlib import Path

def check_imports():
    """Check if all core imports are available."""
    print("=" * 60)
    print("CHECKING CORE IMPORTS")
    print("=" * 60)
    
    imports_to_check = [
        ("langchain", "LangChain"),
        ("langchain_core", "LangChain Core"),
        ("fastapi", "FastAPI"),
        ("sqlalchemy", "SQLAlchemy"),
        ("pydantic", "Pydantic"),
        ("chromadb", "ChromaDB"),
        ("numpy", "NumPy"),
        ("pandas", "Pandas"),
    ]
    
    results = {}
    for module_name, display_name in imports_to_check:
        try:
            __import__(module_name)
            print(f"✓ {display_name:20} - Available")
            results[display_name] = True
        except ImportError as e:
            print(f"✗ {display_name:20} - Missing: {e}")
            results[display_name] = False
    
    return results


def check_local_modules():
    """Check if local modules can be imported."""
    print("\n" + "=" * 60)
    print("CHECKING LOCAL MODULES")
    print("=" * 60)
    
    sys.path.insert(0, str(Path(__file__).parent))
    
    modules_to_check = [
        ("rag.conversation_memory", "ConversationMemory"),
        ("rag.vector_search_optimizer", "VectorSearchOptimizer"),
        ("rag.parallel_tool_executor", "ParallelToolExecutor"),
        ("config", "Configuration"),
        ("logger", "Logger"),
        ("database", "Database"),
        ("exceptions", "Exceptions"),
    ]
    
    results = {}
    for module_path, display_name in modules_to_check:
        try:
            __import__(module_path)
            print(f"✓ {display_name:30} - Available")
            results[display_name] = True
        except Exception as e:
            print(f"✗ {display_name:30} - Error: {str(e)[:40]}")
            results[display_name] = False
    
    return results


def check_conversation_memory():
    """Test ConversationMemory functionality."""
    print("\n" + "=" * 60)
    print("TESTING CONVERSATION MEMORY")
    print("=" * 60)
    
    try:
        from rag.conversation_memory import ConversationMemory
        
        memory = ConversationMemory(
            session_id="health_check",
            max_history=10,
            db_session=None
        )
        
        # Test add messages
        memory.add_user_message("Test question")
        memory.add_ai_message("Test answer")
        
        # Test get messages
        messages = memory.get_messages()
        
        if len(messages) == 2:
            print(f"✓ ConversationMemory - Functional (2 messages stored)")
            return True
        else:
            print(f"✗ ConversationMemory - Unexpected message count: {len(messages)}")
            return False
    except Exception as e:
        print(f"✗ ConversationMemory - Error: {e}")
        return False


def check_vector_search_optimizer():
    """Test VectorSearchOptimizer availability."""
    print("\n" + "=" * 60)
    print("TESTING VECTOR SEARCH OPTIMIZER")
    print("=" * 60)
    
    try:
        from rag.vector_search_optimizer import VectorSearchOptimizer
        optimizer = VectorSearchOptimizer()
        print(f"✓ VectorSearchOptimizer - Available")
        return True
    except Exception as e:
        print(f"✗ VectorSearchOptimizer - Error: {e}")
        return False


def check_parallel_tool_executor():
    """Test ParallelToolExecutor availability."""
    print("\n" + "=" * 60)
    print("TESTING PARALLEL TOOL EXECUTOR")
    print("=" * 60)
    
    try:
        from rag.parallel_tool_executor import ParallelToolExecutor
        executor = ParallelToolExecutor()
        print(f"✓ ParallelToolExecutor - Available")
        return True
    except Exception as e:
        print(f"✗ ParallelToolExecutor - Error: {e}")
        return False


def check_configuration():
    """Test configuration loading."""
    print("\n" + "=" * 60)
    print("TESTING CONFIGURATION")
    print("=" * 60)
    
    try:
        from config import settings
        
        required_attrs = [
            'database_url',
            'chroma_db_path',
            'log_level',
        ]
        
        missing = []
        for attr in required_attrs:
            if not hasattr(settings, attr):
                missing.append(attr)
        
        if missing:
            print(f"✗ Configuration - Missing attributes: {missing}")
            return False
        else:
            print(f"✓ Configuration - All required attributes present")
            print(f"  - Database: {settings.database_url}")
            print(f"  - Chroma Path: {settings.chroma_db_path}")
            print(f"  - Log Level: {settings.log_level}")
            return True
    except Exception as e:
        print(f"✗ Configuration - Error: {e}")
        return False


def check_logger():
    """Test logger initialization."""
    print("\n" + "=" * 60)
    print("TESTING LOGGER")
    print("=" * 60)
    
    try:
        from logger import logger
        
        if logger is not None:
            logger.info("Health check log message")
            print(f"✓ Logger - Initialized and functional")
            return True
        else:
            print(f"✗ Logger - Failed to initialize")
            return False
    except Exception as e:
        print(f"✗ Logger - Error: {e}")
        return False


def main():
    """Run all health checks."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "RAGDOCMAN BACKEND HEALTH CHECK" + " " * 13 + "║")
    print("╚" + "=" * 58 + "╝")
    
    results = {}
    
    # Check imports
    results['imports'] = check_imports()
    
    # Check local modules
    results['local_modules'] = check_local_modules()
    
    # Check functionality
    results['conversation_memory'] = check_conversation_memory()
    results['vector_search_optimizer'] = check_vector_search_optimizer()
    results['parallel_tool_executor'] = check_parallel_tool_executor()
    results['configuration'] = check_configuration()
    results['logger'] = check_logger()
    
    # Summary
    print("\n" + "=" * 60)
    print("HEALTH CHECK SUMMARY")
    print("=" * 60)
    
    total_checks = 0
    passed_checks = 0
    
    # Count import checks
    for status in results['imports'].values():
        total_checks += 1
        if status:
            passed_checks += 1
    
    # Count local module checks
    for status in results['local_modules'].values():
        total_checks += 1
        if status:
            passed_checks += 1
    
    # Count functionality checks
    for key in ['conversation_memory', 'vector_search_optimizer', 'parallel_tool_executor', 'configuration', 'logger']:
        total_checks += 1
        if results[key]:
            passed_checks += 1
    
    print(f"\nTotal Checks: {total_checks}")
    print(f"Passed: {passed_checks}")
    print(f"Failed: {total_checks - passed_checks}")
    print(f"Success Rate: {(passed_checks / total_checks * 100):.1f}%")
    
    if passed_checks == total_checks:
        print("\n✓ BACKEND IS HEALTHY")
        return 0
    elif passed_checks >= total_checks * 0.8:
        print("\n⚠ BACKEND IS PARTIALLY HEALTHY")
        return 1
    else:
        print("\n✗ BACKEND HAS ISSUES")
        return 2


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
