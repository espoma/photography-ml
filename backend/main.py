from contextlib import asynccontextmanager
from typing import Annotated, List, Optional
from fastapi import FastAPI, Depends, HTTPException, Query, File, UploadFile, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select
from app.database import create_db_and_tables, get_session
from app.models import Image, ImageCreate, ImagePublic, ImageUpdate
from app.services.ml_service import generate_tags, generate_embedding
from app.routes import auth as auth_routes
from app.routes import preferences as pref_routes
from app.security import get_current_user
from app.models import User
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi.responses import JSONResponse
from starlette.status import HTTP_429_TOO_MANY_REQUESTS
import shutil
import uuid
import numpy as np
from pathlib import Path


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up... Creating database tables...")
    create_db_and_tables()
    Path("static/images").mkdir(parents=True, exist_ok=True)
    yield
    print("Shutting down...")


app = FastAPI(
    title="Photography ML",
    description="API for Smart Photography Portfolio",
    version="0.2.0",
    lifespan=lifespan,
)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


async def _rate_limit_exceeded_handler(request, exc):
    return JSONResponse(
        status_code=HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Rate limit exceeded. Try again later."},
    )


app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(auth_routes.router)
app.include_router(pref_routes.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _save_upload(file: UploadFile) -> tuple[str, str]:
    """Save uploaded file; return (unique_filename, file_path_str)."""
    ext = Path(file.filename).suffix
    name = f"{uuid.uuid4()}{ext}"
    path = Path("static/images") / name
    with open(path, "wb") as buf:
        shutil.copyfileobj(file.file, buf)
    return name, str(path)


def _build_image(
    filename: str,
    file_path_str: str,
    description: Optional[str],
    extra_tags: List[str],
    user_id: Optional[int],
) -> Image:
    ai_tags = generate_tags(file_path_str)
    combined_tags = list(set(extra_tags + ai_tags))
    embedding = generate_embedding(combined_tags, description)
    return Image(
        filename=filename,
        file_path=f"/static/images/{filename}",
        description=description,
        tags=combined_tags,
        embedding=embedding,
        user_id=user_id,
    )


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    va, vb = np.array(a), np.array(b)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    return float(np.dot(va, vb) / denom) if denom else 0.0


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
def read_root():
    return {"message": "Photography ML API", "status": "active"}


@app.post("/images/", response_model=ImagePublic)
@limiter.limit("10/hour")
async def create_image(
    request: Request,
    file: UploadFile = File(...),
    description: str = Form(None),
    tags: List[str] = Form([]),
    session: Session = Depends(get_session),
    current_user: User | None = Depends(get_current_user),
):
    filename, path = _save_upload(file)
    db_image = _build_image(filename, path, description, tags, getattr(current_user, "id", None))
    session.add(db_image)
    session.commit()
    session.refresh(db_image)
    return db_image


@app.post("/images/batch", response_model=List[ImagePublic])
@limiter.limit("5/hour")
async def create_images_batch(
    request: Request,
    files: List[UploadFile] = File(...),
    description: str = Form(None),
    session: Session = Depends(get_session),
    current_user: User | None = Depends(get_current_user),
):
    """Upload multiple images at once. Tags and embeddings are generated per image."""
    results = []
    for file in files:
        filename, path = _save_upload(file)
        db_image = _build_image(
            filename, path, description, [], getattr(current_user, "id", None)
        )
        session.add(db_image)
        session.flush()   # get id without full commit
        results.append(db_image)
    session.commit()
    for img in results:
        session.refresh(img)
    return results


@app.get("/images/similar/{image_id}", response_model=List[ImagePublic])
def get_similar_images(
    image_id: int,
    n: int = Query(default=5, ge=1, le=50),
    session: Session = Depends(get_session),
):
    """Return the N most similar images to the given one, ranked by cosine similarity of embeddings."""
    target = session.get(Image, image_id)
    if not target:
        raise HTTPException(status_code=404, detail="Image not found")
    if not target.embedding:
        raise HTTPException(status_code=422, detail="Target image has no embedding yet")

    candidates = session.exec(select(Image).where(Image.id != image_id)).all()
    scored = [
        (img, _cosine_similarity(target.embedding, img.embedding))
        for img in candidates
        if img.embedding
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [img for img, _ in scored[:n]]


@app.get("/images/", response_model=List[ImagePublic])
def read_images(
    offset: int = 0,
    limit: int = Query(default=100, le=100),
    session: Session = Depends(get_session),
):
    return session.exec(select(Image).offset(offset).limit(limit)).all()


@app.get("/images/{image_id}", response_model=ImagePublic)
def read_image(image_id: int, session: Session = Depends(get_session)):
    image = session.get(Image, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    return image


@app.patch("/images/{image_id}", response_model=ImagePublic)
def update_image(image_id: int, image: ImageUpdate, session: Session = Depends(get_session)):
    db_image = session.get(Image, image_id)
    if not db_image:
        raise HTTPException(status_code=404, detail="Image not found")
    for key, value in image.model_dump(exclude_unset=True).items():
        setattr(db_image, key, value)
    session.add(db_image)
    session.commit()
    session.refresh(db_image)
    return db_image


@app.delete("/images/{image_id}")
def delete_image(image_id: int, session: Session = Depends(get_session)):
    image = session.get(Image, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    session.delete(image)
    session.commit()
    return {"ok": True}
