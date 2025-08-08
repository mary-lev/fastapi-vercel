import pytest
from utils.checker import run_code, sanitize_code


class TestCodeExecutionSecurity:
    """Test security of code execution functionality"""

    def test_safe_code_execution(self):
        """Test that safe code executes successfully"""
        safe_code = """
print("Hello, World!")
result = 2 + 2
print(f"Result: {result}")
"""
        result = run_code(safe_code, "test_safe")

        assert result["success"] == True
        assert "Hello, World!" in result["output"]
        assert "Result: 4" in result["output"]

    def test_dangerous_function_blocked_eval(self):
        """Test that eval() function is blocked"""
        dangerous_code = """
eval("print('This should not execute')")
"""
        result = run_code(dangerous_code, "test_eval")

        assert result["success"] == False
        assert "Use of dangerous function: eval" in result["output"]

    def test_dangerous_function_blocked_exec(self):
        """Test that exec() function is blocked"""
        dangerous_code = """
exec("import os; os.system('ls')")
"""
        result = run_code(dangerous_code, "test_exec")

        assert result["success"] == False
        assert "Use of dangerous function: exec" in result["output"]

    def test_dangerous_function_blocked_open(self):
        """Test that open() function is blocked"""
        dangerous_code = """
with open('/etc/passwd', 'r') as f:
    print(f.read())
"""
        result = run_code(dangerous_code, "test_open")

        assert result["success"] == False
        assert "Use of dangerous function: open" in result["output"]

    def test_unapproved_module_import(self):
        """Test that unapproved modules are blocked"""
        dangerous_code = """
import os
os.system('echo "This should not work"')
"""
        result = run_code(dangerous_code, "test_import")

        assert result["success"] == False
        assert "Use of unapproved module: os" in result["output"]

    def test_unapproved_module_from_import(self):
        """Test that unapproved 'from' imports are blocked"""
        dangerous_code = """
from subprocess import call
call(['echo', 'This should not work'])
"""
        result = run_code(dangerous_code, "test_from_import")

        assert result["success"] == False
        assert "Use of unapproved module: subprocess" in result["output"]

    def test_approved_module_allowed_math(self):
        """Test that approved modules work correctly"""
        safe_code = """
import math
result = math.sqrt(16)
print(f"Square root of 16 is {result}")
"""
        result = run_code(safe_code, "test_math")

        assert result["success"] == True
        assert "Square root of 16 is 4.0" in result["output"]

    def test_approved_module_allowed_random(self):
        """Test that random module is allowed"""
        safe_code = """
import random
random.seed(42)  # For consistent testing
value = random.randint(1, 10)
print(f"Random value: {value}")
"""
        result = run_code(safe_code, "test_random")

        assert result["success"] == True
        assert "Random value:" in result["output"]

    def test_timeout_protection(self):
        """Test that infinite loops are stopped by timeout"""
        infinite_loop_code = """
while True:
    pass
"""
        result = run_code(infinite_loop_code, "test_timeout")

        assert result["success"] == False
        assert "Execution timed out" in result["output"]

    def test_too_many_loops_detected(self):
        """Test that too many loops are detected"""
        many_loops_code = """
for i in range(1):
    pass

for j in range(1):
    pass

for k in range(1):
    pass

for l in range(1):
    pass

# This should trigger the loop limit
"""
        result = run_code(many_loops_code, "test_loops")

        assert result["success"] == False
        assert "Too many or potentially infinite loops detected" in result["output"]

    def test_syntax_error_handling(self):
        """Test that syntax errors are properly handled"""
        syntax_error_code = """
print("Missing closing quote)
"""
        result = run_code(syntax_error_code, "test_syntax")

        assert result["success"] == False
        assert "Syntax error" in result["output"]

    def test_runtime_error_handling(self):
        """Test that runtime errors are properly handled"""
        runtime_error_code = """
result = 1 / 0
print(result)
"""
        result = run_code(runtime_error_code, "test_runtime")

        assert result["success"] == False
        assert "ZeroDivisionError" in result["output"] or "division by zero" in result["output"]


class TestCodeSanitization:
    """Test the code sanitization functions"""

    def test_sanitize_safe_code(self):
        """Test sanitization of safe code"""
        safe_code = """
import math
result = math.sqrt(25)
print(result)
"""
        errors = sanitize_code(safe_code)
        assert len(errors) == 0

    def test_sanitize_dangerous_import(self):
        """Test sanitization catches dangerous imports"""
        dangerous_code = """
import os
print("test")
"""
        errors = sanitize_code(dangerous_code)
        assert len(errors) > 0
        assert "Use of unapproved module: os" in errors[0]

    def test_sanitize_dangerous_function(self):
        """Test sanitization catches dangerous functions"""
        dangerous_code = """
eval("2 + 2")
"""
        errors = sanitize_code(dangerous_code)
        assert len(errors) > 0
        assert "Use of dangerous function: eval" in errors[0]

    def test_sanitize_syntax_error(self):
        """Test sanitization handles syntax errors"""
        syntax_error_code = """
def broken_function(
    pass
"""
        errors = sanitize_code(syntax_error_code)
        assert len(errors) > 0
        assert "Syntax error" in errors[0]


class TestCodeExecutionLimits:
    """Test resource limits and constraints"""

    def test_memory_intensive_code(self):
        """Test handling of memory-intensive code"""
        # This test may need adjustment based on system limits
        memory_code = """
# Create a large list
big_list = [i for i in range(100000)]
print(f"Created list with {len(big_list)} elements")
"""
        result = run_code(memory_code, "test_memory")

        # Should either succeed with reasonable memory usage or fail gracefully
        assert result["success"] in [True, False]
        if not result["success"]:
            # If it fails, it should be due to resource limits, not a crash
            assert "Error:" in result["output"] or "timeout" in result["output"].lower()

    def test_complex_computation(self):
        """Test handling of complex but safe computations"""
        complex_code = """
import math

def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# Small enough to complete within timeout
result = fibonacci(10)
print(f"Fibonacci(10) = {result}")
"""
        result = run_code(complex_code, "test_complex")

        assert result["success"] == True
        assert "Fibonacci(10) = 55" in result["output"]
