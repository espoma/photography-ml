# Checkpoint - 2026-05-29

## Session Summary
Fixed critical operational issues with the app to make it work seamlessly. Focus: stability first, ML refinement later.

## Major Fixes Completed

### 1. ✅ Gemini API Environment Loading
- **Problem**: Backend started from repo root couldn't load `GEMINI_API_KEY` from `backend/.env`
- **Fix**: Updated `backend/app/database.py` to load `.env` with absolute path:
  ```python
  env_path = Path(__file__).resolve().parent.parent / '.env'
  load_dotenv(dotenv_path=env_path)
  ```
- **Result**: API key now loads correctly regardless of CWD

### 2. ✅ ML Service Multi-Model Fallback
- **Problem**: Gemini 2.5-flash hitting 503 errors during high load spikes
- **Solution**: Added fallback chain for free-tier models:
  1. `gemini-2.5-flash` (primary)
  2. `gemini-1.5-flash` (fallback 1)
  3. `gemini-1.5-flash-8b` (fallback 2)
- **Behavior**: Tries each model in order, returns default tags `["ai_generated", "photography"]` only if all fail
- **Tests**: Added `test_generate_tags_fallback_models` to verify fallback logic

### 3. ✅ Auth Session Persistence (Critical)
- **Problem**: Gallery page was logging out users on every navigation
- **Root Cause**: Frontend was clearing auth token on ANY error (network, server errors, not just 401)
- **Fix**: Updated `frontend/app/gallery/page.tsx` to only clear token on explicit 401 (Unauthorized)
  - Network/server errors now don't clear session
  - Token only cleared if backend says it's invalid
  - Graceful fallback: show session state even if auth check fails temporarily
- **Result**: Users stay logged in across uploads → gallery → uploads workflow

### 4. ✅ Backend Unit Tests
- Fixed ML service test mocking to properly mock:
  - `mimetypes.guess_type`
  - `types.Part.from_bytes`
  - `genai.Client`
- Both tests now pass: `test_generate_tags_with_mock` and `test_generate_tags_fallback_models`

### 5. ✅ CI/CD Integration Test
- `test_endpoints.py` pytest integration test passes
- Covers full image lifecycle: POST → GET list → GET detail → PATCH → DELETE → 404 verify

## Operational Status

| Component | Status | Details |
|-----------|--------|---------|
| Backend | ✅ Running | `127.0.0.1:8000`, all routes responding |
| Frontend | ✅ Running | `localhost:3000`, auth state persists |
| Database | ✅ Running | PostgreSQL via Docker Compose |
| Unit Tests | ✅ Passing | 2/2 ML service tests, 1/1 endpoint test |
| Auth Flow | ✅ Working | Login/Signup/Session → Upload → Gallery without logout |
| Tag Generation | ✅ Working | Tries multiple models, graceful fallback to defaults |
| API Quota | ⚠️ Limited | 1,500 requests/day free tier (may hit 503s during spikes) |

## Git Status

**Branch**: `feature/auth-models-security-fix`

**Changed Files**:
- `backend/app/database.py` - Fixed .env loading
- `backend/app/services/ml_service.py` - Added multi-model fallback
- `backend/test_ml_service.py` - Fixed/added fallback tests
- `frontend/app/gallery/page.tsx` - Fixed auth session clearing logic
- `GEMINI_QUOTA_AND_LIMITS.md` - New doc on quota and fallback models
- `CHECKPOINT_2026_05_29.md` - This file

**Uncommitted**: Several changes pending commit

## Known Limitations

1. **Gemini API Rate Limits**: Free tier (1,500/day) may cause 503 errors on high traffic
   - Mitigation: Automatic fallback to other models
   - Long-term: Upgrade to paid tier or use alternative models

2. **Synchronous Tag Generation**: Upload blocks until tags generated
   - Mitigation: Works for now, acceptable for current scale
   - Future: Move to async/background jobs

3. **Auth Token Verification**: Gallery calls `/auth/me` on mount
   - Mitigation: Doesn't clear token on network errors
   - Future: Use refresh tokens for better resilience

## Immediate Next Steps (Tomorrow)

1. **Commit all changes** with meaningful messages:
   - Env loading fix
   - ML fallback models
   - Auth session persistence
   - Test updates

2. **Open PR** to `dev` branch with:
   - Clear description of fixes
   - Link to this checkpoint
   - Testing notes

3. **Consider**:
   - Should we add a background task for tag generation?
   - Should we implement refresh token rotation?
   - Should we cache Gemini responses?

## Testing Checklist (Manual)

- [x] Backend starts and loads Gemini API key
- [x] Frontend loads and starts dev server
- [x] Unit tests pass (ML service, endpoints)
- [x] Can sign up / log in
- [x] Can upload image with auth token
- [x] Tags generate (or fallback gracefully)
- [x] Can navigate to gallery without logging out
- [x] Session persists across page navigations
- [x] Can manually log out when desired

## Resources

- **Gemini Quota**: https://aistudio.google.com/ (API keys section)
- **Free Tier Limits**: 1,500 requests/day, 15 RPM
- **Fallback Models**: Configured in `backend/app/services/ml_service.py:GEMINI_MODELS`
- **Local Testing**: `http://localhost:3000` (frontend), `http://127.0.0.1:8000` (backend)

## Session Time Spent

Focus: Debugging, fixing operational issues, writing tests, updating docs

Key learnings:
- Environment loading paths matter when apps start from different CWDs
- Aggressive error handling on auth can be worse than no validation
- Multi-model fallback gracefully handles API outages
- Testing async flows (image + tag generation) requires proper mocking
