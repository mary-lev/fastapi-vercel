## Codebase Cleanup and Optimization Plan

### Completed in this pass
- Removed legacy app files: `app_v2.py`, `app_v2_clean.py`, `app_backup_*.py`, `app_original_backup.py`.
- Removed unused `SessionRecording` model and DB usage; kept file-based session storage for `routes/session.py`.
- Fixed `routes/student.py`:
  - Replaced undefined `user` with `user_id` in lesson progress joins.
  - Renamed `submitted_data` to `attempt_content` to match `models.TaskAttempt`.
- Prevented `utils/sessions.py` from executing on import by guarding with `if __name__ == "__main__"`.
- Cleaned `db.py` unused `Base` import and aligned to single declarative base.
- Fixed `pyproject.toml` `requires-python` to ">=3.9".
- Updated `README.md` to correct venv name and run command.

### Next actions
1. Unused imports cleanup
   - Remove imports flagged by linter across `routes/*`, `utils/*`, `data/export.py`, tests, and exclude `alembic/versions`.
   - Add Ruff config to exclude `venv`, `dependencies`, and `alembic/versions`.

2. Session routes deprecation
   - Remove or deprecate session-related endpoints in `routes/auth.py` and `routes/session.py` if not used.
   - Delete `schemas` related to sessions (`SessionRecording*`) if not referenced.

3. Database base unification
   - Use a single declarative `Base` (from `base.py` or `models.py`) everywhere; migrate Alembic if needed.

4. Query efficiency improvements
   - Batch fetch in `get_user_solutions` (join Task to avoid per-row lookup).
   - Consider aggregate queries for course progress; add indexes on `Task.topic_id`, `Lesson.course_id`, `TaskAttempt(user_id, task_id)`.

5. CORS/env consistency
   - Centralize CORS origins in env (`settings.CORS_ORIGINS`) and use in all app variants (now only `app.py`).

6. Test hygiene
   - Fix ambiguous var names and unused imports in tests; remove `bare except` and pointless f-strings.

7. CI and tooling
   - Add `ruff` and `black` to dev extras. Configure pre-commit.

8. Dead code removal
   - Delete `utils/task_import.py` unused imports and dead variables; similar cleanups across `routes/*`.

9. Docs
   - Keep `docs/PHASE_*` up to date; ensure `ENDPOINT_COMPARISON.md` matches `app.py` routing.

# FastAPI Application Improvement Plan

## 🎯 Implementation Strategy

This plan prioritizes **database-safe improvements** first, followed by schema changes that require careful migration planning.

---

## 📋 PHASE 1: IMMEDIATE FIXES (No Database Impact)

### ✅ COMPLETED
- [x] Move API key to environment variables

### 🔄 IN PROGRESS
- [ ] Fix hardcoded API key usage in telegram_bot.py
- [ ] Align dependency versions (requirements.txt vs pyproject.toml)
- [ ] Fix duplicate function names in routes/task.py
- [ ] Standardize database session management
- [ ] Add proper error handling and logging
- [ ] Add input validation schemas

---

## 🚨 CRITICAL ISSUES (Immediate Action Required)

### 1. **Security Issues**
| Issue | File | Priority | Database Impact |
|-------|------|----------|----------------|
| Hardcoded API key | `routes/telegram_bot.py:20` | CRITICAL | None |
| Code execution sandbox | `utils/checker.py:85-95` | HIGH | None |
| Database session leaks | Multiple files | HIGH | None |

### 2. **Bugs & Inconsistencies**
| Issue | File | Priority | Database Impact |
|-------|------|----------|----------------|
| Duplicate function names | `routes/task.py` | HIGH | None |
| Dependency version conflicts | `requirements.txt` vs `pyproject.toml` | HIGH | None |
| Generic exception handling | Multiple route files | MEDIUM | None |

---

## 🔧 PHASE 2: CODE QUALITY IMPROVEMENTS (No Database Changes)

### Database Session Management
**Files to Update**: 13 files using `SessionLocal()` directly
- `routes/users.py`
- `routes/solution.py`
- `routes/analysis.py`
- `routes/course.py`
- `routes/lesson.py`
- `routes/task.py`
- `routes/submission.py`
- `utils/task_generator.py`
- `routes/topics.py`
- `routes/session.py`
- `utils/task_import.py`
- `export.py`

**Change Pattern**:
```python
# FROM (current pattern)
db: Session = SessionLocal()
try:
    # operations
finally:
    db.close()

# TO (dependency injection)
def endpoint(db: Session = Depends(get_db)):
    # operations - session auto-closed
```

### Error Handling Standardization
**Pattern to Replace**:
```python
# Current generic handling
except Exception as e:
    db.rollback()
    raise HTTPException(status_code=500, detail=str(e))

# Replace with specific handling
except IntegrityError as e:
    db.rollback()
    raise HTTPException(status_code=409, detail="Resource conflict")
except SQLAlchemyError as e:
    db.rollback()
    logger.error(f"Database error: {e}")
    raise HTTPException(status_code=500, detail="Database operation failed")
```

### Input Validation Schemas
**Add Pydantic models for**:
- Task update operations
- User registration/updates
- Course/Lesson creation
- Session data validation

---

## 📊 PHASE 3: PERFORMANCE IMPROVEMENTS (Requires Database Planning)

### Database Optimizations (Requires Migration)
```sql
-- Add these indexes (will require Alembic migration)
CREATE INDEX CONCURRENTLY idx_tasks_topic_id ON tasks(topic_id);
CREATE INDEX CONCURRENTLY idx_tasks_created_at ON tasks(created_at);
CREATE INDEX CONCURRENTLY idx_task_attempts_user_task ON task_attempts(user_id, task_id);
CREATE INDEX CONCURRENTLY idx_ai_feedback_task_user ON ai_feedback(task_id, user_id);
```

### Query Optimization (Code Changes Only)
```python
# Update relationship loading strategies
topics = relationship("Topic", back_populates="lesson", lazy="selectin")
tasks = relationship('Task', backref='topic', lazy='dynamic', order_by='Task.order')
```

---

## 🏗️ PHASE 4: ARCHITECTURE IMPROVEMENTS (No Database Impact)

### Repository Pattern Implementation
- Create `repositories/` directory
- Implement `TaskRepository`, `UserRepository`, etc.
- Centralize data access logic

### Enhanced Security Sandbox
- Add memory limits to code execution
- Implement better temp file management
- Add rate limiting for code execution

### Logging & Monitoring
- Structured logging throughout application
- Performance monitoring endpoints
- Health check improvements

---

## ⚠️ DATABASE MIGRATION CONSIDERATIONS

### Safe Migration Strategy
1. **Create indexes CONCURRENTLY** to avoid blocking
2. **Test migrations on copy of production data**
3. **Plan for rollback scenarios**
4. **Monitor performance during migration**

### Migration Files to Create
```bash
# For index additions
alembic revision --autogenerate -m "add_performance_indexes"

# For relationship loading changes (if any model changes needed)
alembic revision --autogenerate -m "optimize_relationship_loading"
```

---

## 🚀 IMPLEMENTATION ORDER

### Week 1: Critical Fixes (Database Safe)
1. Fix hardcoded API key ✅ (You're handling this)
2. Align dependency versions
3. Fix duplicate function names
4. Standardize session management

### Week 2: Quality Improvements
1. Add proper error handling
2. Implement input validation
3. Add structured logging
4. Fix naming inconsistencies

### Week 3: Performance (Plan Database Changes)
1. Create migration for indexes
2. Test on staging database
3. Update relationship loading strategies
4. Implement repository pattern

### Week 4: Architecture & Security
1. Enhanced security sandbox
2. Rate limiting implementation
3. Monitoring and health checks
4. Documentation updates

---

## 🎯 SUCCESS METRICS

- [ ] Zero hardcoded credentials
- [ ] Consistent dependency versions
- [ ] All database sessions properly managed
- [ ] Specific error handling throughout
- [ ] Input validation on all endpoints
- [ ] Performance baseline established
- [ ] Comprehensive test coverage plan
- [ ] Security audit completed

---

## 📝 NOTES

- **Database Safety**: All Phase 1-2 changes are code-only and won't affect database
- **Migration Safety**: Phase 3 database changes will be done with `CONCURRENTLY` option
- **Rollback Plan**: Each phase can be rolled back independently
- **Testing**: Each change will be tested before proceeding to next