"""
Structured Logging with Correlation IDs
Provides comprehensive logging with request tracking and correlation
"""

import logging
import json
import sys
import traceback
from typing import Dict, Any, Optional, Union
from datetime import datetime
from contextvars import ContextVar
import uuid
from enum import Enum
from fastapi import Request, Response
from pydantic import BaseModel, Field

# Context variable for storing correlation ID
correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)

# ============================================================================
# LOG LEVELS AND CONFIGURATION
# ============================================================================


class LogLevel(str, Enum):
    """Log severity levels"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    SECURITY = "SECURITY"  # Special level for security events


class LogCategory(str, Enum):
    """Log categories for filtering and analysis"""

    REQUEST = "request"
    RESPONSE = "response"
    DATABASE = "database"
    SECURITY = "security"
    AUTHENTICATION = "authentication"
    CODE_EXECUTION = "code_execution"
    ERROR = "error"
    PERFORMANCE = "performance"
    BUSINESS = "business"
    SYSTEM = "system"


# ============================================================================
# STRUCTURED LOG MODELS
# ============================================================================


class StructuredLogEntry(BaseModel):
    """Standard structured log entry format"""

    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    level: str = Field(..., description="Log severity level")
    category: str = Field(..., description="Log category for filtering")
    message: str = Field(..., description="Log message")
    correlation_id: Optional[str] = Field(None, description="Request correlation ID")
    user_id: Optional[str] = Field(None, description="User identifier")

    # Request context
    request_id: Optional[str] = Field(None, description="Unique request ID")
    request_method: Optional[str] = Field(None, description="HTTP method")
    request_path: Optional[str] = Field(None, description="Request path")
    request_ip: Optional[str] = Field(None, description="Client IP address")

    # Response context
    response_status: Optional[int] = Field(None, description="HTTP response status")
    response_time_ms: Optional[float] = Field(None, description="Response time in milliseconds")

    # Error context
    error_type: Optional[str] = Field(None, description="Error class name")
    error_message: Optional[str] = Field(None, description="Error message")
    error_stack: Optional[str] = Field(None, description="Stack trace")

    # Security context
    security_event: Optional[str] = Field(None, description="Security event type")
    security_severity: Optional[str] = Field(None, description="Security severity")
    security_details: Optional[Dict[str, Any]] = Field(None, description="Security event details")

    # Performance context
    duration_ms: Optional[float] = Field(None, description="Operation duration")
    database_queries: Optional[int] = Field(None, description="Number of DB queries")
    memory_mb: Optional[float] = Field(None, description="Memory usage in MB")

    # Additional context
    extra: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# ============================================================================
# STRUCTURED LOGGER CLASS
# ============================================================================


class StructuredLogger:
    """Enhanced logger with structured output and correlation IDs"""

    def __init__(self, name: str, level: str = "INFO"):
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level))

        # Remove existing handlers
        self.logger.handlers = []

        # Create structured formatter
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredFormatter())
        self.logger.addHandler(handler)

        # Disable propagation to avoid duplicate logs
        self.logger.propagate = False

    def _create_log_entry(self, level: str, category: str, message: str, **kwargs) -> StructuredLogEntry:
        """Create a structured log entry with context"""

        # Get correlation ID from context
        correlation_id = correlation_id_var.get()

        # Build log entry
        entry = StructuredLogEntry(
            level=level, category=category, message=message, correlation_id=correlation_id, **kwargs
        )

        return entry

    def debug(self, message: str, category: str = LogCategory.SYSTEM, **kwargs):
        """Log debug message"""
        entry = self._create_log_entry(LogLevel.DEBUG, category, message, **kwargs)
        self.logger.debug(entry.json())

    def info(self, message: str, category: str = LogCategory.SYSTEM, **kwargs):
        """Log info message"""
        entry = self._create_log_entry(LogLevel.INFO, category, message, **kwargs)
        self.logger.info(entry.json())

    def warning(self, message: str, category: str = LogCategory.SYSTEM, **kwargs):
        """Log warning message"""
        entry = self._create_log_entry(LogLevel.WARNING, category, message, **kwargs)
        self.logger.warning(entry.json())

    def error(self, message: str, category: str = LogCategory.ERROR, exception: Optional[Exception] = None, **kwargs):
        """Log error message with optional exception"""

        # Add exception details if provided
        if exception:
            kwargs["error_type"] = type(exception).__name__
            kwargs["error_message"] = str(exception)
            kwargs["error_stack"] = traceback.format_exc()

        entry = self._create_log_entry(LogLevel.ERROR, category, message, **kwargs)
        self.logger.error(entry.json())

    def critical(
        self, message: str, category: str = LogCategory.ERROR, exception: Optional[Exception] = None, **kwargs
    ):
        """Log critical message"""

        if exception:
            kwargs["error_type"] = type(exception).__name__
            kwargs["error_message"] = str(exception)
            kwargs["error_stack"] = traceback.format_exc()

        entry = self._create_log_entry(LogLevel.CRITICAL, category, message, **kwargs)
        self.logger.critical(entry.json())

    def security(
        self, message: str, event_type: str, severity: str = "medium", details: Optional[Dict] = None, **kwargs
    ):
        """Log security event"""

        kwargs["security_event"] = event_type
        kwargs["security_severity"] = severity
        kwargs["security_details"] = details or {}

        entry = self._create_log_entry(LogLevel.SECURITY, LogCategory.SECURITY, message, **kwargs)
        self.logger.warning(entry.json())  # Use warning level for security events

    def request(self, request: Request, **kwargs):
        """Log incoming request"""

        entry = self._create_log_entry(
            LogLevel.INFO,
            LogCategory.REQUEST,
            f"Incoming {request.method} {request.url.path}",
            request_method=request.method,
            request_path=request.url.path,
            request_ip=request.client.host if request.client else None,
            **kwargs,
        )
        self.logger.info(entry.json())

    def response(self, request: Request, response: Response, duration_ms: float, **kwargs):
        """Log outgoing response"""

        entry = self._create_log_entry(
            LogLevel.INFO,
            LogCategory.RESPONSE,
            f"Response {response.status_code} for {request.method} {request.url.path}",
            request_method=request.method,
            request_path=request.url.path,
            response_status=response.status_code,
            response_time_ms=duration_ms,
            **kwargs,
        )
        self.logger.info(entry.json())

    def database(self, operation: str, table: str, duration_ms: float, **kwargs):
        """Log database operation"""

        entry = self._create_log_entry(
            LogLevel.DEBUG,
            LogCategory.DATABASE,
            f"Database {operation} on {table}",
            duration_ms=duration_ms,
            extra={"operation": operation, "table": table},
            **kwargs,
        )
        self.logger.debug(entry.json())

    def performance(self, operation: str, duration_ms: float, **kwargs):
        """Log performance metrics"""

        entry = self._create_log_entry(
            LogLevel.INFO,
            LogCategory.PERFORMANCE,
            f"Performance: {operation} took {duration_ms:.2f}ms",
            duration_ms=duration_ms,
            **kwargs,
        )
        self.logger.info(entry.json())


# ============================================================================
# CUSTOM FORMATTER
# ============================================================================


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON output"""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""

        # If message is already JSON, return as-is
        if isinstance(record.msg, str) and record.msg.startswith("{"):
            return record.msg

        # Otherwise create structured entry
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id_var.get(),
        }

        # Add exception info if present
        if record.exc_info:
            entry["error_stack"] = self.formatException(record.exc_info)

        return json.dumps(entry)


# ============================================================================
# CORRELATION ID MANAGEMENT
# ============================================================================


def generate_correlation_id() -> str:
    """Generate a unique correlation ID"""
    return f"corr_{uuid.uuid4().hex[:16]}"


def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """Set correlation ID in context"""

    if not correlation_id:
        correlation_id = generate_correlation_id()

    correlation_id_var.set(correlation_id)
    return correlation_id


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID from context"""
    return correlation_id_var.get()


# ============================================================================
# REQUEST LOGGING MIDDLEWARE
# ============================================================================


async def log_request_middleware(request: Request, call_next):
    """Middleware to log requests with correlation IDs"""

    import time
    from fastapi import Response

    # Generate or extract correlation ID
    correlation_id = request.headers.get("X-Correlation-ID")
    if not correlation_id:
        correlation_id = generate_correlation_id()

    # Set correlation ID in context
    set_correlation_id(correlation_id)

    # Store in request state for access in endpoints
    request.state.correlation_id = correlation_id
    request.state.request_id = f"req_{uuid.uuid4().hex[:8]}"

    # Create logger
    logger = get_logger("api.request")

    # Log request
    logger.request(request, request_id=request.state.request_id, user_id=getattr(request.state, "user_id", None))

    # Process request and measure time
    start_time = time.time()

    try:
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Request-ID"] = request.state.request_id

        # Log response
        logger.response(
            request,
            response,
            duration_ms,
            request_id=request.state.request_id,
            user_id=getattr(request.state, "user_id", None),
        )

        return response

    except Exception as e:
        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log error
        logger.error(
            f"Request failed: {str(e)}",
            exception=e,
            request_id=request.state.request_id,
            request_method=request.method,
            request_path=request.url.path,
            response_time_ms=duration_ms,
        )

        raise


# ============================================================================
# LOGGER FACTORY
# ============================================================================

# Global logger cache
_loggers: Dict[str, StructuredLogger] = {}


def get_logger(name: str, level: str = "INFO") -> StructuredLogger:
    """Get or create a structured logger"""

    if name not in _loggers:
        _loggers[name] = StructuredLogger(name, level)

    return _loggers[name]


# ============================================================================
# LOGGING DECORATORS
# ============================================================================


def log_execution(category: str = LogCategory.BUSINESS):
    """Decorator to log function execution with timing"""

    def decorator(func):
        import time
        import functools

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            start_time = time.time()

            try:
                logger.debug(
                    f"Starting {func.__name__}",
                    category=category,
                    extra={"function": func.__name__, "args_count": len(args)},
                )

                result = await func(*args, **kwargs)

                duration_ms = (time.time() - start_time) * 1000
                logger.info(
                    f"Completed {func.__name__}",
                    category=category,
                    duration_ms=duration_ms,
                    extra={"function": func.__name__},
                )

                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"Failed {func.__name__}",
                    category=category,
                    exception=e,
                    duration_ms=duration_ms,
                    extra={"function": func.__name__},
                )
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            start_time = time.time()

            try:
                logger.debug(
                    f"Starting {func.__name__}",
                    category=category,
                    extra={"function": func.__name__, "args_count": len(args)},
                )

                result = func(*args, **kwargs)

                duration_ms = (time.time() - start_time) * 1000
                logger.info(
                    f"Completed {func.__name__}",
                    category=category,
                    duration_ms=duration_ms,
                    extra={"function": func.__name__},
                )

                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"Failed {func.__name__}",
                    category=category,
                    exception=e,
                    duration_ms=duration_ms,
                    extra={"function": func.__name__},
                )
                raise

        # Return appropriate wrapper based on function type
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# ============================================================================
# SECURITY LOGGING HELPERS
# ============================================================================


def log_security_event(
    event_type: str,
    message: str,
    user_id: Optional[str] = None,
    severity: str = "medium",
    details: Optional[Dict] = None,
):
    """Log a security event with context"""

    logger = get_logger("security")
    logger.security(
        message,
        event_type=event_type,
        severity=severity,
        details=details,
        user_id=user_id,
        correlation_id=get_correlation_id(),
    )


def log_authentication_event(
    event_type: str,
    user_id: Optional[str] = None,
    success: bool = True,
    method: str = "password",
    details: Optional[Dict] = None,
):
    """Log authentication event"""

    logger = get_logger("auth")

    if success:
        logger.info(
            f"Authentication successful: {event_type}",
            category=LogCategory.AUTHENTICATION,
            user_id=user_id,
            extra={"method": method, "success": True, **(details or {})},
        )
    else:
        logger.warning(
            f"Authentication failed: {event_type}",
            category=LogCategory.AUTHENTICATION,
            user_id=user_id,
            extra={"method": method, "success": False, **(details or {})},
        )


# ============================================================================
# CONFIGURATION
# ============================================================================


def configure_logging(level: str = "INFO", json_output: bool = True, correlation_id_header: str = "X-Correlation-ID"):
    """Configure global logging settings"""

    # Set root logger level
    logging.getLogger().setLevel(getattr(logging, level))

    # Configure JSON output
    if json_output:
        # Set up JSON formatter for all handlers
        for handler in logging.getLogger().handlers:
            handler.setFormatter(StructuredFormatter())

    # Store configuration
    _config = {"level": level, "json_output": json_output, "correlation_id_header": correlation_id_header}

    # Log configuration
    logger = get_logger("system")
    logger.info("Logging configured", category=LogCategory.SYSTEM, extra=_config)
