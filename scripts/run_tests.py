#!/usr/bin/env python
"""
Simple test runner for CodeDjinn unit tests.

This script provides an easy way to run all or specific test modules
for the CodeDjinn project.
"""

import sys
import subprocess
import os
from pathlib import Path


def run_tests(test_pattern="", verbose=True):
    """
    Run pytest with the specified test pattern.
    
    Args:
        test_pattern: Pattern to match test files (default: all test files)
        verbose: Whether to run with verbose output
    """
    # Change to project root directory
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Build pytest command - use sys.executable to get current Python interpreter
    if test_pattern:
        cmd = [sys.executable, "-m", "pytest", f"tests/{test_pattern}"]
    else:
        cmd = [sys.executable, "-m", "pytest", "tests/"]
    
    if verbose:
        cmd.append("-v")
    
    # Add short traceback for cleaner output
    cmd.append("--tb=short")
    
    print(f"Running: {' '.join(cmd)}")
    print("=" * 60)
    
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode == 0
    except FileNotFoundError:
        print("Error: pytest not found. Install with: pip install pytest")
        return False


def main():
    """Main entry point for test runner."""
    if len(sys.argv) > 1:
        # Run specific test module
        test_module = sys.argv[1]
        if not test_module.startswith("test_"):
            test_module = f"test_{test_module}"
        if not test_module.endswith(".py"):
            test_module = f"{test_module}.py"
        
        print(f"Running tests for module: {test_module}")
        success = run_tests(test_module)
    else:
        # Run all tests
        print("Running all unit tests...")
        success = run_tests()
    
    if success:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()