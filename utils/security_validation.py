"""
Security Validation Utilities
Comprehensive input sanitization and security validation for code execution endpoints
"""

import re
import ast
import html
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field, validator
from fastapi import HTTPException
from utils.logging_config import logger

# =============================================================================
# SECURITY CONFIGURATION
# =============================================================================

# Maximum code size (in characters)
MAX_CODE_SIZE = 10000

# Maximum text input size (in characters)
MAX_TEXT_SIZE = 5000

# Allowed Python modules for educational platform
ALLOWED_MODULES = {
    "math",
    "random",
    "datetime",
    "itertools",
    "collections",
    "string",
    "re",
    "json",
    "statistics",
    "decimal",
    "fractions",
    "anytree",  # For tree exercises
}

# Dangerous Python functions that should be blocked
DANGEROUS_FUNCTIONS = {
    "eval",
    "exec",
    "compile",
    "open",
    "input",
    "raw_input",
    "__import__",
    "getattr",
    "setattr",
    "delattr",
    "hasattr",
    "globals",
    "locals",
    "vars",
    "dir",
    "help",
    "exit",
    "quit",
    "reload",
    "breakpoint",
    "memoryview",
}

# Dangerous Python modules that should be blocked
DANGEROUS_MODULES = {
    "os",
    "sys",
    "subprocess",
    "shutil",
    "glob",
    "pickle",
    "marshal",
    "ctypes",
    "threading",
    "multiprocessing",
    "socket",
    "urllib",
    "requests",
    "http",
    "ftplib",
    "smtplib",
    "poplib",
    "imaplib",
    "telnetlib",
    "ssl",
    "hashlib",
    "hmac",
    "secrets",
    "tempfile",
    "webbrowser",
    "platform",
    "pwd",
    "grp",
    "resource",
    "syslog",
    "gc",
    "weakref",
    "copy_reg",
    "imp",
    "importlib",
    "pkgutil",
    "modulefinder",
    "runpy",
    "timeit",
    "trace",
    "traceback",
    "pdb",
    "bdb",
    "faulthandler",
    "linecache",
    "tokenize",
}

# SQL injection patterns for text inputs
SQL_INJECTION_PATTERNS = [
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
    r"(\b(UNION|JOIN|WHERE|ORDER BY|GROUP BY|HAVING)\b)",
    r"(--|/\*|\*/|;)",
    r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
    r"(\b(OR|AND)\s+['\"]?\w*['\"]?\s*=\s*['\"]?\w*['\"]?)",
]

# XSS patterns for text inputs
XSS_PATTERNS = [
    r"<script[^>]*>.*?</script>",
    r"javascript:",
    r"on\w+\s*=",
    r"<iframe[^>]*>",
    r"<object[^>]*>",
    r"<embed[^>]*>",
    r"<form[^>]*>",
    r"<input[^>]*>",
    r"<link[^>]*>",
    r"<meta[^>]*>",
]

# =============================================================================
# SECURITY VALIDATION CLASSES
# =============================================================================


class SecurityViolation(BaseModel):
    """Represents a security violation found during validation"""

    severity: str = Field(..., description="Severity: critical, high, medium, low")
    category: str = Field(..., description="Category: code_injection, module_restriction, etc.")
    message: str = Field(..., description="Human-readable security violation message")
    line_number: Optional[int] = Field(None, description="Line number where violation occurs")
    code_snippet: Optional[str] = Field(None, description="Relevant code snippet")


class ValidationResult(BaseModel):
    """Result of security validation"""

    is_safe: bool = Field(..., description="Whether the input is considered safe")
    violations: List[SecurityViolation] = Field(default_factory=list)
    sanitized_input: Optional[str] = Field(None, description="Sanitized version of input")
    risk_score: int = Field(default=0, description="Risk score (0-100)")


# =============================================================================
# CODE SECURITY ANALYZER
# =============================================================================


class CodeSecurityAnalyzer(ast.NodeVisitor):
    """Advanced AST-based code security analyzer"""

    def __init__(self):
        self.violations: List[SecurityViolation] = []
        self.loop_count = 0
        self.recursion_depth = 0
        self.max_recursion_depth = 10
        self.function_definitions = set()

    def add_violation(
        self,
        severity: str,
        category: str,
        message: str,
        line_number: Optional[int] = None,
        code_snippet: Optional[str] = None,
    ):
        """Add a security violation"""
        self.violations.append(
            SecurityViolation(
                severity=severity,
                category=category,
                message=message,
                line_number=line_number,
                code_snippet=code_snippet,
            )
        )

    def visit_Import(self, node):
        """Check import statements"""
        for alias in node.names:
            module_name = alias.name
            if module_name in DANGEROUS_MODULES:
                self.add_violation(
                    severity="critical",
                    category="dangerous_module",
                    message=f"Import of dangerous module '{module_name}' is not allowed",
                    line_number=node.lineno,
                    code_snippet=f"import {module_name}",
                )
            elif module_name not in ALLOWED_MODULES:
                self.add_violation(
                    severity="high",
                    category="module_restriction",
                    message=f"Import of unapproved module '{module_name}' is not allowed",
                    line_number=node.lineno,
                    code_snippet=f"import {module_name}",
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """Check from X import Y statements"""
        if node.module:
            if node.module in DANGEROUS_MODULES:
                self.add_violation(
                    severity="critical",
                    category="dangerous_module",
                    message=f"Import from dangerous module '{node.module}' is not allowed",
                    line_number=node.lineno,
                    code_snippet=f"from {node.module} import ...",
                )
            elif node.module not in ALLOWED_MODULES:
                self.add_violation(
                    severity="high",
                    category="module_restriction",
                    message=f"Import from unapproved module '{node.module}' is not allowed",
                    line_number=node.lineno,
                    code_snippet=f"from {node.module} import ...",
                )
        self.generic_visit(node)

    def visit_Call(self, node):
        """Check function calls for dangerous functions"""
        func_name = None

        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        if func_name and func_name in DANGEROUS_FUNCTIONS:
            self.add_violation(
                severity="critical",
                category="dangerous_function",
                message=f"Use of dangerous function '{func_name}' is not allowed",
                line_number=node.lineno,
                code_snippet=f"{func_name}(...)",
            )

        # Check for potential code injection via string operations
        if isinstance(node.func, ast.Attribute) and node.func.attr == "format":
            self.add_violation(
                severity="medium",
                category="code_injection_risk",
                message="String formatting can be dangerous - ensure no user input is used",
                line_number=node.lineno,
            )

        self.generic_visit(node)

    def visit_While(self, node):
        """Check while loops for infinite loop potential"""
        self.loop_count += 1
        if self.loop_count > 5:
            self.add_violation(
                severity="high",
                category="resource_exhaustion",
                message="Too many nested loops detected - potential infinite loop risk",
                line_number=node.lineno,
            )
        self.generic_visit(node)
        self.loop_count -= 1

    def visit_For(self, node):
        """Check for loops for potential issues"""
        self.loop_count += 1
        if self.loop_count > 5:
            self.add_violation(
                severity="high",
                category="resource_exhaustion",
                message="Too many nested loops detected - potential performance issue",
                line_number=node.lineno,
            )
        self.generic_visit(node)
        self.loop_count -= 1

    def visit_FunctionDef(self, node):
        """Check function definitions"""
        self.recursion_depth += 1
        if self.recursion_depth > self.max_recursion_depth:
            self.add_violation(
                severity="medium",
                category="resource_exhaustion",
                message="Excessive function nesting detected",
                line_number=node.lineno,
            )

        # Check for potential recursive functions
        if node.name in self.function_definitions:
            self.add_violation(
                severity="medium",
                category="recursion_risk",
                message=f"Function '{node.name}' might be recursive - ensure proper base case",
                line_number=node.lineno,
            )
        else:
            self.function_definitions.add(node.name)

        self.generic_visit(node)
        self.recursion_depth -= 1

    def visit_Attribute(self, node):
        """Check attribute access for dangerous operations"""
        if isinstance(node.value, ast.Name):
            # Check for potential dangerous attribute access
            dangerous_attrs = {"__class__", "__bases__", "__subclasses__", "__globals__"}
            if node.attr in dangerous_attrs:
                self.add_violation(
                    severity="critical",
                    category="reflection_abuse",
                    message=f"Access to dangerous attribute '{node.attr}' is not allowed",
                    line_number=node.lineno,
                )
        self.generic_visit(node)


# =============================================================================
# INPUT SANITIZATION FUNCTIONS
# =============================================================================


def sanitize_code_input(code: str) -> ValidationResult:
    """
    Comprehensive code input sanitization and validation
    """
    violations = []
    risk_score = 0

    # Basic input validation
    if not code or not code.strip():
        return ValidationResult(
            is_safe=False,
            violations=[
                SecurityViolation(
                    severity="medium", category="input_validation", message="Empty code input is not allowed"
                )
            ],
            risk_score=50,
        )

    # Check code size
    if len(code) > MAX_CODE_SIZE:
        violations.append(
            SecurityViolation(
                severity="high",
                category="input_validation",
                message=f"Code size ({len(code)} chars) exceeds maximum allowed ({MAX_CODE_SIZE} chars)",
            )
        )
        risk_score += 30

    # Check for obvious malicious patterns
    malicious_patterns = [
        (r"__.*__", "Use of dunder methods is restricted"),
        (r"chr\(|ord\(", "Character manipulation functions are restricted"),
        (r"exec\s*\(|eval\s*\(", "Dynamic code execution is forbidden"),
        (r"import\s+os|from\s+os", "OS module access is forbidden"),
        (r"while\s+True\s*:", "Infinite loops are not allowed"),
    ]

    for pattern, message in malicious_patterns:
        if re.search(pattern, code, re.IGNORECASE):
            violations.append(SecurityViolation(severity="critical", category="malicious_pattern", message=message))
            risk_score += 40

    # Parse and analyze AST
    try:
        tree = ast.parse(code)
        analyzer = CodeSecurityAnalyzer()
        analyzer.visit(tree)
        violations.extend(analyzer.violations)

        # Calculate additional risk score based on violations
        for violation in analyzer.violations:
            if violation.severity == "critical":
                risk_score += 30
            elif violation.severity == "high":
                risk_score += 20
            elif violation.severity == "medium":
                risk_score += 10
            else:
                risk_score += 5

    except SyntaxError as e:
        violations.append(
            SecurityViolation(
                severity="medium",
                category="syntax_error",
                message=f"Syntax error in code: {str(e)}",
                line_number=e.lineno if hasattr(e, "lineno") else None,
            )
        )
        risk_score += 20

    # Determine if code is safe
    critical_violations = [v for v in violations if v.severity == "critical"]
    is_safe = len(critical_violations) == 0 and risk_score < 70

    return ValidationResult(
        is_safe=is_safe,
        violations=violations,
        sanitized_input=code.strip(),  # Basic sanitization
        risk_score=min(risk_score, 100),
    )


def sanitize_text_input(text: str) -> ValidationResult:
    """
    Sanitize and validate text inputs (for quiz answers, etc.)
    """
    violations = []
    risk_score = 0

    if not text:
        return ValidationResult(is_safe=True, violations=[], sanitized_input="", risk_score=0)

    # Check text size
    if len(text) > MAX_TEXT_SIZE:
        violations.append(
            SecurityViolation(
                severity="medium",
                category="input_validation",
                message=f"Text size ({len(text)} chars) exceeds maximum allowed ({MAX_TEXT_SIZE} chars)",
            )
        )
        risk_score += 20

    # Check for SQL injection patterns
    for pattern in SQL_INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            violations.append(
                SecurityViolation(
                    severity="high", category="sql_injection", message="Potential SQL injection pattern detected"
                )
            )
            risk_score += 25
            break

    # Check for XSS patterns
    for pattern in XSS_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            violations.append(
                SecurityViolation(severity="high", category="xss_attempt", message="Potential XSS pattern detected")
            )
            risk_score += 25
            break

    # Check for suspicious patterns
    suspicious_patterns = [
        (r"<\s*script", "Script tags are not allowed"),
        (r"javascript\s*:", "JavaScript URLs are not allowed"),
        (r"data\s*:", "Data URLs are not allowed"),
        (r"vbscript\s*:", "VBScript is not allowed"),
    ]

    for pattern, message in suspicious_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            violations.append(SecurityViolation(severity="medium", category="suspicious_pattern", message=message))
            risk_score += 15

    # Sanitize the text
    sanitized_text = html.escape(text.strip())  # HTML escape for safety

    # Determine if text is safe
    high_violations = [v for v in violations if v.severity in ["critical", "high"]]
    is_safe = len(high_violations) == 0 and risk_score < 50

    return ValidationResult(
        is_safe=is_safe, violations=violations, sanitized_input=sanitized_text, risk_score=min(risk_score, 100)
    )


# =============================================================================
# FASTAPI REQUEST VALIDATORS
# =============================================================================


def validate_code_request(code: str, language: str = "python") -> Tuple[bool, str]:
    """
    Validate code submission request
    Returns (is_valid, error_message)
    """
    # Only support Python for now
    if language.lower() != "python":
        return False, f"Programming language '{language}' is not supported"

    # Validate code
    result = sanitize_code_input(code)

    if not result.is_safe:
        # Get the most severe violation
        critical_violations = [v for v in result.violations if v.severity == "critical"]
        if critical_violations:
            return False, critical_violations[0].message

        high_violations = [v for v in result.violations if v.severity == "high"]
        if high_violations:
            return False, high_violations[0].message

        return False, "Code contains security violations"

    return True, ""


def validate_text_request(text: str) -> Tuple[bool, str]:
    """
    Validate text submission request
    Returns (is_valid, error_message)
    """
    result = sanitize_text_input(text)

    if not result.is_safe:
        # Get the most severe violation
        high_violations = [v for v in result.violations if v.severity in ["critical", "high"]]
        if high_violations:
            return False, high_violations[0].message

        return False, "Text contains potentially unsafe content"

    return True, ""


# =============================================================================
# SECURITY MIDDLEWARE HELPERS
# =============================================================================


def log_security_violation(user_id: str, violation: SecurityViolation, input_data: str):
    """Log security violations for monitoring"""
    logger.warning(
        f"SECURITY_VIOLATION: User {user_id} - {violation.severity.upper()} - "
        f"{violation.category}: {violation.message} | Input: {input_data[:100]}..."
    )


def raise_security_error(violation: SecurityViolation):
    """Raise appropriate HTTP exception for security violation"""
    if violation.severity == "critical":
        raise HTTPException(status_code=403, detail=f"Security violation: {violation.message}")
    elif violation.severity == "high":
        raise HTTPException(status_code=400, detail=f"Input validation failed: {violation.message}")
    else:
        raise HTTPException(status_code=400, detail="Input contains unsafe content")
