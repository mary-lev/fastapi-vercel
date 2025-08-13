# Testing Strategy for FastAPI Application

## 🎯 Testing Priorities

### **CRITICAL PRIORITY (Must Have Before Phase 2)**
These tests protect the database and core functionality:

1. **Database Model Tests** - Ensure data integrity
2. **Core API Endpoint Tests** - Verify primary user workflows  
3. **Security Tests** - Validate input sanitization and code execution safety
4. **Session Management Tests** - Ensure our dependency injection changes work

### **HIGH PRIORITY (Phase 2)**
5. **Integration Tests** - End-to-end user workflows
6. **Performance Tests** - Database query optimization validation

### **MEDIUM PRIORITY (Phase 3)**
7. **Edge Case Tests** - Error handling and boundary conditions
8. **Load Tests** - Concurrent user scenarios

---

## 📋 REQUIRED TEST TYPES

### 1. **Database Model Tests** (Critical)
**Purpose**: Protect database integrity during schema changes
- ✅ **User model operations** - CRUD operations
- ✅ **Task polymorphic inheritance** - Ensure task types work correctly
- ✅ **Relationship integrity** - Foreign key constraints
- ✅ **Migration safety** - Test that existing data isn't corrupted

### 2. **Core API Tests** (Critical) 
**Purpose**: Verify essential user workflows work
- ✅ **Task submission flow** - `POST /api/insertTaskSolution`
- ✅ **User data retrieval** - `GET /api/getTopicSolutions/{user_id}`
- ✅ **Task management** - Create, update, delete operations
- ✅ **Course/Lesson hierarchy** - Navigate content structure

### 3. **Security Tests** (Critical)
**Purpose**: Validate security improvements
- ✅ **Input validation** - Pydantic schema validation
- ✅ **Code execution sandbox** - Safe code execution limits
- ✅ **SQL injection protection** - ORM parameter binding
- ✅ **Authentication flow** - API key validation

### 4. **Session Management Tests** (Critical)
**Purpose**: Ensure dependency injection works correctly
- ✅ **Database session cleanup** - No connection leaks
- ✅ **Transaction rollback** - Error handling rollbacks work
- ✅ **Concurrent requests** - Session isolation

---

## 🛠️ TESTING INFRASTRUCTURE NEEDS

### Test Database Setup
```python
# Use SQLite in-memory for fast tests
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

# For integration tests, use separate test database
SQLALCHEMY_INTEGRATION_DATABASE_URL = "postgresql://user:pass@localhost/test_db"
```

### FastAPI Test Client
```python
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)
```

### Fixtures Needed
- **Test database session**
- **Sample users, courses, lessons, tasks**
- **Authentication tokens**
- **Clean database state per test**

---

## 📊 CRITICAL WORKFLOWS TO TEST

### **Workflow 1: Student Task Submission** (CRITICAL)
```
User submits solution → Task attempt recorded → Points calculated → Progress updated
```
**Tests Needed**:
- Valid submission saves correctly
- Invalid submission rejected
- Duplicate submissions handled
- Points calculation accurate

### **Workflow 2: Task Management** (HIGH)
```
Admin creates task → Students attempt → View analytics → Update task
```
**Tests Needed**:
- Task CRUD operations
- Polymorphic task types work
- Task deactivation vs deletion
- Analytics data accuracy

### **Workflow 3: Course Structure** (HIGH)
```
Course → Lesson → Topic → Task hierarchy navigation
```
**Tests Needed**:
- Hierarchy relationships maintained
- Ordering preserved
- Cascading deletes work correctly

### **Workflow 4: Code Execution** (CRITICAL - SECURITY)
```
User submits code → Sanitization → Safe execution → Result returned
```
**Tests Needed**:
- Malicious code blocked
- Resource limits enforced
- Timeout protection works
- Safe modules only

---

## 🚨 DATABASE SAFETY TESTS

### **Before Making Schema Changes**
```python
def test_existing_data_preserved():
    """Ensure existing data isn't corrupted by changes"""
    # Load sample data matching production structure
    # Apply changes
    # Verify data integrity maintained

def test_migration_rollback():
    """Ensure we can safely rollback changes"""
    # Apply migration
    # Rollback migration  
    # Verify original state restored
```

### **Model Relationship Tests**
```python
def test_cascade_deletes():
    """Ensure deleting Course doesn't orphan data"""
    
def test_foreign_key_constraints():
    """Verify referential integrity maintained"""

def test_polymorphic_task_inheritance():
    """Ensure all task types save/load correctly"""
```

---

## 🧪 RECOMMENDED TESTING TOOLS

### **Core Testing Stack**
- **pytest** - Primary testing framework
- **pytest-asyncio** - For async endpoint testing
- **pytest-xdist** - Parallel test execution
- **factory-boy** - Test data generation

### **Database Testing**
- **pytest-postgresql** - Test database management
- **pytest-alembic** - Migration testing
- **SQLAlchemy test utilities**

### **API Testing**  
- **httpx** - Async HTTP client for testing
- **FastAPI TestClient** - Built-in testing support

### **Security Testing**
- **bandit** - Security vulnerability scanning
- **safety** - Dependency vulnerability checking

---

## 📦 DEPENDENCIES TO ADD

```toml
[project.optional-dependencies]
test = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "pytest-xdist>=3.0.0",
    "pytest-postgresql>=5.0.0",
    "factory-boy>=3.2.0",
    "httpx>=0.24.0",
    "coverage>=7.0.0"
]
```

---

## 🎯 IMMEDIATE ACTION PLAN

### **Week 1: Critical Tests**
1. **Set up test infrastructure** - pytest, test database
2. **Write database model tests** - Protect data integrity  
3. **Test core API endpoints** - Task submission, user data
4. **Validate security features** - Input validation, code execution

### **Week 2: Integration Tests**
1. **End-to-end workflows** - Complete user scenarios
2. **Session management validation** - Our dependency injection changes
3. **Performance baseline** - Query performance metrics

### **Benefits Before Phase 2**:
- ✅ **Database protection** - Safe to make schema changes
- ✅ **Regression prevention** - Catch breaking changes early
- ✅ **Confidence boost** - Know changes work correctly
- ✅ **Documentation** - Tests serve as usage examples

---

## 💡 TESTING BEST PRACTICES

### **Test Organization**
```
tests/
├── unit/           # Fast, isolated tests
│   ├── test_models.py
│   ├── test_schemas.py
│   └── test_utils.py
├── integration/    # API endpoint tests  
│   ├── test_solution_api.py
│   ├── test_task_api.py
│   └── test_user_api.py
├── security/       # Security validation
│   ├── test_code_execution.py
│   └── test_input_validation.py
└── fixtures/       # Test data
    ├── conftest.py
    └── sample_data.py
```

### **Key Principles**
- **Fast unit tests** - Run in < 1 second total
- **Isolated tests** - Each test independent  
- **Clear test names** - Describe what's being tested
- **Database cleanup** - Fresh state for each test
- **Mock external dependencies** - No real API calls in tests

This testing strategy prioritizes protecting your existing database while giving confidence to continue with improvements.