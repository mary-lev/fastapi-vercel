import os
import re
import subprocess
import secrets

# import docker
from pathlib import Path
import ast


DANGEROUS_MODULES = ["os", "sys", "subprocess"]
DANGEROUS_FUNCTIONS = ["eval", "exec", "compile", "open", "input"]


class CodeSanitizer(ast.NodeVisitor):
    def __init__(self):
        self.errors = []

    def visit_Import(self, node):
        for alias in node.names:
            if alias.name in DANGEROUS_MODULES:
                self.errors.append(f"Use of dangerous module: {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module in DANGEROUS_MODULES:
            self.errors.append(f"Use of dangerous module: {node.module}")
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id in DANGEROUS_FUNCTIONS:
            self.errors.append(f"Use of dangerous function: {node.func.id}")
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

    with open(file_path, "w") as temp_file:
        temp_file.write(code)

    errors = sanitize_code(code)
    if errors:
        # Delete the temporary file
        os.remove(file_path)
        return {
            "success": False,
            "output": f"Code cannot be executed due to {errors[0]}",
        }
    else:
        try:
            # Running the Python script using subprocess
            result = subprocess.run(
                ["python", file_path], capture_output=True, text=True, timeout=30
            )

            # Delete the temporary file
            os.remove(file_path)

            if result.returncode == 0:
                # Success
                return {
                    "success": True,
                    "output": result.stdout,
                }
            else:
                # Error running script
                error_message = result.stderr
                pattern = r'File ".*?/([a-zA-Z0-9_]+\.py)", line'
                replacement = "Your code, line"
                error_message = re.sub(pattern, replacement, error_message)

                # Sanitize or modify the error message as needed
                return {
                    "success": False,
                    "output": error_message,
                }
        except subprocess.TimeoutExpired:
            # Delete the temporary file
            os.remove(file_path)
            return {
                "success": False,
                "output": "Execution timed out.",
            }
        except Exception as e:
            # Delete the temporary file
            os.remove(file_path)
            return {
                "success": False,
                "output": str(e),
            }
