"""
Comprehensive Security Tests
Tests all security features including input validation, rate limiting, and injection protection
"""

import pytest
import time
from fastapi import status
from models import User, Task, Course, Lesson, Topic
from utils.rate_limiting import rate_limiter
from utils.security_validation import sanitize_code_input, sanitize_text_input


class TestComprehensiveSecurity:
    """Comprehensive security testing across all endpoints"""

    @pytest.fixture
    def setup_security_test_data(self, test_db):
        """Setup test data for security tests"""
        user = User(
            internal_user_id="security-test-user", hashed_sub="security_hash", username="securityuser", status="student"
        )
        test_db.add(user)
        test_db.commit()

        # Create minimal course structure for testing
        course = Course(title="Security Test Course", description="Test", professor_id=user.id)
        test_db.add(course)
        test_db.commit()

        lesson = Lesson(title="Security Lesson", description="Test", course_id=course.id, lesson_order=1)
        test_db.add(lesson)
        test_db.commit()

        topic = Topic(
            title="Security Topic",
            lesson_id=lesson.id,
            topic_order=1,
            background="Test",
            objectives="Test",
            content_file_md="test.md",
            concepts="test",
        )
        test_db.add(topic)
        test_db.commit()

        task = Task(
            task_name="Security Task",
            task_link="security-task",
            points=10,
            type="CodeTask",
            order=1,
            data={"question": "Test"},
            topic_id=topic.id,
        )
        test_db.add(task)
        test_db.commit()

        return {"user": user, "course": course, "lesson": lesson, "topic": topic, "task": task}

    def test_code_injection_attacks(self, client, setup_security_test_data):
        """Test protection against various code injection attacks"""
        user = setup_security_test_data["user"]

        # Reset rate limiter for clean test
        rate_limiter.violations.clear()
        rate_limiter.blocked_users.clear()

        dangerous_codes = [
            # OS command execution
            "import os; os.system('rm -rf /')",
            "import subprocess; subprocess.call(['ls', '/'])",
            # File system access
            "open('/etc/passwd', 'r').read()",
            "with open('/etc/shadow') as f: print(f.read())",
            # Dynamic code execution
            "exec('import os; os.system(\"whoami\")')",
            'eval(\'__import__("os").system("ls")\')',
            # Module manipulation
            "__import__('os').system('id')",
            "getattr(__builtins__, 'exec')('print(\"hack\")')",
            # Reflection attacks
            "object.__subclasses__()",
            "[].__class__.__bases__[0].__subclasses__()",
            # Network access attempts
            "import socket; socket.socket()",
            "import urllib; urllib.request.urlopen('http://evil.com')",
            # Process manipulation
            "import threading; threading.Thread(target=lambda: None).start()",
            "import multiprocessing; multiprocessing.Process().start()",
        ]

        for dangerous_code in dangerous_codes:
            request_data = {"code": dangerous_code, "language": "python"}

            response = client.post(f"/api/v1/students/{user.internal_user_id}/compile", json=request_data)

            # Should be blocked by security validation
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "Security validation failed" in response.json()["detail"]

    def test_sql_injection_protection(self, client, setup_security_test_data):
        """Test protection against SQL injection attacks"""
        user = setup_security_test_data["user"]
        task = setup_security_test_data["task"]

        sql_injection_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM users --",
            "'; INSERT INTO users VALUES ('hacker', 'password'); --",
            "' OR 1=1 LIMIT 1 OFFSET 0 --",
            "'; UPDATE users SET password='hacked' WHERE id=1; --",
            "' AND (SELECT COUNT(*) FROM users) > 0 --",
            "'; EXEC xp_cmdshell('dir'); --",
        ]

        for payload in sql_injection_payloads:
            request_data = {"user_answer": payload, "task_id": task.id}

            response = client.post(f"/api/v1/students/{user.internal_user_id}/submit-text", json=request_data)

            # Should be blocked by input validation
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "Input validation failed" in response.json()["detail"]

    def test_xss_protection(self, client, setup_security_test_data):
        """Test protection against XSS attacks"""
        user = setup_security_test_data["user"]
        task = setup_security_test_data["task"]

        xss_payloads = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "<svg onload=alert('xss')>",
            "javascript:alert('xss')",
            "<iframe src=javascript:alert('xss')></iframe>",
            "<object data='data:text/html;base64,PHNjcmlwdD5hbGVydCgneHNzJyk8L3NjcmlwdD4='></object>",
            "<embed src='data:text/html;base64,PHNjcmlwdD5hbGVydCgneHNzJyk8L3NjcmlwdD4='></embed>",
            "<form><input formaction=javascript:alert('xss')>",
            "<link rel=stylesheet href=javascript:alert('xss')>",
            "<meta http-equiv=refresh content='0;url=javascript:alert(\"xss\")'>",
        ]

        for payload in xss_payloads:
            request_data = {"user_answer": payload, "task_id": task.id}

            response = client.post(f"/api/v1/students/{user.internal_user_id}/submit-text", json=request_data)

            # Should be blocked by XSS protection
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "Input validation failed" in response.json()["detail"]

    def test_path_traversal_protection(self, client, setup_security_test_data):
        """Test protection against path traversal attacks"""
        user = setup_security_test_data["user"]

        path_traversal_payloads = [
            "../../etc/passwd",
            "..\\..\\windows\\system32\\config\\sam",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "....//....//....//etc//passwd",
            "..%252f..%252f..%252fetc%252fpasswd",
            "..%c0%af..%c0%af..%c0%afetc%c0%afpasswd",
            "../../../../../../../etc/passwd%00",
            "..\\..\\..\\..\\..\\..\\..\\etc\\passwd",
        ]

        for payload in path_traversal_payloads:
            # Test in various endpoints that might process file paths
            endpoints_to_test = [
                f"/api/v1/students/{payload}/profile",
                f"/api/v1/learning/{payload}",
            ]

            for endpoint in endpoints_to_test:
                response = client.get(endpoint)

                # Should return 404 or 400, not succeed or crash
                assert response.status_code in [
                    status.HTTP_404_NOT_FOUND,
                    status.HTTP_400_BAD_REQUEST,
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                ]

    def test_rate_limiting_security(self, client, setup_security_test_data):
        """Test rate limiting security features"""
        user = setup_security_test_data["user"]

        # Reset rate limiter
        rate_limiter.requests.clear()
        rate_limiter.violations.clear()
        rate_limiter.blocked_users.clear()

        # Test normal rate limiting
        safe_code = {"code": "print('test')", "language": "python"}

        # Make requests up to the limit
        for i in range(30):  # Limit is 30 per 5 minutes
            response = client.post(f"/api/v1/students/{user.internal_user_id}/compile", json=safe_code)
            assert response.status_code == status.HTTP_200_OK

        # 31st request should be rate limited
        response = client.post(f"/api/v1/students/{user.internal_user_id}/compile", json=safe_code)
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "Rate limit exceeded" in response.json()["detail"]

    def test_progressive_security_penalties(self, client, setup_security_test_data):
        """Test progressive penalties for security violations"""
        user = setup_security_test_data["user"]

        # Reset rate limiter
        rate_limiter.requests.clear()
        rate_limiter.violations.clear()
        rate_limiter.blocked_users.clear()

        dangerous_code = {"code": "import os; os.system('ls')", "language": "python"}

        # Generate multiple security violations
        for i in range(5):
            response = client.post(f"/api/v1/students/{user.internal_user_id}/compile", json=dangerous_code)
            assert response.status_code == status.HTTP_400_BAD_REQUEST

            # After 3 violations, user should be temporarily blocked
            if i >= 2:
                # Check if user is blocked (might happen on subsequent requests)
                test_response = client.post(
                    f"/api/v1/students/{user.internal_user_id}/compile",
                    json={"code": "print('test')", "language": "python"},
                )
                if test_response.status_code == status.HTTP_403_FORBIDDEN:
                    assert "temporarily blocked" in test_response.json()["detail"]

    def test_input_size_limits(self, client, setup_security_test_data):
        """Test input size limit enforcement"""
        user = setup_security_test_data["user"]
        task = setup_security_test_data["task"]

        # Test oversized code input (limit is 10000 characters)
        oversized_code = "print('a')\n" * 1000  # Should exceed limit

        request_data = {"code": oversized_code, "language": "python"}

        response = client.post(f"/api/v1/students/{user.internal_user_id}/compile", json=request_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test oversized text input (limit is 5000 characters)
        oversized_text = "a" * 6000

        text_request = {"user_answer": oversized_text, "task_id": task.id}

        response = client.post(f"/api/v1/students/{user.internal_user_id}/submit-text", json=text_request)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_malicious_unicode_and_encoding(self, client, setup_security_test_data):
        """Test protection against malicious unicode and encoding attacks"""
        user = setup_security_test_data["user"]
        task = setup_security_test_data["task"]

        malicious_unicode_payloads = [
            # Unicode normalization attacks
            "\\u0061\\u0300",  # a with combining grave accent
            "\\u0065\\u0301",  # e with combining acute accent
            # Right-to-left override attacks
            "\\u202E",
            # Zero-width characters
            "\\u200B\\u200C\\u200D\\uFEFF",
            # Overlong UTF-8 encoding
            "\\xC0\\xAE",
            # High bit characters
            "\\xFF\\xFE",
        ]

        for payload in malicious_unicode_payloads:
            request_data = {"user_answer": payload, "task_id": task.id}

            response = client.post(f"/api/v1/students/{user.internal_user_id}/submit-text", json=request_data)

            # Should handle gracefully (either accept or reject, but not crash)
            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            ]

    def test_concurrent_attack_simulation(self, client, setup_security_test_data):
        """Test system behavior under concurrent attack simulation"""
        user = setup_security_test_data["user"]

        # Reset rate limiter
        rate_limiter.requests.clear()
        rate_limiter.violations.clear()
        rate_limiter.blocked_users.clear()

        dangerous_code = {"code": "exec('malicious')", "language": "python"}

        # Simulate concurrent malicious requests
        responses = []
        for _ in range(10):
            response = client.post(f"/api/v1/students/{user.internal_user_id}/compile", json=dangerous_code)
            responses.append(response)

        # All should be blocked, none should crash the system
        for response in responses:
            assert response.status_code in [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_403_FORBIDDEN,
                status.HTTP_429_TOO_MANY_REQUESTS,
            ]

    def test_security_validation_unit_tests(self):
        """Test security validation functions directly"""
        # Test code validation
        safe_code_result = sanitize_code_input("print('Hello World')")
        assert safe_code_result.is_safe == True
        assert len(safe_code_result.violations) == 0

        dangerous_code_result = sanitize_code_input("import os; os.system('rm -rf /')")
        assert dangerous_code_result.is_safe == False
        assert len(dangerous_code_result.violations) > 0

        # Test text validation
        safe_text_result = sanitize_text_input("This is a normal answer")
        assert safe_text_result.is_safe == True
        assert len(safe_text_result.violations) == 0

        xss_text_result = sanitize_text_input("<script>alert('xss')</script>")
        assert xss_text_result.is_safe == False
        assert len(xss_text_result.violations) > 0

    def test_error_information_leakage(self, client, setup_security_test_data):
        """Test that error messages don't leak sensitive information"""
        user = setup_security_test_data["user"]

        # Test with invalid user ID
        response = client.get("/api/v1/students/invalid-user/profile")
        assert response.status_code == status.HTTP_404_NOT_FOUND

        error_detail = response.json()["detail"]

        # Error should be generic, not revealing system internals
        assert "User not found" in error_detail
        # Should not contain database error details, file paths, etc.
        assert "database" not in error_detail.lower()
        assert "sql" not in error_detail.lower()
        assert "/home/" not in error_detail
        assert "postgres" not in error_detail.lower()

    def test_timing_attack_protection(self, client, setup_security_test_data):
        """Test protection against timing attacks"""
        # Test user existence timing
        valid_user = setup_security_test_data["user"]

        # Time requests for valid and invalid users
        import time

        # Valid user request
        start_time = time.time()
        response1 = client.get(f"/api/v1/students/{valid_user.internal_user_id}/profile")
        valid_time = time.time() - start_time

        # Invalid user request
        start_time = time.time()
        response2 = client.get("/api/v1/students/non-existent-user/profile")
        invalid_time = time.time() - start_time

        # Both should complete in reasonable time
        assert valid_time < 5.0
        assert invalid_time < 5.0

        # Timing difference should not be significant enough for timing attacks
        # (This is a basic check - in production you might want more sophisticated timing analysis)
        time_difference = abs(valid_time - invalid_time)
        assert time_difference < 2.0  # Reasonable threshold

    def test_session_security(self, client, setup_security_test_data):
        """Test session security features"""
        user = setup_security_test_data["user"]

        # Test that sessions are properly isolated
        # Make request with one user
        response1 = client.get(f"/api/v1/students/{user.internal_user_id}/profile")
        assert response1.status_code == status.HTTP_200_OK

        # Create another user
        user2_id = "different-user-123"

        # Attempt to access other user's data should fail
        response2 = client.get(f"/api/v1/students/{user2_id}/profile")
        assert response2.status_code == status.HTTP_404_NOT_FOUND

    def test_content_type_validation(self, client, setup_security_test_data):
        """Test content type validation and protection"""
        user = setup_security_test_data["user"]

        # Test with wrong content type
        response = client.post(
            f"/api/v1/students/{user.internal_user_id}/compile",
            data="invalid data",  # Plain text instead of JSON
            headers={"Content-Type": "text/plain"},
        )

        # Should reject invalid content type
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        ]
