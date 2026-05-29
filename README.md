# Photography ML

Photography-ML is a small full-stack project demonstrating an image-upload and enhancement pipeline with a machine learning service backend. The goal is to provide an opinionated example of how a FastAPI backend (with SQLModel + PostgreSQL), a Next.js frontend, and ML services can be integrated, tested, and deployed.

## Objective
- Provide a simple web UI to upload photos and run enhancement or analysis ML tasks.
- Offer a backend service exposing REST endpoints for auth, image upload, and ML processing.
- Keep the project lightweight and reproducible with Docker for the database and a local Python venv for development.

## Quickstart (local)
Prereqs: macOS/Linux with Git, Python 3.14 (venv used here), Docker (for Postgres), and Node.js (for Next.js frontend).

1. Backend

```bash
cd backend
./env-photography-ml/bin/pip install -r requirements.txt
docker compose up -d db
./env-photography-ml/bin/python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

2. Frontend

```bash
cd frontend
npm install
npm run dev
# open http://localhost:3000
```

3. Notes
- Backend virtual environment is checked into `backend/env-photography-ml` for convenience in this repository; prefer creating a fresh venv in new clones.
- Environment variables for DB and JWT (see `backend/app/security.py` and `backend/main.py`) should be set for production usage.

## Current Status
- Auth and signup flow fixed; password hashing uses Argon2.
- SQLModel relationship issues simplified to avoid runtime errors with recent SQLModel/SQLAlchemy versions.
- Feature branch `feature/auth-models-security-fix` was merged into `dev` (see repo history).

## Planned / Future Features
- CI: Add GitHub Actions to run backend tests and lint on PRs.
- CD: Deploy a staging environment (container registry + deploy target) and add a deployment workflow.
- Add E2E tests for upload and ML processing flows.
- Improve model registry and ML model versioning for reproducible results.
- Image storage backend abstraction (S3-compatible or GCS) and background processing workers.

## Branching and Workflow Notes
- Short-lived feature branches -> open PR against `dev` -> CI runs -> merge into `dev` -> scheduled or gated release from `dev` to `master` (or `main`).
- We use `dev` as the integration branch to collect features and validate them before releasing to `master`.

## How to Help
- Run the test suite in `backend` and report failures.
- Review the open PRs and suggest smaller, focused commits for reviewability.

---
_Generated and committed by the project maintainer (helper assistant)._ 
