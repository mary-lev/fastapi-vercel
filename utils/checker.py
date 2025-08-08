import os
import re
import subprocess
import secrets
from pathlib import Path
import ast
import sys
import logging

log_level = "INFO"
logger = logging.getLogger()
logger.setLevel(log_level)

console_handler = logging.StreamHandler()
console_handler.setLevel(log_level)
logger.addHandler(console_handler)

# Whitelist of allowed modules
ALLOWED_MODULES = ["anytree", "math", "random", "datetime"]

# List of dangerous functions
DANGEROUS_FUNCTIONS = ["eval", "exec", "compile", "open", "input"]


class CodeSanitizer(ast.NodeVisitor):
    def __init__(self):
        self.errors = []
        self.loop_count = 0  # Counter to detect excessive looping

    def visit_Import(self, node):
        for alias in node.names:
            if alias.name not in ALLOWED_MODULES:
                self.errors.append(f"Use of unapproved module: {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module not in ALLOWED_MODULES:
            self.errors.append(f"Use of unapproved module: {node.module}")
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id in DANGEROUS_FUNCTIONS:
            self.errors.append(f"Use of dangerous function: {node.func.id}")
        self.generic_visit(node)

    def visit_While(self, node):
        self.loop_count += 1
        if self.loop_count > 3:  # Limit number of loops to avoid infinite loops
            self.errors.append("Too many or potentially infinite loops detected.")
        self.generic_visit(node)

    def visit_For(self, node):
        self.loop_count += 1
        if self.loop_count > 3:
            self.errors.append("Too many or potentially infinite loops detected.")
        self.generic_visit(node)


def sanitize_code(code):
    try:
        tree = ast.parse(code)
    except BaseException as e:
        return [f"Syntax error: {e}"]
    sanitizer = CodeSanitizer()
    sanitizer.visit(tree)
    return sanitizer.errors


def run_code(code, token: str = "test"):
    random_hex = secrets.token_hex(4)
    temp_directory = Path("/tmp")
    temp_directory.mkdir(parents=True, exist_ok=True)
    file_path = str(temp_directory / f"{token}_{random_hex}.py")

    # Run the code through the sanitizer
    errors = sanitize_code(code)
    if errors:
        return {
            "success": False,
            "output": f"{errors[0]}",
        }

    # Write sanitized code to a temporary file
    with open(file_path, "w") as temp_file:
        temp_file.write(code)

    try:
        result = subprocess.run(
            [sys.executable, file_path],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
            env={
                "PYTHONHASHSEED": "0",
                "PYTHONPATH": str(Path(__file__).resolve().parent / "dependencies"),  # Include dependencies
            },
        )
        logger.info(f"Result: {result}")

        os.remove(file_path)
        return {
            "success": result.returncode == 0,
            "output": result.stdout if result.returncode == 0 else result.stderr,
        }

    except subprocess.TimeoutExpired:
        os.remove(file_path)
        return {
            "success": False,
            "output": "Execution timed out. Possible infinite loop detected.",
        }
    except subprocess.CalledProcessError as e:
        os.remove(file_path)
        error_message = re.sub(r'File ".*?/([a-zA-Z0-9_]+\.py)", line', "Your code, line", e.stderr)
        return {
            "success": False,
            "output": error_message,
        }
    except Exception as e:
        os.remove(file_path)
        return {
            "success": False,
            "output": f"Error: {e}",
        }
