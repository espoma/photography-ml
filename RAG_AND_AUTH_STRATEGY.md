# Photography ML - RAG & Fine-Tuning Strategy + Authentication

## Overview

Your app will remember each user's photographic style and preferences by:
1. **Storing their tagging history** (what tags they typically use)
2. **Using RAG (Retrieval-Augmented Generation)** to inject relevant past context into Gemini
3. **Allowing user prompts** for batch-specific instructions
4. **Authenticating users** so each sees only their own images and receives personalized tagging

This creates a **personalized AI tagger** that learns your style over time.

---

## Part 1: Authentication Strategy

### Why Authentication?
- Each user's images stay private
- Each user gets personalized tagging based on their history
- You can deploy to production safely with multiple users

### Architecture: JWT-Based Authentication

**Tech Stack:**
- `python-jose` + `passlib` for JWT tokens and password hashing
- User table in PostgreSQL
- Refresh tokens (separate from access tokens)
- Token expiry: 1 hour access, 7 days refresh

**Database Schema:**

```python
# app/models.py - Add User model

class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)
    
    # Relationship to images
    images: List["Image"] = Relationship(back_populates="owner")

# Modify Image model to include user ownership

class Image(ImageBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")  # NEW
    owner: User = Relationship(back_populates="images")  # NEW
    
    tags: List[str] = Field(default=[], sa_column=Column(ARRAY(String)))
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Request/Response schemas

class UserCreate(SQLModel):
    username: str
    email: str
    password: str

class UserPublic(SQLModel):
    id: int
    username: str
    email: str
    created_at: datetime

class Token(SQLModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenData(SQLModel):
    username: str | None = None
```

**Authentication Flow:**

```
1. User signs up: POST /auth/signup
   → Create User, hash password, return tokens

2. User logs in: POST /auth/login
   → Verify credentials, return access + refresh tokens

3. User makes request: GET /images/ with Authorization: Bearer <token>
   → Verify token, extract username, return their images only

4. Token expires: POST /auth/refresh
   → Use refresh token, return new access token

5. User logs out: POST /auth/logout (optional)
   → Invalidate refresh token (store in blacklist)
```

### Implementation Steps (Order matters)

**Step 1: Add dependencies**
```bash
pip install python-jose passlib bcrypt python-multipart
```

**Step 2: Create security utilities**
File: `backend/app/security.py`
```python
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import os

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return username
    except JWTError:
        return None
```

**Step 3: Create auth endpoints**
File: `backend/app/routes/auth.py`
```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.models import User, UserCreate, Token
from app.security import hash_password, verify_password, create_access_token, create_refresh_token, verify_token
from app.database import get_session
from datetime import timedelta

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/signup", response_model=Token)
def signup(user: UserCreate, session: Session = Depends(get_session)):
    # Check if user already exists
    existing = session.exec(select(User).where(User.username == user.username)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Create new user
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hash_password(user.password)
    )
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    
    # Return tokens
    access_token = create_access_token(data={"sub": user.username})
    refresh_token = create_refresh_token(data={"sub": user.username})
    
    return Token(access_token=access_token, refresh_token=refresh_token)

@router.post("/login", response_model=Token)
def login(username: str, password: str, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == username)).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": username})
    refresh_token = create_refresh_token(data={"sub": username})
    
    return Token(access_token=access_token, refresh_token=refresh_token)

@router.get("/me", response_model=UserPublic)
def get_current_user(token: str = Depends(get_token), session: Session = Depends(get_session)):
    username = verify_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = session.exec(select(User).where(User.username == username)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user

# Dependency to extract token from header
def get_token(request) -> str:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    return auth_header.split(" ")[1]
```

---

## Part 2: RAG Strategy for Gemini Flash

### The Problem
Without RAG: Gemini tags every photo independently, no awareness of user's style.

Example:
- User uploads 100 sunset photos over time
- Some tagged "warm", some "golden_hour", some "romantic"
- New sunset photo gets tagged randomly from all possibilities
- No consistency with user's own tagging history

### The Solution: RAG
**Retrieve** user's past tags → **Augment** the Gemini prompt → **Generate** tags informed by history

### Architecture

**Option 1: Vector Database (Recommended for Scale)**
- Store embeddings of user's tags + images
- Use semantic search to find similar past photos
- Fast retrieval, scales to 10k+ photos

**Option 2: In-Database (Simpler, Works for Now)**
- Store embeddings in PostgreSQL
- Use pgvector extension for similarity search
- Good enough for <5k photos

**Option 3: Simple Tag Frequency (Easiest to Start)**
- Just look at user's most-used tags
- Inject into prompt as "user frequently uses these tags"
- Works immediately, no extra infrastructure

---

### Recommended: Start with Option 3 (Tag Frequency), evolve to Option 1

**Phase 1 (Now): Tag Frequency**
```python
# For each user, track their most-used tags
@app.post("/images/", response_model=ImagePublic)
async def create_image(
    file: UploadFile,
    description: str = Form(None),
    user_prompt: str = Form(None),  # NEW: user can add instructions
    tags: List[str] = Form([]),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    # ... file upload logic ...
    
    # Get user's top 10 most-used tags
    top_user_tags = get_top_user_tags(current_user.id, session, limit=10)
    
    # Get user's top 5 most-used style words
    top_styles = extract_style_words(top_user_tags)  # e.g., ["warm", "romantic", "sharp"]
    
    # Enhance Gemini prompt with user context
    ai_tags = generate_tags_with_context(
        image_path=str(file_location),
        user_tags_history=top_user_tags,
        user_style_words=top_styles,
        user_custom_prompt=user_prompt
    )
    
    # Save image
    db_image = Image(
        filename=unique_filename,
        file_path=f"/static/images/{unique_filename}",
        description=description,
        tags=combined_tags,
        user_id=current_user.id  # NEW: associate with user
    )
    session.add(db_image)
    session.commit()
    session.refresh(db_image)
    
    return db_image

def get_top_user_tags(user_id: int, session: Session, limit: int = 10) -> List[str]:
    """Get user's most frequently used tags"""
    images = session.exec(
        select(Image).where(Image.user_id == user_id)
    ).all()
    
    from collections import Counter
    all_tags = []
    for img in images:
        all_tags.extend(img.tags)
    
    tag_counts = Counter(all_tags)
    return [tag for tag, count in tag_counts.most_common(limit)]

def extract_style_words(tags: List[str]) -> List[str]:
    """Extract style/mood words from tags"""
    style_keywords = ["warm", "cool", "sharp", "soft", "romantic", "dramatic", "muted", "vibrant"]
    return [tag for tag in tags if any(style in tag.lower() for style in style_keywords)]
```

**Phase 2 (Next): Embeddings with PostgreSQL**
```python
# Add pgvector to PostgreSQL
# Store embeddings alongside each image
# Use semantic search

class Image(ImageBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    embedding: List[float] = Field(default=[])  # NEW: store image embeddings
    ...

def find_similar_user_photos(
    current_embedding: List[float],
    user_id: int,
    session: Session,
    limit: int = 5
) -> List[Image]:
    """Find top-N most similar past photos by embedding similarity"""
    user_images = session.exec(
        select(Image).where(Image.user_id == user_id)
    ).all()
    
    from sklearn.metrics.pairwise import cosine_similarity
    similarities = []
    for img in user_images:
        if img.embedding:
            sim = cosine_similarity(
                [current_embedding],
                [img.embedding]
            )[0][0]
            similarities.append((img, sim))
    
    # Sort by similarity, return top N
    top_similar = sorted(similarities, key=lambda x: x[1], reverse=True)[:limit]
    return [img for img, sim in top_similar]
```

**Phase 3 (Future): Vector Database (Pinecone/Weaviate)**
```python
# Use specialized vector DB for ultra-fast retrieval
# Store embeddings there, reference back to PostgreSQL
# No changes needed to logic, just swap backend
```

### Enhanced Gemini Prompt with User Context

**Old prompt** (current):
```python
prompt = (
    "You are an expert photography assistant. Analyze this image and generate 5-10 "
    "highly descriptive keywords. Focus on lighting, mood, subject matter, and composition. "
    "Only use lowercase."
)
```

**New prompt with RAG** (with user context):
```python
def generate_tags_with_context(
    image_path: str,
    user_tags_history: List[str],
    user_style_words: List[str],
    user_custom_prompt: str | None = None
) -> List[str]:
    """
    Generate tags informed by user's tagging history and custom instructions
    """
    
    # Build context from user's history
    context = f"""
    This user frequently tags photos with: {', '.join(user_tags_history)}.
    Their typical photography style includes: {', '.join(user_style_words)}.
    """
    
    # Add custom user instructions if provided
    custom_instruction = ""
    if user_custom_prompt:
        custom_instruction = f"\nFor this batch: {user_custom_prompt}"
    
    prompt = f"""
    You are an expert photography assistant trained on this specific photographer's style.
    
    {context}
    {custom_instruction}
    
    Analyze this image and generate 5-10 keywords that:
    1. Match this photographer's typical style and vocabulary
    2. Are consistent with their tagging history
    3. Follow any special instructions they provided
    4. Use lowercase, prioritize their recurring tags over generic ones
    
    Return ONLY a JSON array of strings, no explanation.
    """
    
    client = genai.Client()
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    
    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type:
        mime_type = "image/jpeg"
    
    image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[image_part, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema={"type": "array", "items": {"type": "string"}}
        )
    )
    
    tags = json.loads(response.text)
    return tags
```

---

## Part 3: Frontend Changes for User Prompts

### Updated Upload Form

**File: `frontend/app/upload/page.tsx`**

Add two new fields:
1. **User Prompt** (optional textarea) — "What style do you want? E.g., 'focus on shadows', 'editorial look'"
2. **Login button** — Show current user, allow logout

```typescript
// New state
const [userPrompt, setUserPrompt] = useState('');
const [isAuthenticated, setIsAuthenticated] = useState(false);
const [currentUser, setCurrentUser] = useState<string | null>(null);

// Fetch current user on mount
useEffect(() => {
    const checkAuth = async () => {
        const token = localStorage.getItem('access_token');
        if (token) {
            const response = await fetch('http://localhost:8000/auth/me', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (response.ok) {
                const user = await response.json();
                setCurrentUser(user.username);
                setIsAuthenticated(true);
            }
        }
    };
    checkAuth();
}, []);

// In form submission
const handleSubmit = async (e: React.FormEvent) => {
    // ... existing validation ...
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('description', description);
    formData.append('user_prompt', userPrompt);  // NEW
    
    // ... rest of upload logic ...
};

// In JSX - add fields
<div>
    <label className="block text-sm font-medium text-purple-300 mb-2">
        Photography Style Notes (Optional)
    </label>
    <textarea
        value={userPrompt}
        onChange={(e) => setUserPrompt(e.target.value)}
        rows={3}
        className="w-full px-4 py-2 bg-purple-900/20 border border-purple-500/30 rounded-lg"
        placeholder="e.g., 'focus on shadows and contrast', 'editorial style', 'warm tones'"
    />
    <p className="text-xs text-gray-400 mt-1">
        Guide the AI tagging for this batch. Useful for: editorial projects, specific moods, technical preferences.
    </p>
</div>

// Add auth UI
<div className="flex justify-between items-center mb-8">
    <h1 className="text-4xl font-bold">Upload Image</h1>
    {isAuthenticated && (
        <div className="text-gray-300">
            Logged in as: <span className="text-cyan-400 font-semibold">{currentUser}</span>
            <button onClick={logout} className="ml-4 text-red-400">Logout</button>
        </div>
    )}
</div>
```

---

## Implementation Roadmap

### Phase 1: Authentication (2-3 hours)
- [ ] Add User model and auth endpoints
- [ ] Update Image model with user_id
- [ ] Update all image queries to filter by user_id
- [ ] Add login/signup pages to frontend
- [ ] Store JWT tokens in localStorage

### Phase 2: RAG Tag Frequency (1 hour)
- [ ] Add `get_top_user_tags()` function
- [ ] Update `generate_tags()` to accept user context
- [ ] Update upload form to include user_prompt field
- [ ] Test with same user uploading multiple photos

### Phase 3: Embeddings & Semantic Search (2 hours)
- [ ] Install `pgvector` extension in PostgreSQL
- [ ] Add embedding field to Image model
- [ ] Generate embeddings with Gemini `embedding-001` model
- [ ] Implement `find_similar_user_photos()` function
- [ ] Update prompt to include similar photo context

### Phase 4: Polish & Testing (1 hour)
- [ ] Add error handling for auth failures
- [ ] Test multi-user isolation
- [ ] Test RAG consistency
- [ ] Add feedback loop (users correct tags)

---

## Key Files to Create/Modify

**New files:**
- `backend/app/security.py` — JWT and password utilities
- `backend/app/routes/auth.py` — Auth endpoints
- `frontend/app/login/page.tsx` — Login/signup UI
- `frontend/app/protected.tsx` — Protected routes wrapper (optional)

**Modified files:**
- `backend/app/models.py` — Add User model, update Image
- `backend/main.py` — Include auth router, update middleware
- `backend/app/services/ml_service.py` — Update generate_tags()
- `frontend/app/upload/page.tsx` — Add user_prompt field and auth UI
- `frontend/app/gallery/page.tsx` — Add logout, user info

**Environment variables to add:**
- `SECRET_KEY` — For JWT signing (generate with `openssl rand -hex 32`)

---

## Security Notes

1. **HTTPS in production** — JWT tokens vulnerable over HTTP
2. **CORS**: Only allow your frontend domain
3. **Rate limiting**: Add per-user limits (max 100 uploads/day)
4. **Token rotation**: Implement refresh token rotation
5. **Password requirements**: Enforce strong passwords
6. **Input sanitization**: Clean user_prompt before injecting into prompt

