from contextlib import asynccontextmanager
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, Query, File, UploadFile, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlmodel import Session, select
from app.database import create_db_and_tables, get_session
from app.models import Image, ImagePublic, ImageUpdate
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
from collections import Counter
import shutil
import uuid
import numpy as np
from pathlib import Path


# ── App setup ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    Path("static/images").mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="Photography ML",
    description="API for Smart Photography Portfolio",
    version="0.3.0",
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


# ── Response models ───────────────────────────────────────────────────────────

class ImageSummary(BaseModel):
    id: int
    filename: str
    file_path: str
    tags: List[str]
    description: Optional[str]


class Storyline(BaseModel):
    story_id: int
    theme: str           # top tags that characterise this group
    image_count: int
    images: List[ImageSummary]


class StorylinesRequest(BaseModel):
    image_ids: Optional[List[int]] = None   # None = all images for the user
    n_stories: Optional[int] = None         # None = auto-detect optimal k
    max_stories: int = 8
    embedding_backend: str = "clip"         # must match the backend used when uploading


# ── Internal helpers ──────────────────────────────────────────────────────────

def _save_upload(file: UploadFile) -> tuple[str, str]:
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
    embedding_backend: str = "clip",
) -> Image:
    ai_tags = generate_tags(file_path_str)
    combined_tags = list(set(extra_tags + ai_tags))
    embedding = generate_embedding(
        tags=combined_tags,
        description=description,
        image_path=file_path_str,
        backend=embedding_backend,
    )
    return Image(
        filename=filename,
        file_path=f"/static/images/{filename}",
        description=description,
        tags=combined_tags,
        embedding=embedding,
        embedding_backend=embedding_backend if embedding else None,
        user_id=user_id,
    )


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    va, vb = np.array(a), np.array(b)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    return float(np.dot(va, vb) / denom) if denom else 0.0


def _auto_k(embeddings: np.ndarray, max_k: int) -> int:
    """Pick optimal number of clusters via silhouette score."""
    from sklearn.metrics import silhouette_score
    from sklearn.cluster import KMeans

    best_k, best_score = 2, -1.0
    for k in range(2, min(max_k + 1, len(embeddings))):
        labels = KMeans(n_clusters=k, random_state=42, n_init=10).fit_predict(embeddings)
        score = silhouette_score(embeddings, labels)
        if score > best_score:
            best_score, best_k = score, k
    return best_k


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
def read_root():
    return {"message": "Photography ML API", "status": "active", "version": "0.3.0"}


@app.post("/images/", response_model=ImagePublic)
@limiter.limit("50/hour")
async def create_image(
    request: Request,
    file: UploadFile = File(...),
    description: str = Form(None),
    tags: List[str] = Form([]),
    embedding_backend: str = Form("clip"),
    session: Session = Depends(get_session),
    current_user: User | None = Depends(get_current_user),
):
    """Upload a single image. Tags and embedding generated automatically."""
    filename, path = _save_upload(file)
    db_image = _build_image(filename, path, description, tags, getattr(current_user, "id", None), embedding_backend)
    session.add(db_image)
    session.commit()
    session.refresh(db_image)
    return db_image


@app.post("/images/batch", response_model=List[ImagePublic])
@limiter.limit("10/hour")
async def create_images_batch(
    request: Request,
    files: List[UploadFile] = File(...),
    description: str = Form(None),
    embedding_backend: str = Form("clip"),
    session: Session = Depends(get_session),
    current_user: User | None = Depends(get_current_user),
):
    """Upload multiple images at once. Each gets its own tags and embedding."""
    results = []
    for file in files:
        filename, path = _save_upload(file)
        db_image = _build_image(
            filename, path, description, [], getattr(current_user, "id", None), embedding_backend
        )
        session.add(db_image)
        session.flush()
        results.append(db_image)
    session.commit()
    for img in results:
        session.refresh(img)
    return results


@app.post("/images/storylines", response_model=List[Storyline])
def create_storylines(
    body: StorylinesRequest,
    session: Session = Depends(get_session),
    current_user: User | None = Depends(get_current_user),
):
    """
    Group images into thematic story lines using KMeans clustering on embeddings.

    - image_ids: which images to cluster (default: all images for the current user)
    - n_stories: how many groups (default: auto-detected via silhouette score)
    - max_stories: upper bound for auto-detection (default 8)
    - embedding_backend: only images embedded with this backend are used
    """
    from sklearn.cluster import KMeans

    # Fetch candidate images
    query = select(Image)
    if body.image_ids:
        query = query.where(Image.id.in_(body.image_ids))
    elif current_user:
        query = query.where(Image.user_id == current_user.id)

    images = session.exec(query).all()

    # Keep only those with embeddings from the requested backend
    images = [
        img for img in images
        if img.embedding and img.embedding_backend == body.embedding_backend
    ]

    if len(images) < 2:
        raise HTTPException(
            status_code=422,
            detail=f"Need at least 2 images with '{body.embedding_backend}' embeddings. "
                   f"Found {len(images)}. Upload images with embedding_backend={body.embedding_backend}.",
        )

    embeddings = np.array([img.embedding for img in images])

    k = body.n_stories or _auto_k(embeddings, body.max_stories)
    k = min(k, len(images))

    labels = KMeans(n_clusters=k, random_state=42, n_init=10).fit_predict(embeddings)

    storylines = []
    for story_id in range(k):
        group = [img for img, lbl in zip(images, labels) if lbl == story_id]
        all_tags = [tag for img in group for tag in img.tags]
        top_tags = ", ".join(t for t, _ in Counter(all_tags).most_common(5))
        storylines.append(Storyline(
            story_id=story_id,
            theme=top_tags,
            image_count=len(group),
            images=[
                ImageSummary(
                    id=img.id,
                    filename=img.filename,
                    file_path=img.file_path,
                    tags=img.tags,
                    description=img.description,
                )
                for img in group
            ],
        ))

    # Sort by group size descending so the dominant theme is first
    storylines.sort(key=lambda s: s.image_count, reverse=True)
    return storylines


@app.get("/images/similar/{image_id}", response_model=List[ImagePublic])
def get_similar_images(
    image_id: int,
    n: int = Query(default=5, ge=1, le=50),
    session: Session = Depends(get_session),
):
    """Return N most visually similar images ranked by cosine similarity."""
    target = session.get(Image, image_id)
    if not target:
        raise HTTPException(status_code=404, detail="Image not found")
    if not target.embedding:
        raise HTTPException(status_code=422, detail="Target image has no embedding yet")

    candidates = session.exec(
        select(Image).where(
            Image.id != image_id,
            Image.embedding_backend == target.embedding_backend,
        )
    ).all()

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
