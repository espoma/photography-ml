# Photography ML - Quick Implementation Checklist

## Phase 1: Authentication (Start Here)

### Step 1: Install Dependencies
```bash
cd /Users/espoma/Desktop/espoma-ml/photography-ml/backend
./env-photography-ml/bin/pip install python-jose passlib bcrypt python-multipart
```

### Step 2: Create `backend/app/security.py`
[See RAG_AND_AUTH_STRATEGY.md for full code]

### Step 3: Create `backend/app/routes/auth.py`
[See RAG_AND_AUTH_STRATEGY.md for full code]

### Step 4: Update `backend/app/models.py`
- Add User model
- Update Image model with user_id foreign key

### Step 5: Update `backend/main.py`
```python
from app.routes import auth

# Add after CORS middleware
app.include_router(auth.router)

# Update database lifespan to create User table
```

### Step 6: Add to `backend/.env`
```
SECRET_KEY=your-secret-key-from-openssl-rand-hex-32
```

### Step 7: Create `frontend/app/login/page.tsx`
Simple login/signup form with username, email, password fields.

### Step 8: Update `frontend/app/upload/page.tsx`
- Add user_prompt textarea
- Add logout button
- Check authentication on mount
- Include user_prompt in form submission

### Step 9: Update `frontend/app/gallery/page.tsx`
- Add user info display
- Update API calls to include Authorization header

---

## Phase 2: RAG Tag Frequency (After Auth Works)

### Step 1: Update `backend/app/services/ml_service.py`
- Rename `generate_tags()` to `generate_tags_old()`
- Add new `generate_tags_with_context()` function
- Add `get_top_user_tags()` helper

### Step 2: Update `backend/main.py`
- Modify `/images/` POST endpoint
- Add user_prompt parameter
- Extract current_user from token
- Call `generate_tags_with_context()` instead of `generate_tags()`

### Step 3: Test RAG
1. Create user account
2. Upload 10 photos with tags emphasizing "warm", "soft", "romantic"
3. Upload 11th photo
4. Check if new photo tags include more "warm"/"soft"/"romantic"

---

## Phase 3: Embeddings (Optional, for Later)

### Requirements
- [ ] PostgreSQL pgvector extension installed
- [ ] Gemini embedding-001 model access
- [ ] numpy/scikit-learn for similarity calculations

### Files to Modify
- `backend/app/models.py` — Add embedding field to Image
- `backend/app/services/ml_service.py` — Add embedding generation
- `backend/main.py` — Generate and store embeddings on upload

---

## Testing Workflow

### Test 1: Authentication
```bash
# Signup
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"password123"}'

# Response should be:
# {"access_token":"...", "refresh_token":"...", "token_type":"bearer"}

# Save the access_token

# Get current user
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer <token>"

# Should return user info
```

### Test 2: Upload with Auth
```bash
# Upload without token (should fail)
curl -X POST http://localhost:8000/images/ \
  -F "file=@photo.jpg"

# Upload with token (should work)
curl -X POST http://localhost:8000/images/ \
  -H "Authorization: Bearer <token>" \
  -F "file=@photo.jpg" \
  -F "user_prompt=warm, soft tones"
```

### Test 3: RAG Consistency
1. Create 2 user accounts: alice, bob
2. Alice uploads 5 sunset photos, tags them "warm", "romantic", "golden_hour"
3. Alice uploads 6th photo → should tag similarly
4. Bob uploads similar sunset photo → should tag differently (more generic)
5. Each user only sees their own images in gallery

---

## Time Estimates

| Phase | Tasks | Time |
|-------|-------|------|
| 1 | Auth setup + models | 2-3 hours |
| 2 | RAG tag frequency | 1-1.5 hours |
| 3 | Embeddings (optional) | 2-3 hours |
| Testing | Multi-user, RAG consistency | 1 hour |

**Total to get personalized RAG working: 4-5 hours**

---

## Debugging Tips

### Issue: "User not found" after signup
- Check if User table was created
- Run: `docker compose exec db psql -U user -d photography_db -c "\dt"`

### Issue: Token verification fails
- Check SECRET_KEY is set in .env
- Verify token isn't expired
- Check Authorization header format: `Bearer <token>`

### Issue: RAG tags aren't reflecting user style
- Check `get_top_user_tags()` is returning something
- Log the prompt being sent to Gemini
- Verify user has uploaded multiple photos with consistent tags first

### Issue: User sees other user's images
- Check Image query filters by `user_id`
- Verify token extraction is correct
- Check current_user is passed to query function

---

## Next: Which Phase Do You Want to Start?

**Recommendation:** Start with Phase 1 (Auth) because:
1. It's foundational — everything depends on it
2. It's the shortest
3. You can test each piece as you build it

Once Phase 1 works, Phase 2 (RAG) becomes straightforward.

Let me know when you're ready, and I can walk you through Phase 1 step-by-step with actual code!

