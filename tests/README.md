# Comprehensive Test Suite

This directory contains a comprehensive test suite for the FastAPI educational platform, covering unit tests, integration tests, and security tests.

## Test Structure

```
tests/
├── conftest.py                    # Test configuration and fixtures
├── pytest.ini                     # Pytest configuration
├── test_runner.py                 # Custom test runner script
├── README.md                      # This file
├── unit/                          # Unit tests
│   ├── test_basic.py              # Basic functionality tests
│   └── test_models.py             # Database model tests
├── integration/                   # Integration tests
│   ├── test_code_execution_workflow.py      # Code execution workflows
│   ├── test_authentication_workflow.py     # Authentication workflows
│   ├── test_learning_content_workflow.py   # Learning content delivery
│   └── test_solution_api.py               # Solution API tests
└── security/                      # Security tests
    ├── test_code_execution.py     # Code execution security
    ├── test_input_validation.py   # Input validation tests
    └── test_comprehensive_security.py      # Comprehensive security suite
```

## Test Categories

### 🧪 Unit Tests
- **Basic functionality**: Core application features
- **Model validation**: Database model integrity
- **Utility functions**: Helper function correctness
- **Security validation**: Input sanitization functions

### 🔗 Integration Tests
- **Code Execution Workflow**: Complete code compilation and submission flow
- **Authentication Workflow**: User authentication and authorization
- **Learning Content Workflow**: Course navigation and content delivery
- **Solution API**: Task solution submission and retrieval

### 🔒 Security Tests
- **Code Injection Protection**: Prevention of malicious code execution
- **Input Validation**: XSS, SQL injection, and path traversal protection
- **Rate Limiting**: Progressive penalties and abuse prevention
- **Authentication Security**: Session management and access control

## Running Tests

### Using the Test Runner

```bash
# Run all tests with coverage
python tests/test_runner.py all

# Run specific test categories
python tests/test_runner.py unit
python tests/test_runner.py integration
python tests/test_runner.py security

# Run critical workflow tests
python tests/test_runner.py critical

# Run performance tests
python tests/test_runner.py performance

# Run smoke tests (quick validation)
python tests/test_runner.py smoke
```

### Using Pytest Directly

```bash
# Run all tests
pytest tests/ -v

# Run tests by marker
pytest -m "unit" -v
pytest -m "integration" -v
pytest -m "security" -v

# Run specific test files
pytest tests/security/test_comprehensive_security.py -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html:htmlcov

# Run tests matching pattern
pytest -k "code_execution" -v
```

## Test Markers

- `unit`: Unit tests
- `integration`: Integration tests
- `security`: Security tests
- `slow`: Slow running tests
- `workflow`: End-to-end workflow tests
- `authentication`: Authentication and authorization tests
- `code_execution`: Code execution and compilation tests
- `content_delivery`: Learning content delivery tests
- `performance`: Performance and load tests
- `concurrent`: Concurrent access tests

## Test Coverage Areas

### 1. Code Execution Security
- ✅ Dangerous function blocking (`eval`, `exec`, `open`, etc.)
- ✅ Malicious module detection (`os`, `subprocess`, `socket`, etc.)
- ✅ Resource limit enforcement (loops, recursion, timeout)
- ✅ AST-based code analysis
- ✅ Input size validation
- ✅ Syntax error handling

### 2. Input Validation & Sanitization
- ✅ XSS attack prevention
- ✅ SQL injection protection
- ✅ Path traversal defense
- ✅ Unicode and encoding attack protection
- ✅ Content type validation
- ✅ Input size limits

### 3. Rate Limiting & Abuse Prevention
- ✅ Request rate limiting (30 requests per 5 minutes)
- ✅ Progressive security penalties
- ✅ User blocking after violations
- ✅ Concurrent attack simulation
- ✅ Rate limit isolation between users

### 4. Authentication & Authorization
- ✅ Role-based access control
- ✅ User data isolation
- ✅ Session management
- ✅ Cross-user access protection
- ✅ User enumeration protection
- ✅ Authorization boundary testing

### 5. Learning Content Delivery
- ✅ Course hierarchy navigation
- ✅ Content ordering and structure
- ✅ Performance optimization (N+1 query prevention)
- ✅ Concurrent content access
- ✅ Content consistency across endpoints
- ✅ Error handling in navigation

### 6. Code Execution Workflows
- ✅ Complete compilation workflow
- ✅ Code submission and evaluation
- ✅ Multiple attempt handling
- ✅ Progress tracking
- ✅ Error recovery
- ✅ User isolation

## Test Data Management

### Fixtures
- `test_db`: Clean database session for each test
- `client`: TestClient with database override
- `setup_*_test_data`: Comprehensive test data setup for each workflow

### Database Handling
- SQLite in-memory database for fast tests
- Automatic table cleanup between tests
- Transaction rollback for isolation
- Test data seeding via fixtures

## Security Test Scenarios

### Code Injection Attacks
```python
# Examples of blocked code
"import os; os.system('rm -rf /')"
"exec('malicious code')"
"open('/etc/passwd', 'r').read()"
"__import__('subprocess').call(['ls'])"
```

### Web Attack Prevention
```python
# XSS attempts
"<script>alert('xss')</script>"
"<img src=x onerror=alert('xss')>"

# SQL injection attempts
"'; DROP TABLE users; --"
"' OR '1'='1"
```

### Path Traversal Prevention
```python
# Path traversal attempts
"../../etc/passwd"
"..\\..\\windows\\system32\\config\\sam"
```

## Performance Benchmarks

### Response Time Targets
- Course hierarchy loading: < 2 seconds
- Code compilation: < 5 seconds
- User authentication: < 1 second
- Content navigation: < 1 second

### Concurrency Targets
- 10+ concurrent users without degradation
- Rate limiting properly isolates users
- No race conditions in data access

## Continuous Integration

### GitHub Actions Integration
```yaml
# Example CI workflow
- name: Run Tests
  run: |
    python tests/test_runner.py all
    python tests/test_runner.py security
```

### Pre-commit Hooks
```bash
# Run critical tests before commit
python tests/test_runner.py critical
```

## Test Environment Setup

### Required Environment Variables
```bash
NODE_ENV=test
TELEGRAM_BOT_API_KEY=test_api_key
POSTGRES_USER=test_user
POSTGRES_PASSWORD=test_password
OPENAI_API_KEY=test_openai_key
```

### Dependencies
- pytest
- pytest-cov
- fastapi[test]
- sqlalchemy
- All application dependencies

## Debugging Failed Tests

### Common Issues
1. **Database Connection**: Ensure test database is accessible
2. **Environment Variables**: Check all required vars are set
3. **Rate Limiting**: Reset rate limiter between test runs
4. **Dependencies**: Verify all packages are installed

### Debug Commands
```bash
# Run with verbose output
pytest tests/security/test_comprehensive_security.py -v -s

# Run single test with debugging
pytest tests/integration/test_code_execution_workflow.py::TestCodeExecutionWorkflow::test_security_violation_workflow -v -s

# Show test duration
pytest tests/ --durations=10
```

## Test Maintenance

### Adding New Tests
1. Create test file in appropriate directory
2. Add relevant markers using `@pytest.mark.marker_name`
3. Use existing fixtures or create new ones
4. Follow naming convention: `test_*`
5. Update this README if adding new categories

### Test Data Updates
- Update fixtures in `conftest.py` for shared data
- Create workflow-specific fixtures in test files
- Ensure test isolation and cleanup

### Performance Monitoring
- Monitor test execution time
- Profile slow tests
- Optimize database operations
- Update benchmarks as needed

## Security Test Compliance

This test suite ensures compliance with:
- ✅ OWASP Top 10 security risks
- ✅ Code injection prevention standards
- ✅ Input validation best practices
- ✅ Authentication security guidelines
- ✅ Rate limiting and abuse prevention
- ✅ Educational platform security requirements

## Test Coverage Goals

- **Unit Tests**: > 80% code coverage
- **Integration Tests**: All critical workflows covered
- **Security Tests**: All attack vectors tested
- **Performance Tests**: All endpoints benchmarked

Current coverage can be viewed by running:
```bash
python tests/test_runner.py all
# Check htmlcov/index.html for detailed coverage report
```