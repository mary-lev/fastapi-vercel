"""
Test Runner Script
Executes comprehensive test suites with proper reporting
"""

import pytest
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_unit_tests():
    """Run unit tests"""
    print("🧪 Running Unit Tests...")
    result = pytest.main([
        "tests/unit/",
        "-v",
        "--tb=short",
        "-m", "unit"
    ])
    return result == 0


def run_integration_tests():
    """Run integration tests"""
    print("🔗 Running Integration Tests...")
    result = pytest.main([
        "tests/integration/",
        "-v",
        "--tb=short",
        "-m", "integration"
    ])
    return result == 0


def run_security_tests():
    """Run security tests"""
    print("🔒 Running Security Tests...")
    result = pytest.main([
        "tests/security/",
        "-v",
        "--tb=short",
        "-m", "security"
    ])
    return result == 0


def run_all_tests():
    """Run all tests"""
    print("🚀 Running All Tests...")
    result = pytest.main([
        "tests/",
        "-v",
        "--tb=short",
        "--cov=.",
        "--cov-report=html:htmlcov",
        "--cov-report=term-missing"
    ])
    return result == 0


def run_critical_workflow_tests():
    """Run critical workflow tests only"""
    print("⚡ Running Critical Workflow Tests...")
    result = pytest.main([
        "tests/integration/test_code_execution_workflow.py",
        "tests/integration/test_authentication_workflow.py",
        "tests/security/test_comprehensive_security.py",
        "-v",
        "--tb=short"
    ])
    return result == 0


def run_performance_tests():
    """Run performance-focused tests"""
    print("📊 Running Performance Tests...")
    result = pytest.main([
        "tests/",
        "-v",
        "--tb=short",
        "-k", "performance or concurrent or timing",
        "--durations=10"
    ])
    return result == 0


def run_smoke_tests():
    """Run smoke tests for quick validation"""
    print("💨 Running Smoke Tests...")
    result = pytest.main([
        "tests/unit/test_basic.py",
        "tests/integration/test_solution_api.py::TestSolutionAPI::test_insert_task_solution_success",
        "tests/security/test_code_execution.py::TestCodeExecutionSecurity::test_safe_code_execution",
        "-v",
        "--tb=line"
    ])
    return result == 0


def main():
    """Main test runner"""
    if len(sys.argv) < 2:
        print("Usage: python test_runner.py [unit|integration|security|all|critical|performance|smoke]")
        sys.exit(1)
    
    test_type = sys.argv[1].lower()
    
    # Set test environment
    os.environ["NODE_ENV"] = "test"
    
    success = False
    
    if test_type == "unit":
        success = run_unit_tests()
    elif test_type == "integration":
        success = run_integration_tests()
    elif test_type == "security":
        success = run_security_tests()
    elif test_type == "all":
        success = run_all_tests()
    elif test_type == "critical":
        success = run_critical_workflow_tests()
    elif test_type == "performance":
        success = run_performance_tests()
    elif test_type == "smoke":
        success = run_smoke_tests()
    else:
        print(f"Unknown test type: {test_type}")
        sys.exit(1)
    
    if success:
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()