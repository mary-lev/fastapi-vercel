"""
Security-enhanced Pydantic schemas for code execution endpoints
"""

from pydantic import BaseModel, Field, validator, field_validator
from typing import Optional
from utils.security_validation import validate_code_request, validate_text_request

class SecureCompileRequest(BaseModel):
    """Secure version of CompileRequest with input validation"""
    code: str = Field(
        ..., 
        description="Code to compile/run",
        min_length=1,
        max_length=10000
    )
    language: str = Field(
        default="python", 
        description="Programming language",
        pattern="^(python)$"  # Only allow python for now
    )
    
    @validator('code')
    def validate_code_security(cls, v):
        """Validate code for security issues"""
        is_valid, error_message = validate_code_request(v, "python")
        if not is_valid:
            raise ValueError(error_message)
        return v.strip()
    
    @validator('language')  
    def validate_language(cls, v):
        """Ensure only supported languages"""
        if v.lower() not in ["python"]:
            raise ValueError(f"Language '{v}' is not supported")
        return v.lower()

class SecureCodeSubmitRequest(BaseModel):
    """Secure version of CodeSubmitRequest with input validation"""
    code: str = Field(
        ..., 
        description="Code to submit",
        min_length=1,
        max_length=10000
    )
    task_id: int = Field(..., description="Task ID", gt=0)
    language: str = Field(
        default="python", 
        description="Programming language",
        pattern="^(python)$"
    )
    
    @validator('code')
    def validate_code_security(cls, v):
        """Validate code for security issues"""
        is_valid, error_message = validate_code_request(v, "python")
        if not is_valid:
            raise ValueError(error_message)
        return v.strip()
    
    @validator('language')
    def validate_language(cls, v):
        """Ensure only supported languages"""
        if v.lower() not in ["python"]:
            raise ValueError(f"Language '{v}' is not supported")
        return v.lower()

class SecureTextSubmitRequest(BaseModel):
    """Secure version of TextSubmitRequest with input validation"""
    user_answer: str = Field(
        ..., 
        description="Text answer to submit",
        min_length=1,
        max_length=5000
    )
    task_id: int = Field(..., description="Task ID", gt=0)
    
    @validator('user_answer')
    def validate_text_security(cls, v):
        """Validate text for security issues"""
        is_valid, error_message = validate_text_request(v)
        if not is_valid:
            raise ValueError(error_message)
        return v.strip()

# Rate limiting support models
class RateLimitInfo(BaseModel):
    """Information about rate limiting"""
    attempts_remaining: int = Field(..., description="Number of attempts remaining")
    reset_time: Optional[int] = Field(None, description="Unix timestamp when limit resets")
    limit_type: str = Field(..., description="Type of limit: hourly, daily, etc.")

class SecurityValidationResponse(BaseModel):
    """Response model for security validation results"""
    is_valid: bool = Field(..., description="Whether input passed validation")
    violations_found: int = Field(default=0, description="Number of security violations found")
    risk_score: int = Field(default=0, description="Risk score (0-100)")
    message: Optional[str] = Field(None, description="Validation message")