### Backend audit: findings and recommended improvements

- **Overall**: The app works for a small project but has correctness bugs, security risks (esp. code execution), tight coupling across layers, mixed async/sync, and several import-time side effects that can break tests and deployments.

### Critical correctness issues

- **Duplicate SQLAlchemy Base**
  - Two separate `Base` declarations cause schema/migration/test inconsistencies. Unify to a single `Base` and make all models inherit from it.
  ```
Base = declarative_base()
  ```
  ```
Base = declarative_base()
  ```

- **Import-time side effects (DB/file writes)**
  - Running on import can corrupt environments and crash deployments; move to CLI tasks or guard with `if __name__ == "__main__":`.
  ```
current_topic = 31
import_tasks(current_topic)
  ```

- **Enum misuse in Telegram linking**
  - Store the enum value, not a string literal.
  ```
user = User(
    internal_user_id=internal_user_id,
    telegram_user_id=telegram_user_id,
    username=f"telegram_user_{telegram_user_id}",
    hashed_sub=f"telegram:{telegram_user_id}",
    status="STUDENT"  # Should be UserStatus.STUDENT
)
  ```

- **Misspelled field in lesson payload**
  - Breaks clients that expect `lessonLink`.
  ```
"lessonType": task.type,
"lssonLink": task.task_link,  # typo
"lessonName": task.task_name,
  ```

- **Returning raw ORM objects**
  - One endpoint returns SQLAlchemy models directly; use response schemas.
  ```
user_solutions = db.query(TaskSolution).filter(TaskSolution.user_id == user.id).all()
return user_solutions
  ```

- **Session file endpoints are inconsistent**
  - One writes with a random UUID; the reader also uses a new random UUID, guaranteeing 404.
  ```
id = str(uuid4())
with open(f"data/sessions/{id}.json", "w") as f:
    json.dump(data, f)
  ```
  ```
id = str(uuid4())
with open(f"data/sessions/{id}.json", "r") as f:
    data = json.load(f)
  ```

### Security risks

- **Unsafe code execution**
  - AST checks are bypassable; execution happens in the host Python process with no OS/network/memory isolation. Replace with a sandboxed runner or remove until safe.
  ```
ALLOWED_MODULES = ["anytree", "math", "random", "datetime"]
DANGEROUS_FUNCTIONS = ["eval", "exec", "compile", "open", "input"]
  ```
  ```
result = subprocess.run(
    [sys.executable, file_path],
    capture_output=True,
    text=True,
    timeout=5,
    check=True,
    env={...},
)
  ```

- **Admin-grade endpoints lack auth**
  - Task create/update/delete, analytics, and generation endpoints are publicly accessible. Add JWT-based auth and role checks across routers.

- **In-memory rate limiting (per-instance only)**
  - Not effective across multiple instances; use Redis-backed rate limiting.
  ```
rate_limiter = InMemoryRateLimiter()
def rate_limit(max_requests: int, window_minutes: int, key_func=None):
  ```

- **Hardcoded secret defaults**
  - Fail fast if secrets not provided; remove insecure defaults for production.
  ```
BACKEND_API_KEY: str = "your-secure-api-key-here"
BACKEND_JWT_SECRET: str = "your-jwt-secret-here"
SESSION_SECRET: str = "your-session-secret-here"
  ```

- **Import-time env requirement in Telegram bot**
  - Crashes imports/tests; defer to startup or dependency.
  ```
API_KEY = os.getenv("TELEGRAM_BOT_API_KEY")
if not API_KEY:
    raise ValueError(...)
  ```

### Architecture and layering

- **Tight coupling from utils to routes**
  - Utilities import router functions; invert to a service layer callable from routers.
  ```
from routes.topics import get_topic_data
from routes.lesson import rebuild_task_links
  ```

- **Mixed async/sync with blocking calls**
  - `subprocess`, SQLAlchemy sync, and OpenAI calls inside async endpoints can block the loop. Make endpoints sync, or offload blocking work to a threadpool, or migrate to async stack.
  ```
result = run_code(code)
...
attempt_count = db.query(TaskAttempt)...
  ```
  ```
evaluation = evaluate_code_submission(code_submission, result.get("output"), task.data)
db.add(new_feedback)
db.commit()
  ```

- **Validation consistency**
  - Some handlers parse `request.json()` manually; standardize on Pydantic request/response models for all endpoints.

- **Pydantic v2 migration incomplete**
  - Use `ConfigDict(from_attributes=True)` and `@field_validator`.
  ```
class Config:
    from_attributes = True
  ```

### Data modeling and DB constraints

- **`User.username` not unique in DB**
  - Code checks uniqueness, but DB should enforce it to avoid races.

- **Timezone consistency**
  - Mix of naive (DB) and aware (JWT) datetimes. Standardize on UTC-aware for tokens and explicit UTC for DB.

- **JSON fields lack validation**
  - Add typed sub-schemas per task type to validate `Task.data` structure.

### Configuration, deployment, and ops

- **CORS config hardcoded**
  - Make origins configurable; default to strict in production.

- **`psycopg2-binary` in production**
  - Prefer `psycopg2` or async `asyncpg` with SQLAlchemy async.

- **Logging**
  - Good baseline; ensure sensitive data (e.g., code, tokens) isn’t logged; add request IDs and structured fields.

### Testing gaps and stability

- **Test DB schema may not include models**
  - Tests create tables via `base.Base.metadata.create_all(...)`; with two Bases, some models won’t be created. Fix Base duplication and re-run tests.
  ```
from base import Base
Base.metadata.create_all(bind=engine)
  ```

- **Add test coverage for**
  - Auth/roles on admin endpoints
  - Rate limiting behavior (Redis)
  - Telegram link flows (valid, expired, reused)
  - Code execution bypass attempts (`__import__`, `getattr`, file APIs, network)
  - OpenAI error handling/timeouts
  - Lesson navigation payload and `lessonLink` typo

### Actionable remediation plan (priority order)

1. Unify SQLAlchemy `Base`; ensure all models inherit from `base.Base`; fix Alembic/env.
2. Remove all import-time side effects; move generation/imports to CLI scripts.
3. Secure endpoints:
   - Add JWT auth and role guards; secure task management, analytics, generation routes.
   - Replace in-memory rate limiter with Redis.
4. Replace code execution with a sandboxed runner (containerized or managed service) or disable until safe.
5. Standardize Pydantic v2 usage; add response models everywhere.
6. Introduce service/repository layers; remove `utils -> routes` imports.
7. Normalize async usage; either sync endpoints or offload blocking work; consider async DB.
8. Harden config: no default secrets; separate env profiles; fail if missing in prod.
9. DB constraints: add unique index on `User.username`; validate JSON `Task.data` via sub-schemas.
10. CORS/env hardening; logging hygiene; dependency updates.

### Quick wins (low effort, high value)

- Fix `lesson.py` `lssonLink` -> `lessonLink`.
- Replace `"STUDENT"` with `UserStatus.STUDENT` in `routes/telegram_auth.py`.
- Change `routes/solution.py#get_user_solutions` to return a response schema, not ORM models.
- Defer `TELEGRAM_BOT_API_KEY` validation to a dependency function.
- Guard `utils/task_import.py` execution.


