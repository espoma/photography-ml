# Checkpoint — Photography ML

_Update this file at the end of every session. Most recent entry at the top._

---

## 2026-06-05

### Done this session
- **Diagnosed CI failure**: `test_endpoints.py` was a script that hit a live server (never started in CI), and `ci.yml` also referenced `test_ml_service.py` which doesn't exist — both caused consistent CI failures.
- **Rewrote `test_endpoints.py`**: now proper pytest using FastAPI `TestClient` (no live server needed). Covers 13 tests: health, auth (signup/login/me/unauthenticated/duplicate), images (upload/list/get/update/delete/404/user association). Gemini API calls are mocked.
- **Added `httpx`** to `requirements.txt` — required by Starlette 0.35.1's TestClient.
- **Fixed `ci.yml`**: removed `pytest test_ml_service.py -v` line (file doesn't exist).

### Still needs to be done (immediate)
- [ ] **Commit `backend/app/routes/`** — auth router (`auth.py` + `__init__.py`) is untracked and never committed. `main.py` imports it, so CI fails to even import the app without it. This is the next thing to push.
- [ ] **Merge `4752dbd` fix into `dev`** — `fix: load .env with absolute path so GEMINI_API_KEY available from any CWD` is sitting on `origin/feature/auth-models-security-fix` and never landed in `dev`. Worth cherry-picking.
- [ ] **Push `dev` → open PR to `master`** — `master` is still on the initial commit. Once tests pass in CI, merge `dev` → `master`.

### Backlog (from FEATURES_AND_IMPROVEMENTS.md)
- [ ] Rate limiter: switch from IP-based to user-based now that auth is in place
- [ ] Input validation: file size limit, magic bytes check, format whitelist (JPEG/PNG/WebP)
- [ ] Health check endpoint (`GET /health` returning DB status)
- [ ] Async tag generation (background task so upload doesn't block)
- [ ] UI redesign (Priority 1.5 in the roadmap)
- [ ] Image safety check (Gemini or Vision API)

---

## Architecture snapshot
```
photography-ml/
├── backend/           FastAPI + SQLModel + PostgreSQL + Gemini
│   ├── main.py        Routes: /, /images/ CRUD, rate-limited upload
│   ├── app/
│   │   ├── models.py  User, Image (PostgreSQL ARRAY for tags)
│   │   ├── database.py engine + session (reads .env)
│   │   ├── security.py JWT + Argon2
│   │   ├── routes/auth.py  /auth/signup, /auth/login, /auth/me  ← UNTRACKED
│   │   └── services/ml_service.py  Gemini multi-model fallback
│   └── test_endpoints.py  pytest + TestClient (13 tests)
├── frontend/          Next.js 16 + React 19
├── docker-compose.yml PostgreSQL container
└── .github/workflows/ci.yml  CI: backend pytest + frontend build
```

## Branch state
- `dev` = current working branch, synced with `origin/dev`
- `master` = initial commit only (nothing merged yet)
- `feature/auth-models-security-fix` = has one extra commit not in dev (`4752dbd`)
