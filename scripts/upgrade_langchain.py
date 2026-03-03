#!/usr/bin/env python
"""Script to verify LangChain 1.0 upgrade and compatibility."""

import sys
import subprocess
from pathlib import Path


def check_langchain_version():
    """Check installed LangChain version."""
    try:
        import langchain
        version = langchain.__version__
        print(f"✓ LangChain version: {version}")
        
        if version.startswith("1."):
            print("✓ LangChain 1.0+ detected")
            return True
        else:
            print("✗ LangChain version is not 1.0+")
            return False
    except ImportError:
        print("✗ LangChain not installed")
        return False


def check_langchain_core():
    """Check if langchain-core is installed."""
    try:
        import langchain_core
        version = langchain_core.__version__
        print(f"✓ langchain-core version: {version}")
        return True
    except ImportError:
        print("✗ langchain-core not installed")
        return False


def check_imports():
    """Check if new import paths work."""
    try:
        from langchain_core.tools import tool
        from langchain_core.prompts import PromptTemplate
        from langchain_core.language_models.llm import LLM
        print("✓ All new import paths work correctly")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False


def check_agent_imports():
    """Check if agent imports work."""
    try:
        from langchain.agents import AgentExecutor, create_react_agent
        print("✓ Agent imports work correctly")
        return True
    except ImportError as e:
        print(f"✗ Agent import error: {e}")
        return False


def install_dependencies():
    """Install or upgrade LangChain 1.0."""
    print("\n📦 Installing LangChain 1.0...")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--upgrade", "langchain==1.0.0"]
        )
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--upgrade", "langchain-core==0.1.0"]
        )
        print("✓ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Installation failed: {e}")
        return False


def main():
    """Run all checks."""
    print("🔍 LangChain 1.0 Upgrade Verification\n")
    
    checks = [
        ("LangChain Version", check_langchain_version),
        ("langchain-core", check_langchain_core),
        ("Import Paths", check_imports),
        ("Agent Imports", check_agent_imports),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n📋 Checking {name}...")
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"✗ Error: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*50)
    print("📊 Summary:")
    print("="*50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓" if result else "✗"
        print(f"{status} {name}")
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ All checks passed! LangChain 1.0 is ready to use.")
        return 0
    else:
        print("\n⚠️  Some checks failed. Running installation...")
        if install_dependencies():
            print("\n🔄 Please run this script again to verify the installation.")
            return 0
        else:
            print("\n❌ Installation failed. Please check your environment.")
            return 1


if __name__ == "__main__":
    sys.exit(main())
