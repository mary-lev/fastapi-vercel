#!/usr/bin/env python3
"""
End-to-End API Tests
Tests the actual running API to ensure all endpoints work correctly
Run with: python tests/e2e_test.py
"""

import requests
import json
import time
import sys
from typing import Dict, Any
from datetime import datetime


# Configuration
from config import settings

API_BASE_URL = settings.TEST_API_BASE_URL
TEST_USER_ID = "student1"  # Use a user that exists
TEST_TIMEOUT = 10

# Colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


class APITester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0

    def log_test(self, test_name: str, passed: bool, message: str = ""):
        """Log test result"""
        self.total_tests += 1
        if passed:
            self.passed_tests += 1
            print(f"{GREEN}✓{RESET} {test_name}")
            if message:
                print(f"  {message}")
        else:
            self.failed_tests += 1
            print(f"{RED}✗{RESET} {test_name}")
            if message:
                print(f"  {RED}{message}{RESET}")

        self.test_results.append(
            {"test": test_name, "passed": passed, "message": message, "timestamp": datetime.now().isoformat()}
        )

    def test_endpoint(
        self, method: str, endpoint: str, expected_status: int = 200, json_data: Dict = None, test_name: str = None
    ) -> Dict[str, Any]:
        """Test a single endpoint"""
        if test_name is None:
            test_name = f"{method} {endpoint}"

        url = f"{self.base_url}{endpoint}"

        try:
            if method == "GET":
                response = self.session.get(url, timeout=TEST_TIMEOUT)
            elif method == "POST":
                response = self.session.post(url, json=json_data, timeout=TEST_TIMEOUT)
            elif method == "PUT":
                response = self.session.put(url, json=json_data, timeout=TEST_TIMEOUT)
            elif method == "DELETE":
                response = self.session.delete(url, timeout=TEST_TIMEOUT)
            else:
                raise ValueError(f"Unsupported method: {method}")

            if response.status_code == expected_status:
                self.log_test(test_name, True, f"Status: {response.status_code}")
                return {"success": True, "data": response.json() if response.content else None}
            else:
                self.log_test(test_name, False, f"Expected {expected_status}, got {response.status_code}")
                return {"success": False, "error": response.text}

        except requests.exceptions.Timeout:
            self.log_test(test_name, False, "Request timed out")
            return {"success": False, "error": "Timeout"}
        except requests.exceptions.ConnectionError:
            self.log_test(test_name, False, "Connection failed")
            return {"success": False, "error": "Connection error"}
        except Exception as e:
            self.log_test(test_name, False, str(e))
            return {"success": False, "error": str(e)}

    def run_all_tests(self):
        """Run all test suites"""
        print(f"\n{BLUE}═══════════════════════════════════════════{RESET}")
        print(f"{BLUE}     E2E API Tests - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
        print(f"{BLUE}═══════════════════════════════════════════{RESET}\n")

        # Test suites
        self.test_health_endpoints()
        self.test_course_endpoints()
        self.test_compile_endpoint()
        self.test_submit_endpoints()
        self.test_user_endpoints()
        self.test_error_handling()
        self.test_performance()

        # Print summary
        self.print_summary()

    def test_health_endpoints(self):
        """Test system health endpoints"""
        print(f"\n{YELLOW}Testing Health Endpoints...{RESET}")

        self.test_endpoint("GET", "/", test_name="Root endpoint")
        self.test_endpoint("GET", "/health", test_name="Health check")
        self.test_endpoint("GET", "/api/v1", test_name="API v1 info")

    def test_course_endpoints(self):
        """Test course-related endpoints"""
        print(f"\n{YELLOW}Testing Course Endpoints...{RESET}")

        result = self.test_endpoint("GET", "/api/v1/courses/", test_name="Get all courses")

        if result["success"] and result["data"]:
            course_id = result["data"][0]["id"] if result["data"] else 1
            self.test_endpoint("GET", f"/api/v1/courses/{course_id}", test_name=f"Get course {course_id}")
            self.test_endpoint(
                "GET", f"/api/v1/courses/{course_id}/lessons/", test_name=f"Get lessons for course {course_id}"
            )

    def test_compile_endpoint(self):
        """Test code compilation"""
        print(f"\n{YELLOW}Testing Compile Endpoint...{RESET}")

        # Test successful compilation
        result = self.test_endpoint(
            "POST",
            f"/api/v1/students/{TEST_USER_ID}/compile",
            json_data={"code": "print('Hello, World!')", "language": "python"},
            test_name="Compile valid code",
        )

        if result["success"]:
            data = result["data"]
            if data.get("status") == "success" and "Hello, World!" in data.get("output", ""):
                print(f"  Output: {data['output'].strip()}")
            else:
                self.log_test("Output validation", False, "Unexpected output")

        # Test compilation with error
        self.test_endpoint(
            "POST",
            f"/api/v1/students/{TEST_USER_ID}/compile",
            json_data={"code": "print('Hello", "language": "python"},  # Missing closing quote
            test_name="Compile code with syntax error",
        )

        # Test empty code
        self.test_endpoint(
            "POST",
            f"/api/v1/students/{TEST_USER_ID}/compile",
            expected_status=400,
            json_data={"code": "", "language": "python"},
            test_name="Compile empty code (should fail)",
        )

    def test_submit_endpoints(self):
        """Test submission endpoints"""
        print(f"\n{YELLOW}Testing Submit Endpoints...{RESET}")

        # Test code submission
        result = self.test_endpoint(
            "POST",
            f"/api/v1/students/{TEST_USER_ID}/submit-code",
            json_data={"code": "print(42)", "task_id": 1, "language": "python"},
            test_name="Submit code solution",
        )

        if result["success"]:
            data = result["data"]
            print(f"  Feedback: {data.get('feedback', '')[:50]}...")

        # Test text submission
        result = self.test_endpoint(
            "POST",
            f"/api/v1/students/{TEST_USER_ID}/submit-text",
            json_data={"user_answer": "A variable is a container for storing data", "task_id": 1},
            test_name="Submit text answer",
        )

        if result["success"]:
            data = result["data"]
            print(f"  Is correct: {data.get('is_correct')}")

    def test_user_endpoints(self):
        """Test user-related endpoints"""
        print(f"\n{YELLOW}Testing User Endpoints...{RESET}")

        self.test_endpoint("GET", f"/api/v1/students/{TEST_USER_ID}/solutions", test_name="Get user solutions")

        self.test_endpoint("GET", f"/api/v1/students/{TEST_USER_ID}/profile", test_name="Get user profile")

        self.test_endpoint(
            "GET", f"/api/v1/students/{TEST_USER_ID}/courses/1/progress", test_name="Get user course progress"
        )

    def test_error_handling(self):
        """Test error handling"""
        print(f"\n{YELLOW}Testing Error Handling...{RESET}")

        # Test invalid JSON
        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/students/{TEST_USER_ID}/compile",
                data="invalid json",
                headers={"Content-Type": "application/json"},
                timeout=TEST_TIMEOUT,
            )
            if response.status_code == 422:
                self.log_test("Invalid JSON handling", True, "Returns 422")
            else:
                self.log_test("Invalid JSON handling", False, f"Expected 422, got {response.status_code}")
        except Exception as e:
            self.log_test("Invalid JSON handling", False, str(e))

        # Test missing required fields
        self.test_endpoint(
            "POST",
            f"/api/v1/students/{TEST_USER_ID}/submit-code",
            expected_status=422,
            json_data={
                "code": "print(42)"
                # Missing task_id
            },
            test_name="Missing required field",
        )

        # Test non-existent endpoint
        self.test_endpoint("GET", "/api/v1/nonexistent", expected_status=404, test_name="Non-existent endpoint")

    def test_performance(self):
        """Test performance and response times"""
        print(f"\n{YELLOW}Testing Performance...{RESET}")

        # Test response time
        start_time = time.time()
        result = self.test_endpoint(
            "POST",
            f"/api/v1/students/{TEST_USER_ID}/compile",
            json_data={"code": "print(sum(range(1000)))", "language": "python"},
            test_name="Code execution performance",
        )
        elapsed = time.time() - start_time

        if elapsed < 5:
            self.log_test("Response time check", True, f"Responded in {elapsed:.2f}s")
        else:
            self.log_test("Response time check", False, f"Slow response: {elapsed:.2f}s")

        # Test handling of infinite loop (should timeout)
        self.test_endpoint(
            "POST",
            f"/api/v1/students/{TEST_USER_ID}/compile",
            json_data={"code": "while True: pass", "language": "python"},
            test_name="Infinite loop handling",
        )

    def print_summary(self):
        """Print test summary"""
        print(f"\n{BLUE}═══════════════════════════════════════════{RESET}")
        print(f"{BLUE}                TEST SUMMARY{RESET}")
        print(f"{BLUE}═══════════════════════════════════════════{RESET}")

        success_rate = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0

        print(f"Total Tests: {self.total_tests}")
        print(f"{GREEN}Passed: {self.passed_tests}{RESET}")
        print(f"{RED}Failed: {self.failed_tests}{RESET}")
        print(f"Success Rate: {success_rate:.1f}%")

        if self.failed_tests == 0:
            print(f"\n{GREEN}✓ All tests passed!{RESET}")
        else:
            print(f"\n{RED}✗ Some tests failed. Review the output above.{RESET}")

        # Save results to file
        with open("test_results.json", "w") as f:
            json.dump(
                {
                    "timestamp": datetime.now().isoformat(),
                    "summary": {
                        "total": self.total_tests,
                        "passed": self.passed_tests,
                        "failed": self.failed_tests,
                        "success_rate": success_rate,
                    },
                    "results": self.test_results,
                },
                f,
                indent=2,
            )

        print(f"\nDetailed results saved to: test_results.json")


def check_server_running():
    """Check if the server is running"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=2)
        return response.status_code == 200
    except:
        return False


def main():
    """Main test runner"""
    # Check if server is running
    if not check_server_running():
        print(f"{RED}Error: Server is not running at {API_BASE_URL}{RESET}")
        print("Please start the server with: uvicorn app:app --host 0.0.0.0 --port 8000")
        sys.exit(1)

    # Run tests
    tester = APITester(API_BASE_URL)
    tester.run_all_tests()

    # Exit with appropriate code
    sys.exit(0 if tester.failed_tests == 0 else 1)


if __name__ == "__main__":
    main()
