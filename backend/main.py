from contextlib import asynccontextmanager
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, Query, File, UploadFile, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlmodel import Session, select
from app.database import create_db_and_tables, get_session
from app.models import Image, ImagePublic, ImageUpdate
from app.services.ml_service import generate_tags, generate_embedding, describe_cluster
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
import time
import numpy as np
from pathlib import Path

# Absolute path to uploaded images — robust regardless of CWD
STATIC_DIR = Path(__file__).parent / "static" / "images"


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


class Theme(BaseModel):
    theme_id: int
    title: str           # Gemini-generated narrative title
    description: str     # Gemini-generated 1-2 sentence coherent description
    image_count: int
    images: List[ImageSummary]


class StorylinesOption(BaseModel):
    option_id: int
    n_themes: int
    themes: List[Theme]


class StorylinesRequest(BaseModel):
    image_ids: Optional[List[int]] = None  # None = all images for the authenticated user
    n_options: int = 3                     # how many different splitting proposals to return
    min_themes: int = 3                    # fewest clusters in any option
    max_themes: int = 6                    # most clusters in any option
    embedding_backend: str = "clip"
    user_prompt: Optional[str] = None      # free-text intent, e.g. "for an Instagram carousel"


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


def _k_values(n_options: int, min_k: int, max_k: int) -> List[int]:
    """Return n_options evenly-spaced unique K values between min_k and max_k."""
    if min_k == max_k or n_options == 1:
        return [min_k]
    import numpy as np_
    raw = np_.linspace(min_k, max_k, n_options)
    seen, result = set(), []
    for v in map(int, np_.round(raw)):
        if v not in seen:
            seen.add(v)
            result.append(v)
    return result


def _representative_paths(images, embeddings: np.ndarray, labels, cluster_id: int, n: int = 4) -> List[str]:
    """Return absolute paths of up to n images closest to the cluster centroid."""
    idx = [i for i, l in enumerate(labels) if l == cluster_id]
    vecs = embeddings[idx]
    centroid = vecs.mean(axis=0)
    distances = np.linalg.norm(vecs - centroid, axis=1)
    closest = np.argsort(distances)[:n]
    return [str(STATIC_DIR / images[idx[i]].filename) for i in closest]


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


@app.post("/images/storylines", response_model=List[StorylinesOption])
def create_storylines(
    body: StorylinesRequest,
    session: Session = Depends(get_session),
    current_user: User | None = Depends(get_current_user),
):
    """
    Return n_options different ways to split images into thematic groups.

    Each option uses a different number of clusters (K). For every cluster,
    Gemini receives the most representative images and writes a narrative
    title + description informed by the user's stored preferences.
    """
    from sklearn.cluster import KMeans
    from app.models import UserPreference

    # ── 1. Fetch images ───────────────────────────────────────────────────────
    query = select(Image)
    if body.image_ids:
        # Explicit list — use as-is regardless of ownership
        query = query.where(Image.id.in_(body.image_ids))
    elif current_user:
        # Return this user's images AND any anonymous (user_id=null) uploads
        query = query.where(
            (Image.user_id == current_user.id) | (Image.user_id == None)  # noqa: E711
        )

    images = session.exec(query).all()
    images = [img for img in images if img.embedding and img.embedding_backend == body.embedding_backend]

    if len(images) < 2:
        raise HTTPException(
            status_code=422,
            detail=f"Need at least 2 images with '{body.embedding_backend}' embeddings. "
                   f"Found {len(images)}.",
        )

    embeddings = np.array([img.embedding for img in images])

    # ── 2. Load user preferences ──────────────────────────────────────────────
    user_prefs: dict = {}
    if current_user:
        prefs = session.exec(
            select(UserPreference).where(UserPreference.user_id == current_user.id)
        ).all()
        user_prefs = {p.key: p.value for p in prefs}

    # ── 3. Build K values for each option ─────────────────────────────────────
    min_k = min(body.min_themes, len(images))
    max_k = min(body.max_themes, len(images))
    ks = _k_values(body.n_options, min_k, max_k)

    # ── 4. Cluster + describe for each K ─────────────────────────────────────
    options: List[StorylinesOption] = []

    for option_id, k in enumerate(ks):
        labels = KMeans(n_clusters=k, random_state=42, n_init=10).fit_predict(embeddings)

        themes: List[Theme] = []
        for cluster_id in range(k):
            group = [img for img, lbl in zip(images, labels) if lbl == cluster_id]
            rep_paths = _representative_paths(images, embeddings, labels, cluster_id, n=4)

            if cluster_id > 0:
                time.sleep(1.5)  # avoid Gemini per-minute rate limits

            narrative = describe_cluster(
                image_paths=rep_paths,
                user_preferences=user_prefs or None,
                user_prompt=body.user_prompt,
            )

            themes.append(Theme(
                theme_id=cluster_id,
                title=narrative["title"],
                description=narrative["description"],
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

        themes.sort(key=lambda t: t.image_count, reverse=True)
        options.append(StorylinesOption(option_id=option_id, n_themes=k, themes=themes))

    return options


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
