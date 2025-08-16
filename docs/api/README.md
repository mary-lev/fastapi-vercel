# Educational Platform API Documentation

## 🎓 Overview

The Educational Platform API provides comprehensive endpoints for managing educational content, student progress, and secure code execution.

**Version**: 1.0.0  
**Base URL**: `https://fastapi-vercel-lake.vercel.app`  
**Documentation**: [Swagger UI](/docs) | [ReDoc](/redoc)

## 📚 Generated Documentation

- **[OpenAPI Specification](openapi.json)**: Complete API schema
- **[Security Guide](security_guide.json)**: Comprehensive security implementation
- **[Usage Examples](usage_examples.json)**: Code examples for all endpoints  
- **[Testing Guide](testing_guide.json)**: Complete testing documentation

## 🔗 Quick Links

- **Interactive Docs**: `/docs` - Swagger UI for testing
- **Alternative Docs**: `/redoc` - ReDoc documentation
- **Health Check**: `/health` - Service status
- **API Info**: `/api/v1` - Endpoint directory

## 🚀 Key Features

- **Secure Code Execution**: AST-based analysis and sandboxing
- **Progressive Rate Limiting**: Abuse prevention with user isolation
- **Comprehensive Authentication**: Multiple auth methods including Telegram
- **Real-time Analytics**: Student progress and course insights
- **Performance Optimized**: N+1 query prevention and caching

## 🔒 Security

- **50+ dangerous code patterns** blocked
- **Multi-layer input validation** (XSS, SQL injection, path traversal)
- **Resource management** with execution timeouts
- **User isolation** and progressive penalties
- **Comprehensive logging** for security monitoring

## 📊 Testing

- **Unit Tests**: Component-level validation
- **Integration Tests**: End-to-end workflows  
- **Security Tests**: Vulnerability assessment
- **Performance Tests**: Load and response time validation

Run tests with: `python run_tests_simple.py`

---

*Generated automatically from API specification*
