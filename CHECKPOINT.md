# Checkpoint — Photography ML

_Update this file at the end of every session. Most recent entry at the top._

---

## 2026-07-01

### Done this session
- **Fake test artifacts fixed** — `truncate_tables` fixture now deletes files <1KB from `static/images/` after each test. 14 leftover `fake-jpeg-bytes` files cleaned up.
- **llava-phi3 added** — pulled and documented in `.env` alongside `llava`. `GEMINI_TAG_MODEL` now reads from env (was hardcoded). `.env` has clear comments for switching between all backends.
- **Full pipeline run on 22 Krithika portraits** via `register_and_run.py` (llava + CLIP):
  - Fixed bug: `generate_embedding(str(path))` was passing path as `tags` → identical embeddings for every image. Fixed to use keyword args.
  - Fixed bug: llava sometimes outputs trailing commas in JSON arrays/objects → added `_parse_json_tolerant()` stripping trailing commas before parse. Applied to both tagging and cluster description.
  - Fixed bug: SQLAlchemy `DetachedInstanceError` when accessing image attrs after session close → extract dicts while session is open.
- **Results in `backend/storylines_output/`** — 2 clusters: 19 portraits (faces) + 3 foot/jewelry shots. `storylines_output.json` has the raw data.

### Next session — pick up here
- [ ] Open `backend/storylines_output/` in Finder and review the clustering results
- [ ] Assess quality: does the 2-cluster split make sense? Are there sub-groups within the 19 portraits?
- [ ] Consider re-running with `llava-phi3` once it finishes pulling, compare speed/quality
- [ ] The silhouette scores were low (0.28 max) — expected for a tight portrait series. May want to force k=3 or k=4 to get finer groupings within the portraits

### Backlog
- [ ] Alembic migrations
- [ ] Rate limiter: IP-based → user-based
- [ ] Input validation (file size, magic bytes)
- [ ] CLIP model warm-up on startup
- [ ] Async tag generation for batch uploads
- [ ] Feedback loop: photographer confirms/corrects tags → model learns their style

---

## 2026-06-22

### Done this session
- **Merged PR #3** (`dev` → `master`) — resolved conflicts from feature/auth-models-security-fix branch, master is now fully up to date.
- **Ollama set as default backend** — `TAGGING_BACKEND=ollama`, `OLLAMA_BASE_URL`, `OLLAMA_VISION_MODEL=llava` added to `.env`. Ollama is installed and `llava` model is pulled.
- **Rewrote all prompts** — removed curator/aesthetic framing entirely. v1/v2/v3 tagging prompts and `cluster_description` are now purely observational: describe what is literally in the frame, no aesthetic opinion or narrative imposed. Core philosophy: model learns from photographer's past data, acts as assistant only.

### Still needs to be done (immediate — start here next session)
- [ ] **Run Krithika portraits storylines with Ollama** — backend was already running on port 8000 when we stopped. Need to:
  1. Confirm backend is up: `curl http://localhost:8000/`
  2. Check how many images are in DB: `GET /images/` (may need login if auth required)
  3. If DB is empty, re-upload Krithika portraits from `backend/static/images/` (79 photos there)
  4. Run `POST /images/storylines` with `embedding_backend=clip` and `tagging_backend=ollama`
  5. Save the JSON output and run `organize_storylines.py` to get the folder tree
- [ ] Re-tag existing images with new observational prompts (old tags were generated with aesthetic-framing prompts)

### Design direction confirmed this session
- **Ollama is the primary backend, not a fallback** — photos stay local, always
- **Model philosophy**: the AI observes and describes; it learns from the photographer's past choices rather than imposing aesthetic judgment. It is the user's assistant, nothing more.
- **Future**: build a feedback/learning loop so the model adapts to each photographer's individual style over time

### Backlog
- [ ] Alembic migrations
- [ ] Rate limiter: IP-based → user-based
- [ ] Input validation (file size, magic bytes)
- [ ] CLIP model warm-up on startup
- [ ] Async tag generation for batch uploads
- [ ] Feedback loop: let photographer confirm/correct tags → fine-tune or RAG-weight future tagging

---

## 2026-06-14

### Done this session
- **Bug fix — user_id=null**: storylines endpoint now includes anonymous uploads via `(user_id == current_user.id) | (user_id == None)` so photos uploaded without auth token still appear in clustering.
- **Bug fix — Gemini rate limit**: added `time.sleep(1.5)` between `describe_cluster` calls to avoid per-minute quota errors ("Untitled group" results).
- **Bug fix — relative path**: `_representative_paths` now uses `STATIC_DIR = Path(__file__).parent / "static" / "images"` (absolute) instead of `Path("static/images")` which broke when CWD wasn't `backend/`.
- **Ollama local backend**: set `TAGGING_BACKEND=ollama` in `.env` to keep all photos on-device. Uses Ollama `/api/generate` with base64-encoded images. Controlled via `OLLAMA_BASE_URL` (default: `http://localhost:11434`) and `OLLAMA_VISION_MODEL` (default: `llava`). Both `generate_tags` and `describe_cluster` respect this env var.
- **`organize_storylines.py`**: script that reads a storylines JSON and copies photos into a browsable folder tree (`option_1__3_themes/theme_1__the_adorned_gaze/01_photo.jpg`). Supports `--link` for symlinks. Tested against Krithika portraits output.
- 20/20 tests passing. PR opened to master.

### Still needs to be done (immediate)
- [ ] `ollama pull llava` to use the local backend (or `llava-phi3` for faster)
- [ ] Re-run storylines on Krithika portraits with fixed rate limit — option 3 still has "Untitled group" clusters from the old run

### Backlog
- [ ] Alembic migrations (instead of manual DB resets)
- [ ] Rate limiter: switch from IP-based to user-based
- [ ] Input validation: file size limit, magic bytes, format whitelist
- [ ] Async tag generation (background task for batch uploads)
- [ ] CLIP model warm-up on startup

---

## 2026-06-07

### Done this session
- **3 embedding backends**: CLIP (`clip-ViT-B-32`, 512-dim, local visual), SentenceTransformers (`all-MiniLM-L6-v2`, 384-dim, local text), Gemini (`text-embedding-004`, 768-dim, API). Lazy-loaded on first call. Default = `clip`.
- **`POST /images/storylines`**: KMeans clustering on stored embeddings. Auto-detects k via silhouette score (up to `max_stories=8`). Returns groups with top-5 theme tags per cluster. Accepts `image_ids`, `n_stories`, `embedding_backend`.
- **`embedding_backend` field** added to Image model (tracks which backend was used per image; similarity/storylines filter by this).
- **New deps**: `sentence-transformers`, `scikit-learn`, `Pillow`.
- **README CLI section**: complete curl commands for all endpoints (auth, upload, batch, similar, storylines, preferences, experiments).
- **Tests**: 20/20 passing. Added storylines test.
- CI green on dev.

### Still needs to be done (immediate)
- [ ] Add `LANGCHAIN_API_KEY` + LangSmith vars to `.env` (if not done)
- [ ] Reset DB (`docker compose down -v && docker compose up -d db`) each time models.py changes — no migration system yet
- [ ] Open PR dev → master
- [ ] Real-world test: upload ~10 photos, run storylines

### Backlog
- [ ] Alembic migrations (instead of manual DB resets)
- [ ] Rate limiter: switch from IP-based to user-based
- [ ] Input validation: file size limit, magic bytes, format whitelist
- [ ] Async tag generation (background task for batch uploads)
- [ ] CLIP model warm-up on startup (avoid cold-start latency on first upload)
- [ ] Story line naming via Gemini (currently uses top-5 tags)

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
