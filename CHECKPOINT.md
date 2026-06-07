# Checkpoint — Photography ML

_Update this file at the end of every session. Most recent entry at the top._

---

## 2026-06-06

### Done this session
- **Wired in LangSmith experiment tracking**: every call to `generate_tags` is now automatically traced. Captures inputs, output tags, latency, token counts (input/output/total), model used, fallback flag.
- **Added prompt variants** to `ml_service.py`: `v1` (baseline), `v2` (structured by subject/lighting/mood), `v3` (exactly 8 category-specific tags). `generate_tags` now accepts `prompt_version` and `model_name` params — defaults unchanged so existing API and tests are unaffected.
- **Added `langsmith>=0.1.0`** to `requirements.txt`.
- **Created `backend/experiments/`** folder:
  - `config.py` — experiment matrix (prompt comparison, model comparison, best combo)
  - `run_experiment.py` — CLI runner: `python -m experiments.run_experiment --mode [prompts|models|all] --image path/to/photo.jpg`
- **Updated README** with LangSmith env vars and Experiments section.

### Still needs to be done (immediate)
- [ ] **Commit `backend/app/routes/`** — still untracked (auth router). BLOCKER if running fresh CI.
- [ ] **Git cleanup** (next thing to do — all tests pass, code is ready):
  - Untrack `frontend/` and `backend/static/`: `git rm -r --cached frontend/ backend/static/` then add both to `.gitignore`
  - Stage and commit everything: routes/preferences.py, experiments/, model changes, docker-compose fix
  - Push to dev → open PR to master
- [ ] **Run first experiments**: drop some sample photos into `backend/experiments/sample_images/` and run `--mode all`.
- [ ] **Schema migration note**: `docker-compose.yml` creds were fixed (`user`→`photography_user`). If you had data in the old volume it was wiped — this is fine for dev.

### Backlog
- [ ] Rate limiter: switch from IP-based to user-based
- [ ] Input validation: file size limit, magic bytes check, format whitelist
- [ ] Health check endpoint (`GET /health` returning DB status)
- [ ] Async tag generation (background task)
- [ ] UI redesign

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
├── backend/           FastAPI + SQLModel + PostgreSQL + Gemini + LangSmith
│   ├── main.py        Routes: /, /images/ CRUD, rate-limited upload
│   ├── app/
│   │   ├── models.py  User, Image (PostgreSQL ARRAY for tags)
│   │   ├── database.py engine + session (reads .env)
│   │   ├── security.py JWT + Argon2
│   │   ├── routes/auth.py  /auth/signup, /auth/login, /auth/me  ← UNTRACKED
│   │   └── services/ml_service.py  Gemini multi-model fallback + @traceable (LangSmith)
│   ├── experiments/
│   │   ├── config.py  prompt variants (v1/v2/v3) + model matrix
│   │   └── run_experiment.py  CLI runner for A/B prompt/model experiments
│   └── test_endpoints.py  pytest + TestClient (13 tests)
├── frontend/          Next.js 16 + React 19
├── docker-compose.yml PostgreSQL container
└── .github/workflows/ci.yml  CI: backend pytest + frontend build
```

## Branch state
- `dev` = current working branch, synced with `origin/dev`
- `master` = initial commit only (nothing merged yet)
- `feature/auth-models-security-fix` = has one extra commit not in dev (`4752dbd`)
