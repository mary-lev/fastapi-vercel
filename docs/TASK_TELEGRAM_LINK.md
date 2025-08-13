## Project: Telegram account linking (magic link) across Bot → Next.js → FastAPI

### Goal
Enable students to tap a “Link account” button in the Telegram bot, land on the website, and be automatically registered/logged in with their `telegram_user_id` linked to their user account.

### Non‑Goals
- Implementing Telegram Login Widget/WebApp flows (optional future)
- Replacing existing auth; this is an additional entry path
- Social login providers

---

## Backend (FastAPI) – Tasks

### Data model
- Add `users.telegram_user_id` (BIGINT, nullable, unique index)
- Enforce uniqueness; decide policy if a different user is already linked
- Optional audit store for link tokens: Redis or DB table with `jti`, `telegram_user_id`, `issued_at`, `expires_at`, `used_at`

### Environment
- `BACKEND_API_KEY`: shared secret for bot → backend
- `BACKEND_JWT_SECRET`: signing secret if using JWT link tokens
- `BACKEND_JWT_AUDIENCE` (optional): e.g., `telegram-link`
- `FRONTEND_BASE_URL`: e.g., `https://your-app.vercel.app`
- `SESSION_SECRET` (if issuing your own session JWTs)
- `REDIS_URL` (if using Redis)

### Endpoints
- POST `/api/auth/telegram/link` (auth: `Authorization: Bearer ${BACKEND_API_KEY}`)
  - Input: `{ "telegram_user_id": number }`
  - Create a short‑lived, single‑use token (TTL 3–10 minutes)
  - Token options:
    - JWT with claims: `sub=telegram-link`, `telegram_user_id`, `jti`, `iat`, `exp`, `aud` (optional)
    - Opaque random token stored in Redis/DB with same metadata
  - Persist `jti` to enforce single use
  - Return `{ "link_url": "${FRONTEND_BASE_URL}/telegram/complete?token=${token}" }`
  - Errors: 401 (bad API key), 429 (rate‑limit)

- POST `/api/auth/telegram/complete`
  - Input: `{ "token": string }`
  - Verify token signature/format and expiry
  - Enforce single use via `jti` (mark used on success)
  - Upsert user; set `user.telegram_user_id = claims.telegram_user_id`
  - Create session and return
    - Option A: `{ token: "session-jwt" }`
    - Option B: set HttpOnly cookie (if invoked via same‑site route)
  - Return: `{ status: "ok", user: { id, telegram_user_id }, token? }`
  - Errors: 400 (`TOKEN_INVALID|TOKEN_EXPIRED|TOKEN_USED`), 409 (already linked to another user, if disallowed), 500

### Security
- HTTPS only
- Short TTL for link tokens (3–10 min)
- Single‑use via `jti`
- Do not put PII in token beyond `telegram_user_id`
- Rate‑limit `/api/auth/telegram/link` per user/IP
- Validate `aud`/`iss` for JWT (recommended)

### Sessions and cookies
- Prefer HttpOnly, Secure cookies with `SameSite=Lax` (or `None` if cross‑site)
- If cross‑origin, configure CORS minimally and allow credentials only where required

### CORS
- Allow the Next.js domain for `/api/auth/telegram/complete` if called cross‑origin
- Disallow wildcard credentials

### Observability
- Log issuance and completion (never log raw tokens)
- Metrics: `telegram_link_requested`, `telegram_link_completed`, `telegram_link_invalid`, `telegram_link_expired`

### Tests
- Unit: token issue/verify, single‑use, expiry, upsert/link
- Integration: full flow (link → complete → session), double‑submit (second fails)

### Acceptance criteria
- `/api/auth/telegram/link` returns a valid link for a given `telegram_user_id`
- Visiting the link and posting the token completes linking and signs in
- Tokens cannot be reused or used after expiry
- Users end up with `telegram_user_id` set and unique

---

## Frontend (Next.js/Vercel) – Tasks

### Route `/telegram/complete`
- Read `token` from query
- Call a Next.js API route (recommended) or backend directly to complete linking
- Show loading state; on success redirect to dashboard
- On error, show specific message (expired/used/invalid) and a button to reopen the Telegram bot to request a new link

### Next.js API route `/api/telegram/complete` (recommended)
- Method: POST `{ token }`
- Server‑to‑server call to FastAPI `/api/auth/telegram/complete`
- If backend returns a session token, set an HttpOnly, Secure cookie for the app domain; return `{ ok: true }`

### UI/UX
- Add “Link Telegram” CTA in profile/settings if `telegram_user_id` is missing
- Optional dashboard banner prompting to link if not yet linked
- Success confirmation after linking

### Configuration
- `BACKEND_URL` for server‑side calls in the API route
- `NEXT_PUBLIC_BACKEND_URL` only if calling backend directly from the browser

### Tests
- E2E: success and all error paths on `/telegram/complete`
- API route unit tests: success, expired, invalid, used

### Acceptance criteria
- Visiting `/telegram/complete?token=valid` signs in and redirects
- Error states render clearly and guide the user back to the bot to get a new link
- Session persists across reloads

---

## Bot (python-telegram-bot) – Integration
- `/link` command implemented (already in repo):
  - Calls backend `POST /api/auth/telegram/link` with `telegram_user_id`
  - Sends user an `InlineKeyboardButton(url=...)` to the Next.js page
- Add `/link` to help or menus for visibility

---

## Rollout plan
- Phase 1: Verify flow with mock backend (provided in repo)
- Phase 2: Implement real FastAPI endpoints with Redis/DB token storage and DB migration
- Phase 3: Integrate Next.js API route and page on staging; verify cookies/CORS
- Phase 4: Enable `/link` in production bot; monitor logs/metrics

---

## Edge cases
- Expired link → show guidance to request a new link from the bot
- Reused link → show invalid/used message
- Telegram ID already linked elsewhere → decide policy (reject or admin reassign)

---

## API contracts (final)

### POST `/api/auth/telegram/link`
- Headers: `Authorization: Bearer ${BACKEND_API_KEY}`
- Body: `{ "telegram_user_id": number }`
- 200: `{ "link_url": "https://your-app/telegram/complete?token=..." }`
- 401/429/500: JSON error payload

### POST `/api/auth/telegram/complete`
- Body: `{ "token": string }`
- 200: `{ "status": "ok", "user": { "id": number, "telegram_user_id": number }, "token"?: string }`
- 400: `{ "error": "TOKEN_INVALID|TOKEN_EXPIRED|TOKEN_USED" }`
- 409/500: JSON error payload


