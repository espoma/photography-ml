# 📸 Photography ML

An intelligent photo tagging and gallery application powered by Google's Gemini API. Upload photos, get automatic AI-generated tags, and browse your tagged gallery.

## 🎯 Features

- **User Authentication**: Secure signup/login with JWT tokens and Argon2 password hashing
- **Photo Upload**: Upload photos with automatic AI tag generation via Gemini API
- **Smart Tagging**: Generates descriptive tags using Google Gemini 2.5 Flash with multi-model fallback
- **Gallery View**: Browse, view, and manage uploaded photos with tags
- **Error Resilience**: Graceful fallback when API is unavailable
- **Rate Limiting**: Protects API from abuse with slowapi
- **Responsive Design**: Next.js frontend with modern UI

## 🚀 Quick Start

### Prerequisites

- **macOS/Linux** with Homebrew or equivalent
- **Docker Desktop** (running, for PostgreSQL)
- **Python 3.14+** (virtual environment at `backend/env-photography-ml/`)
- **Node.js 18+** with npm
- **Gemini API Key** from [Google AI Studio](https://aistudio.google.com/app/apikey)

### Step 1: Clone & Navigate

```bash
cd /Users/espoma/Desktop/espoma-ml/photography-ml
```

### Step 2: Set Up Environment Variables

Create `backend/.env`:

```bash
cat > backend/.env << 'EOF'
DATABASE_URL=postgresql+psycopg://photography_user:photography_password@localhost:5432/photography_db
GEMINI_API_KEY=your-actual-gemini-api-key-here
SECRET_KEY=your-secret-key-for-jwt

# LangSmith experiment tracking (optional — tracing is disabled if not set)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your-langsmith-api-key-here
LANGSMITH_PROJECT=photography-ml
EOF
```

Replace `your-actual-gemini-api-key-here` with your actual key from [Google AI Studio](https://aistudio.google.com/app/apikey).

### Step 3: Start PostgreSQL Database

```bash
docker compose up -d db
```

Verify it's running:

```bash
docker ps --filter "name=photography_db"
```

### Step 4: Start Backend (Terminal 1)

```bash
cd backend
./env-photography-ml/bin/python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

**Backend API**: http://127.0.0.1:8000  
**API Docs**: http://127.0.0.1:8000/docs

### Step 5: Start Frontend (Terminal 2)

```bash
cd frontend
npm run dev
```

You should see:
```
▲ Next.js 16.1.4
- Local:         http://localhost:3000
✓ Ready in 1336ms
```

### Step 6: Open the App

Open your browser and navigate to:

```
http://localhost:3000
```

### Step 7: Create Account & Test

1. **Sign up**: Click "Sign Up", create an account
2. **Login**: Use your credentials
3. **Upload**: Go to "Upload" page, select a photo
4. **View Gallery**: Go to "Gallery" to see tagged photos

### Step 8: Stop Everything

```bash
# Terminal 1: Press Ctrl+C to stop backend
# Terminal 2: Press Ctrl+C to stop frontend
docker compose down  # Stop PostgreSQL
```

---

## 📁 Project Structure

```
photography-ml/
├── backend/                    # FastAPI application
│   ├── main.py                # App entry point, routes
│   ├── requirements.txt        # Python dependencies
│   ├── .env                    # Environment variables (gitignored)
│   └── app/
│       ├── database.py         # SQLModel setup, session management
│       ├── models.py           # Database models (User, Image, etc.)
│       ├── security.py         # JWT, Argon2 password hashing
│       ├── services/
│       │   └── ml_service.py   # Gemini API integration, tag generation
│       └── routes/
│           └── auth.py         # Authentication endpoints
├── frontend/                   # Next.js application
│   ├── app/
│   │   ├── layout.tsx          # Root layout
│   │   ├── page.tsx            # Home page
│   │   ├── login/page.tsx       # Login page
│   │   ├── signup/page.tsx      # Signup page
│   │   ├── upload/page.tsx      # Upload page
│   │   └── gallery/page.tsx     # Gallery page
│   ├── package.json            # Node dependencies
│   └── next.config.ts          # Next.js config
├── docker-compose.yml          # PostgreSQL container setup
└── .github/workflows/
    └── ci.yml                  # GitHub Actions CI pipeline
```

---

## 🔑 API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/signup` | Create new user account |
| POST | `/auth/login` | Login and get JWT token |
| GET | `/auth/me` | Get current user info |

### Images

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/images/upload` | Upload photo with auto-tagging |
| GET | `/images` | List user's uploaded images |
| GET | `/images/{image_id}` | Get specific image details |
| DELETE | `/images/{image_id}` | Delete an image |

---

## 🤖 AI Tagging System

### How It Works

1. User uploads a photo
2. Backend processes image and sends to Gemini API
3. Gemini generates tags (e.g., "outdoor", "landscape", "sunset")
4. Tags are saved to database

### Multi-Model Fallback

If the primary Gemini 2.5 Flash model is unavailable:

```
1. Try: gemini-2.5-flash
2. Fallback: gemini-1.5-flash
3. Fallback: gemini-1.5-flash-8b
4. Last resort: ["ai_generated", "photography"]
```

This ensures the app continues working even during API outages.

---

## 🧪 Testing

### Run Backend Tests

```bash
cd backend
./env-photography-ml/bin/python -m pytest test_endpoints.py -v
./env-photography-ml/bin/pytest test_ml_service.py -v
```

### Run CI Tests Locally

Tests automatically run on:
- Push to `dev` branch
- Pull requests to `dev`
- Feature branch pushes

View results at: https://github.com/espoma/photography-ml/actions

---

## 🌳 Git Workflow

### Branch Strategy

- **`master`**: Production-ready releases only
- **`dev`**: Integration branch, all PR tests run here
- **`feature/*`**: Feature branches for development

### Committing Changes

```bash
git checkout -b feature/your-feature
# Make changes...
git add .
git commit -m "feat: describe your feature"
git push origin feature/your-feature
# Create PR to dev
```

---

## 📝 Environment Variables

### `backend/.env` (Local Only)

```
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/photography_db
GEMINI_API_KEY=your-api-key-here
SECRET_KEY=your-secret-jwt-key

# LangSmith (optional)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your-langsmith-key
LANGSMITH_PROJECT=photography-ml
```

**Important**: Never commit `.env`—it's in `.gitignore`

---

## 🧪 Experiments (Prompt & Model Comparison)

Run controlled experiments to compare prompt variants and Gemini models. All runs are traced in LangSmith.

### Prompt variants

| Version | Strategy |
|---------|----------|
| `v1` | Generic photography keywords (baseline) |
| `v2` | Structured by subject/lighting/mood/palette |
| `v3` | Exactly 8 tags covering predefined categories |

### Run experiments

```bash
cd backend

# Compare prompts v1/v2/v3 on one image
python -m experiments.run_experiment --mode prompts --image path/to/photo.jpg

# Compare gemini-2.5-flash vs gemini-1.5-flash vs gemini-1.5-flash-8b
python -m experiments.run_experiment --mode models --image path/to/photo.jpg

# Run everything and save results
python -m experiments.run_experiment --mode all --image path/to/photo.jpg --output results.json
```

### Experiments you can run

1. **Prompt comparison** — does structured prompting (`v3`) produce better tags than generic (`v1`)?
2. **Model comparison** — quality vs cost tradeoff across Gemini model tiers
3. **Prompt × model grid** — which combination gives best quality?
4. **Tag count analysis** — do different prompts produce consistently more/fewer tags?
5. **Edge cases** — low-light photos, abstract art, portraits — do prompts generalize?

Each run appears in your LangSmith dashboard at [smith.langchain.com](https://smith.langchain.com) with: inputs, output tags, latency, token counts, and model used.

---

## 🚨 Common Issues

### "Connection refused" on port 8000
Backend is not running. Make sure Docker database is up:
```bash
docker compose up -d db
cd backend
./env-photography-ml/bin/python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### "GEMINI_API_KEY not found"
Make sure `backend/.env` exists with your API key. Backend loads from:
```
/Users/espoma/Desktop/espoma-ml/photography-ml/backend/.env
```

### "ModuleNotFoundError: No module named 'main'"
Run backend from the correct directory:
```bash
cd /Users/espoma/Desktop/espoma-ml/photography-ml/backend
./env-photography-ml/bin/python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend can't connect to backend
Make sure backend is running on `127.0.0.1:8000` and frontend is on `localhost:3000`

---

## 📚 Technology Stack

| Component | Technology |
|-----------|-----------|
| Backend API | FastAPI |
| Database ORM | SQLModel |
| Database | PostgreSQL |
| Authentication | JWT + Argon2 |
| Rate Limiting | SlowAPI |
| AI API | Google Gemini |
| Frontend Framework | Next.js 16+ |
| UI Library | React 19 |
| Styling | CSS Modules + Tailwind |
| Container | Docker + Docker Compose |
| CI/CD | GitHub Actions |

---

## 🗺️ Planned Features

- [ ] **UI Redesign**: Modern dashboard with improved UX
- [ ] **Async Tag Generation**: Background job processing for faster uploads
- [ ] **Image Filtering**: Search and filter by tags
- [ ] **Batch Upload**: Upload multiple photos at once
- [ ] **Tag Management**: Edit/delete tags manually
- [ ] **Social Features**: Share galleries with others
- [ ] **Advanced ML**: Train custom models for specific photography styles
- [ ] **Caching**: Redis for performance optimization
- [ ] **Deployment**: Fly.io or similar for production

---

## 📞 Support

For issues, check:
1. Backend logs: `docker compose logs db`
2. Frontend console: Browser DevTools (F12)
3. GitHub Issues: Report bugs with reproduction steps

---

## 📄 License

Private repository for educational purposes.

---

**Happy photo tagging! 📸✨**
