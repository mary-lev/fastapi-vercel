# Backend Audit: Findings to Fix

Date: 2026-09-04
Scope: `fastapi-vercel/` (app.py, routes/, utils/, db.py, config.py), with cross-checks against
`python_course_bot/` and `frontend-template/` to see which endpoints are actually used.

## Context: how auth works today

Two auth systems coexist and both must be kept:

| System | Client | Backend endpoints | Status |
|---|---|---|---|
| Telegram link (current) | Bot (`services/backend_service.py`), frontend `/telegram/complete` page | `POST /api/v1/auth/telegram/link`, `POST /api/v1/auth/telegram/complete`, `GET /api/v1/auth/telegram/status/{id}` (routes/auth.py) | Primary |
| Username/password (old) | Frontend NextAuth credentials provider, Login component | `POST /users/register`, `POST /users/login`, `POST /users/update` (routes/users.py) | Keep as fallback |

Service-to-service calls (bot → backend, frontend → backend) use one shared static key
(`BACKEND_API_KEY`) sent as `Authorization: Bearer <key>`.

The middleware in `utils/auth_middleware.py` recognizes only that API key. No code path ever
resolves a *user* from a request (the `AuthContext.set_user` method has zero callers), so every
dependency built on `get_current_user` (`require_student`, `require_professor`, `require_admin`,
`utils/permissions.py`) always returns 401 and is effectively dead.

---

## Status (2026-09-04)

Findings 1, 2 and 3 are fixed in the working tree:
- `app.py` reverted so `professor_local` stays unmounted (local task editing only, never deployed).
- `routes/professor.py` router now carries `dependencies=[Depends(require_api_key)]`.
- `require_api_key` added to the task update in `routes/learning.py`, the student-form DELETE and
  `/debug` endpoints, and all six student write endpoints in `routes/student.py`.
- Regression tests: `tests/security/test_endpoint_auth_guards.py` (30 tests).

**Frontend (done, same day):** `frontend-template` now sends `Authorization: Bearer <NEXT_PUBLIC_API_KEY>`
via a shared `backendAuthHeaders()` helper in `app/utils/api-config.js`, used by:
- `app/components/Topic/CodeMirrorSectionOptimized.js` (compile, submit-code)
- `app/utils/courseAPI.js` (compile, submit-code, submit-text, solutions POST, and all per-user reads
  that previously sent `X-API-Key`, a header the backend never read)
- `app/components/student-form/StudentForm.js` and `app/(auth)/telegram/complete/page.js` (enroll)
- `app/utils/simpleMerge.js`, `app/hooks/useOptimizedTaskData.ts` (solutions reads)
- `app/api/unified-client.ts` (default header; a stored `auth_token` still overrides it)
Both repos must deploy together: backend first breaks submissions, frontend first is harmless.
Make sure `NEXT_PUBLIC_API_KEY` on Vercel equals the backend's `BACKEND_API_KEY`.

## P0: must fix before next deploy

### 1. Uncommitted change mounts an unauthenticated admin router
- **Where:** `app.py` working tree diff (lines ~239-243), `routes/professor_local.py`
- **Problem:** The diff uncomments `app.include_router(professor_local.router)`. That file's own
  docstring says "No authentication required - for local development only". It exposes 22
  endpoints under `/api/v1/professor/*` including `DELETE /tasks/{id}`, `DELETE /topics/{id}`,
  `POST /tasks/bulk-create`, `PUT /courses/{id}`, and two OpenAI generation endpoints that use
  `gpt-5` (real cost per call). Pushing to `main` auto-deploys to Vercel.
- **Fix:** Do not commit as-is. Either
  (a) mount it only when an env flag is set (e.g. `ENABLE_LOCAL_PROFESSOR_TOOLS=true`, never set on
  Vercel), or
  (b) add `Depends(require_api_key)` to the router (`APIRouter(dependencies=[...])`) so the
  `professor-app/` Vite client must send the key.
  Option (a) is the smaller change; (b) is needed anyway if the professor app is ever deployed.

### 2. Student write endpoints have no authentication at all
- **Where:** `routes/student.py`: `POST /{user_id}/submit-code` (l.1557), `POST /{user_id}/submit-text`
  (l.1901), `POST /{user_id}/solutions` (l.968), `POST /{user_id}/submissions` (l.869),
  `POST /{user_id}/enroll` (l.1211), `POST` at l.1342 (compile)
- **Problem:** These call the legacy `resolve_user()` helper (l.151), which only looks the user up.
  Anyone who knows a username or `internal_user_id` can submit code, trigger paid `gpt-5-mini`
  grading, and record solutions as that user. The *read* endpoints in the same file do require the
  key via `get_user_by_id`, so the write side is strictly weaker than the read side.
- **Fix:** Replace `resolve_user(user_id, db)` with `await resolve_user_flexible(user_id, request, db)`
  (already exists in `utils/auth_dependencies.py`, l.171) in each of these handlers. Then delete the
  legacy `resolve_user` helper.

### 3. Unguarded professor/admin endpoints
- **Where:**
  - `routes/professor.py`: all 11 endpoints, including `GET /users` labelled "admin only" (l.594),
    `POST /task-generator/generate` (l.539, calls OpenAI)
  - `routes/learning.py`: `PUT .../tasks/{task_id}` (l.1016) rewrites task content
  - `routes/student_form.py`: `DELETE /student-form/{id}` (l.289), `POST /student-form/debug` (l.322)
- **Fix:** Add `dependencies=[Depends(require_api_key)]` on the professor router and on the three
  write endpoints above. Remove or gate the `/debug` endpoint.

---

## P1: correctness and deployment mismatches

### 4. Bot calls two endpoints that do not exist
- **Where:** `python_course_bot/services/backend_service.py` l.295 (`GET /api/v1/homeworks/upcoming`)
  and l.324 (`GET /api/v1/courses/{course_id}/students`)
- **Problem:** Neither route is defined anywhere in the backend. The only "homeworks" route lives in
  `routes/telegram_bot.py` at `/api/homeworks/upcoming`, and that router is **never mounted** in
  `app.py` (see finding 10).
- **Fix:** Decide which side is right. Either mount `telegram_bot.router` under `/api/v1` and adjust
  its paths, or implement the two routes in `routes/learning.py` / `routes/student.py`. Check the bot
  fails gracefully in the meantime.

### 5. Connection pool sized for a long-lived server, deployed on serverless
- **Where:** `db.py` l.36-52: `pool_size=20, max_overflow=30`
- **Problem:** On Vercel every function instance builds its own pool, so this multiplies connections
  instead of sharing them, and Postgres connection limits get hit under load.
- **Fix:** Use `NullPool` (or `pool_size=1, max_overflow=0`) when `VERCEL` env var is set; keep the
  current pool for local `uvicorn`. Use the pooled `POSTGRES_URL` (pgbouncer) from Vercel Postgres.

### 6. Rate limiting and security blocks are per-process
- **Where:** `utils/rate_limiting.py` (`InMemoryRateLimiter`, plain dicts)
- **Problem:** State resets on every cold start and is not shared across instances, so limits and
  user blocks effectively do not apply in production.
- **Fix:** Either accept it and document it as "local only", or back the limiter with the database
  (a small `rate_limit_events` table) since no Redis is provisioned. The `cache_manager` LRU has the
  same per-instance issue but is harmless.

### 7. Assignment uploads go to ephemeral storage
- **Where:** `routes/assignments.py` l.39: `UPLOAD_DIR = /tmp/uploads/assignments` on Vercel
- **Problem:** `TaskSolution.file_path` is persisted, but the file disappears when the instance is
  recycled. `GET /{solution_id}/file` will 404 later.
- **Fix:** Store file bytes in the database (`LargeBinary` column, files are small student
  submissions) or in Vercel Blob. Minimum: store the text content, which the code already reads for
  evaluation.

### 8. Student code subprocess inherits all server secrets
- **Where:** `utils/checker.py` l.180: `exec_env = os.environ.copy()`
- **Problem:** The child process gets `OPENAI_API_KEY`, `POSTGRES_PASSWORD`, `BACKEND_JWT_SECRET`,
  etc. The AST sanitizer blocks `os`/`subprocess`/`sys` imports, but that is the only barrier.
- **Fix:** Build a minimal env: `{"PATH": ..., "PYTHONPATH": deps_path, "PYTHONHASHSEED": "0",
  "LANG": ...}`. No secrets. Also consider `resource.setrlimit` for memory in a `preexec_fn`.

### 9. Health endpoint lies
- **Where:** `app.py` `/health` returns hardcoded `"database": "operational"`
- **Fix:** Either drop the `checks` block or call `get_quick_health_status()` like `/health/quick`
  does. Also `/` and `/api/v1` advertise "JWT Bearer tokens" and "progressive penalties" that do not
  exist; trim to what is real.

---

## P2: dead code and duplication

### 10. Unmounted router: `routes/telegram_bot.py`
- Never imported in `app.py`. Its 9 endpoints (`/api/users/{telegram_id}`, `/api/homeworks/upcoming`,
  `/api/contact-message`, ...) are the ones documented in the monorepo CLAUDE.md, but they do not
  exist in the running app. Resolve together with finding 4, then delete or mount.

### 11. Duplicate Telegram auth router: `routes/telegram_auth.py`
- Mounted at `/api/auth/telegram/*` and marked "Legacy-compatible endpoints used in tests".
  Neither the bot nor the frontend calls these paths; both use `/api/v1/auth/telegram/*`
  (`routes/auth.py`). ~340 lines duplicating the same link/complete/status logic.
- **Fix:** Point `tests/test_telegram_auth.py` at the v1 paths, then delete `telegram_auth.py`.

### 12. Shadowed module: root `schemas.py`
- The `schemas/` package takes precedence on import; nothing imports the root file. Delete it
  (486 lines).

### 13. Unused utils
- `utils/query_optimizer.py` and `utils/personalized_task_generator.py`: no importers in app code.
- `utils/permissions.py`: only used by `routes/auth_demo.py`, which itself depends on the
  non-functional user auth (see Context). Either delete `auth_demo.py` + `permissions.py`, or keep
  them and implement user resolution properly (finding 15).

### 14. Two logging systems, two request IDs
- `utils/logging_config.py` (plain logger) and `utils/structured_logging.py` (JSON, correlation IDs)
  are both in use across routes.
- The logging middleware sets `request.state.request_id` (`req_xxx`), which appears in error JSON
  bodies. The auth middleware then overwrites the `X-Request-ID` response header with a different
  uuid. A client sees one ID in the header and another in the body.
- **Fix:** In `auth_middleware.py`, reuse `request.state.request_id` instead of generating a new one,
  and stop setting the header there. Migrate remaining `logging_config` users to `structured_logging`
  over time.

---

## P3: app.py hygiene

### 15. Make user-level auth real or remove it
- Decide: is per-user auth needed on the backend, or is "API key + user_id in path" the model?
  If the latter (which is what every client actually does), delete `get_current_user`,
  `require_*`, `create_auth_dependency`, `optional_auth`, `permissions.py`, `auth_demo.py`.
  If the former, `add_auth_context_to_request` needs to verify the session JWT from
  `routes/auth.py` and call `auth_context.set_user`.

### 16. `app.py` cleanups
- `COMMON_RESPONSES` is fetched 9 times via `__import__("schemas.openapi_models", ...)`. Replace with
  `from schemas.openapi_models import COMMON_RESPONSES` once and pass `responses=COMMON_RESPONSES`.
- Unused imports: `uuid`, `json`, `SECURITY_SCHEMES`.
- `datetime.utcnow()` is deprecated in Python 3.12; use `datetime.now(timezone.utc)`.
- `/api/v1` info endpoint claims `release_date: 2024-01-15`; drop or update.

### 17. Config defaults
- `config.py`: `BACKEND_API_KEY`, `BACKEND_JWT_SECRET`, `SESSION_SECRET` default to placeholder
  strings. Make them required (no default) so a misconfigured deploy fails at startup instead of
  accepting `"your-secure-api-key-here"` as a valid key.
- `PROFESSOR_INFO` is a JSON blob in an env var with a TODO to move it to the database
  (`CourseInstructor` model already exists).

### 18. Tests
- `tests/conftest.py` l.58 calls `test_engine.execute(...)`, removed in SQLAlchemy 2.0. Per-test
  cleanup raises. Use `with test_engine.begin() as conn: conn.execute(table.delete())`.
- Test env sets `TELEGRAM_BOT_API_KEY` but the backend reads `BACKEND_API_KEY`.

---

## Suggested order

1. Finding 1 (gate `professor_local`) before any commit of the current working tree.
2. Findings 2 and 3 (auth on write endpoints) as one small PR: they are one-line dependency additions.
3. Finding 4 + 10 (bot endpoint mismatch) since it affects students now.
4. Findings 5, 7, 8 (serverless correctness).
5. Deletions (11, 12, 13) as a single cleanup PR.
6. Everything else opportunistically.
