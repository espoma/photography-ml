# Photography ML - Features & Improvements Roadmap

## ✅ Currently Implemented

### Core Features
- Image upload with drag-and-drop support
- Automatic tag generation using Gemini Flash
- Image gallery with filtering
- Image metadata (description, tags, created_at)
- PostgreSQL database for persistence
- Frontend and backend separation
- Static image serving

---

## 🎯 Priority 1: Production Essentials (Immediate)

These six features are critical for a production app:

### 1. Rate Limiting
- **What**: Prevent abuse by limiting requests per IP/user
- **Implementation**: Use `slowapi` library
- **Example**: Max 10 uploads/hour per IP
- **Why**: Protects backend from spam, controls Gemini API costs

**Status:** ✅ Implemented (May 27, 2026) — currently IP-based (global) limit: `10 uploads/hour`.

**Note:** Because authentication is not yet implemented, the limiter is keyed by client IP. After adding user auth, switch limiter to use user-id so limits apply per account rather than per IP.

### 2. Image Safety Check
- **What**: Reject inappropriate/NSFW images before tagging
- **Implementation**: Google Vision API `SafeSearchAnnotation` or Gemini's built-in filtering
- **Example**: Flag images with ADULT/RACY confidence > 0.5
- **Why**: Prevents inappropriate content in gallery, saves Gemini API calls

### 3. Input Validation
- **What**: Validate file size, format, metadata
- **Implementation**: Check magic bytes, reject >50MB files, whitelist formats (JPEG, PNG, WebP)
- **Example**: `if file.size > 50MB or file.content_type not in ['image/jpeg', 'image/png']`
- **Why**: Security (directory traversal), storage efficiency, prevents crashes

### 4. Structured Logging
- **What**: JSON logs with request ID, timing, errors
- **Implementation**: `python-json-logger` + log context
- **Example**: `{"timestamp": "2026-05-15T10:30:00Z", "request_id": "abc123", "event": "image_upload", "duration_ms": 2340}`
- **Why**: Easy debugging, analytics, production monitoring

### 5. Health Check Endpoint
- **What**: Dedicated `/health` endpoint for load balancers
- **Implementation**: Check database connectivity, return 200/503
- **Example**: `GET /health -> {"status": "healthy", "db": "connected"}`
- **Why**: Kubernetes/monitoring tools need this, zero-downtime deployments

### 6. Async Tag Generation
- **What**: Generate tags in background, don't block upload
- **Implementation**: Use Celery + Redis or simple background tasks
- **Example**: Upload returns immediately with `tags_processing=true`, gets tags later
- **Why**: 2-3s Gemini latency won't block user, better UX

---

## 🚀 Priority 2: Advanced Features (Next Phase)

### Performance & Caching
- **Response caching**: Cache `/images/` list for 5 min (Redis)
- **Image compression**: Resize uploads to max 2000x2000px, optimize for web
- **CDN integration**: Serve images from CloudFront/Cloudflare
- **Database connection pooling**: Optimize PostgreSQL connections

### Content Intelligence
- **Tag quality scoring**: Track Gemini tag confidence, filter low-confidence ones
- **Duplicate detection**: Hash images, reject if already uploaded
- **Tag normalization**: Consolidate similar tags (e.g., "sunset" vs "sunsets")
- **Tag autocomplete**: Suggest tags based on history

### User Experience
- **Search/filtering**: Find images by tags, date range
- **Batch operations**: Upload multiple images at once
- **Tag editing**: Let users correct AI tags (feedback loop)
- **Export**: Download gallery metadata as CSV/JSON

---

## 🔒 Priority 3: Security & Compliance

### Authentication & Authorization
- **User accounts**: JWT tokens, login/signup
- **User isolation**: Users can only see their own images
- **API key management**: Rotate Gemini keys, audit access

### Data Protection
- **Encryption**: Encrypt GEMINI_API_KEY in database
- **HTTPS enforcement**: Only allow TLS connections
- **CORS hardening**: Restrict to your frontend domain only
- **Rate limiting by user**: Different limits for authenticated users

### Compliance
- **Data retention policy**: Delete images after 90 days (configurable)
- **GDPR/Privacy**: Add data export/deletion endpoints
- **Audit logging**: Log all uploads, deletes, tag changes

---

## 📊 Priority 4: ML & Analytics

### Tag Analysis
- **A/B testing prompts**: Test different Gemini system prompts, measure tag quality
- **Tag distribution**: Show stats (most common tags, upload trends)
- **Prompt engineering**: Experiment with different Gemini prompt versions
- **LangSmith integration**: Track prompt performance over time

### Model Insights
- **Tag consistency**: Measure if Gemini gives same tags to similar images
- **Latency tracking**: Monitor Gemini response times, alert on slowdowns
- **Cost tracking**: Log API costs per user, per month
- **Error patterns**: Identify which image types fail tagging

---

## 🛠️ Priority 5: DevOps & Deployment

### Containerization
- **Dockerfile for backend**: Multi-stage build (minimal final image)
- **Dockerfile for frontend**: Build Next.js, serve static files
- **Docker Compose improvements**: Add Redis, Celery workers

### CI/CD
- **GitHub Actions**: Test on push, build images, deploy on merge
- **Automated testing**: Unit tests for API endpoints, integration tests
- **Linting/formatting**: Black, isort, ESLint
- **Security scanning**: Bandit for Python, npm audit for JS

### Monitoring & Alerts
- **Prometheus metrics**: Track uploads, errors, latency
- **Grafana dashboards**: Visualize metrics
- **Sentry integration**: Alert on exceptions
- **Log aggregation**: ELK Stack or Cloud Logging

---

## 🌍 Priority 6: Deployment Options

### Local Deployment
- ✅ Docker Compose (current setup)
- Docker Compose with multiple workers (Celery)

### Cloud Deployment
- **Fly.io** (easiest, $3/mo free tier)
- **Railway.app** ($5/mo free tier)
- **Render** (limited free tier, sleeps on inactivity)
- **AWS (EKS + RDS)** (most expensive but scalable)
- **Google Cloud (GKE + Cloud SQL)** (good balance)
- **Heroku** (simplest, but expensive)

---

## 📋 Implementation Checklist

- [ ] Rate limiting (`slowapi`)
 - [x] Rate limiting (`slowapi`) — implemented (IP-based, 10/hour)
- [ ] Image safety check (Google Vision API or Gemini)
- [ ] Input validation (file size, format, magic bytes)
- [ ] Structured logging (JSON + request IDs)
- [ ] Health check endpoint
- [ ] Async tag generation (Celery + Redis)
- [ ] Image compression
- [ ] Search/filtering by tags
- [ ] User authentication (JWT)
- [ ] Database migrations (Alembic)
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Dockerfiles for backend + frontend
- [ ] Prometheus metrics
- [ ] Sentry error tracking
- [ ] Deployment to Fly.io

---

## 🎓 Learning Resources

### For Production Readiness
- FastAPI best practices: https://fastapi.tiangolo.com/
- Python logging: https://docs.python.org/3/howto/logging.html
- Docker best practices: https://docs.docker.com/develop/dev-best-practices/
- Kubernetes basics: https://kubernetes.io/docs/concepts/overview/

### For ML/AI
- LangChain docs: https://python.langchain.com/
- Gemini API: https://ai.google.dev/
- Prompt engineering: https://platform.openai.com/docs/guides/prompt-engineering

### For DevOps
- GitHub Actions: https://docs.github.com/en/actions
- Prometheus: https://prometheus.io/docs/
- Sentry: https://docs.sentry.io/

