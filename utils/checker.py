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

# Whitelist of allowed modules (enhanced security)
ALLOWED_MODULES = [
    "anytree", "math", "random", "datetime", "itertools", "collections",
    "string", "re", "json", "statistics", "decimal", "fractions"
]

# List of dangerous functions (expanded)
DANGEROUS_FUNCTIONS = [
    "eval", "exec", "compile", "open", "input", "raw_input", "__import__",
    "getattr", "setattr", "delattr", "hasattr", "globals", "locals", "vars",
    "dir", "help", "exit", "quit", "reload", "breakpoint", "memoryview"
]

# Dangerous modules that should be blocked
DANGEROUS_MODULES = {
    "os", "sys", "subprocess", "shutil", "glob", "pickle", "marshal",
    "ctypes", "threading", "multiprocessing", "socket", "urllib", 
    "requests", "http", "ftplib", "smtplib", "tempfile", "webbrowser",
    "platform", "pwd", "grp", "resource", "importlib", "runpy"
}


class CodeSanitizer(ast.NodeVisitor):
    def __init__(self):
        self.errors = []
        self.loop_count = 0  # Counter to detect excessive looping

    def visit_Import(self, node):
        for alias in node.names:
            if alias.name in DANGEROUS_MODULES:
                self.errors.append(f"Import of dangerous module '{alias.name}' is forbidden")
            elif alias.name not in ALLOWED_MODULES:
                self.errors.append(f"Use of unapproved module: {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module and node.module in DANGEROUS_MODULES:
            self.errors.append(f"Import from dangerous module '{node.module}' is forbidden")
        elif node.module and node.module not in ALLOWED_MODULES:
            self.errors.append(f"Use of unapproved module: {node.module}")
        self.generic_visit(node)

    def visit_Call(self, node):
        func_name = None
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr
            
        if func_name and func_name in DANGEROUS_FUNCTIONS:
            self.errors.append(f"Use of dangerous function: {func_name}")
            
        # Additional security checks
        if isinstance(node.func, ast.Attribute) and node.func.attr == "format":
            self.errors.append("String formatting can be dangerous - potential code injection risk")
            
        self.generic_visit(node)
        
    def visit_Attribute(self, node):
        # Check for dangerous attribute access
        dangerous_attrs = {"__class__", "__bases__", "__subclasses__", "__globals__", "__dict__"}
        if node.attr in dangerous_attrs:
            self.errors.append(f"Access to dangerous attribute '{node.attr}' is forbidden")
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
