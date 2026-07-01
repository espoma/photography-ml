"""
Register all real images from static/images/ into DB (tag + embed),
then run storylines clustering and save results.

Run from backend/:  python register_and_run.py
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sqlmodel import Session, select

from app.database import engine
from app.models import Image
from app.services.ml_service import generate_tags, generate_embedding, describe_cluster

STATIC_DIR = Path(__file__).parent / "static" / "images"
OUT_JSON   = Path(__file__).parent / "storylines_output.json"
OUT_TREE   = Path(__file__).parent / "storylines_output"


def register_images(session: Session) -> list:
    files = sorted(
        list(STATIC_DIR.glob("*.jpg")) +
        list(STATIC_DIR.glob("*.jpeg")) +
        list(STATIC_DIR.glob("*.png"))
    )
    # Skip tiny files (test artifacts under 10 KB)
    files = [f for f in files if f.stat().st_size > 10_000]
    print(f"\n=== STEP 1: Tagging & embedding {len(files)} images ===\n")

    registered = []
    for i, path in enumerate(files, 1):
        existing = session.exec(select(Image).where(Image.file_path == str(path))).first()
        if existing:
            print(f"  [{i}/{len(files)}] skip (already in DB): {path.name[:20]}...")
            registered.append(existing)
            continue

        print(f"  [{i}/{len(files)}] {path.name[:30]}...", end=" ", flush=True)
        t0 = time.time()
        try:
            tags = generate_tags(str(path), prompt_version="v1")
        except Exception as e:
            print(f"FAILED tagging: {e}")
            continue

        try:
            embedding = generate_embedding(tags=tags, image_path=str(path))
        except Exception as e:
            print(f"FAILED embedding: {e}")
            embedding = None

        elapsed = time.time() - t0
        print(f"→ {len(tags)} tags  ({elapsed:.1f}s)")

        img = Image(
            filename=path.name,
            file_path=str(path),
            tags=tags,
            embedding=embedding,
            embedding_backend="clip",
        )
        session.add(img)
        session.commit()
        session.refresh(img)
        registered.append(img)

    return registered


def run_storylines(_unused: list) -> None:
    with Session(engine) as session:
        all_imgs = session.exec(select(Image)).all()
        # Extract all data while session is open to avoid DetachedInstanceError
        imgs = [
            {"id": img.id, "file_path": img.file_path, "tags": img.tags, "embedding": img.embedding}
            for img in all_imgs if img.embedding
        ]
    print(f"\n=== STEP 2: Clustering {len(imgs)} images ===\n")

    if len(imgs) < 3:
        print("Need at least 3 images with embeddings.")
        return

    X = np.array([img["embedding"] for img in imgs])

    best_k, best_score = 2, -1
    for k in range(2, min(8, len(imgs) - 1) + 1):
        labels = KMeans(n_clusters=k, random_state=42, n_init=10).fit_predict(X)
        score = silhouette_score(X, labels)
        print(f"  k={k}  silhouette={score:.3f}")
        if score > best_score:
            best_k, best_score = k, score

    print(f"\n  → Best k={best_k}\n")
    labels = KMeans(n_clusters=best_k, random_state=42, n_init=10).fit_predict(X)

    print(f"=== STEP 3: Describing {best_k} clusters with llava ===\n")
    themes = []
    for cid in range(best_k):
        cluster_imgs = [imgs[j] for j in range(len(imgs)) if labels[j] == cid]
        paths = [img["file_path"] for img in cluster_imgs]
        all_tags = [t for img in cluster_imgs for t in img["tags"]]
        top_tags = sorted(set(all_tags), key=lambda t: -all_tags.count(t))[:5]

        print(f"  Cluster {cid+1}/{best_k}: {len(cluster_imgs)} images — asking llava...", end=" ", flush=True)
        t0 = time.time()
        desc = describe_cluster(paths, user_preferences=None, user_prompt=None)
        print(f"({time.time()-t0:.1f}s) → \"{desc.get('title','?')}\"")
        time.sleep(1)

        themes.append({
            "theme_id": cid,
            "title": desc.get("title", f"Group {cid+1}"),
            "description": desc.get("description", ""),
            "top_tags": top_tags,
            "image_ids": [img["id"] for img in cluster_imgs],
            "image_paths": paths,
        })

    options = [{"option_id": 0, "n_themes": best_k, "themes": themes}]
    with open(OUT_JSON, "w") as f:
        json.dump(options, f, indent=2)

    print(f"\n  JSON saved → {OUT_JSON}")


def organize(options_path: Path, source_dir: Path, output_dir: Path) -> None:
    import re, shutil
    print(f"\n=== STEP 4: Building folder tree → {output_dir} ===\n")

    def slugify(text):
        text = text.lower().strip()
        text = re.sub(r"[^\w\s-]", "", text)
        return re.sub(r"[\s_-]+", "_", text)[:50]

    with open(options_path) as f:
        options = json.load(f)

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    for option in options:
        opt_dir = output_dir / f"option_{option['option_id']+1}__{option['n_themes']}_themes"
        opt_dir.mkdir()
        for theme in option["themes"]:
            theme_dir = opt_dir / f"theme_{theme['theme_id']+1}__{slugify(theme['title'])}"
            theme_dir.mkdir()
            for idx, img_path in enumerate(theme["image_paths"], 1):
                src = Path(img_path)
                if src.exists():
                    dst = theme_dir / f"{idx:02d}_{src.name}"
                    shutil.copy2(src, dst)
                    print(f"  {dst.relative_to(output_dir)}")

    print(f"\nDone. Open {output_dir} in Finder to browse.")


if __name__ == "__main__":
    with Session(engine) as session:
        images = register_images(session)
    print(f"\n  {len(images)} images registered.")
    run_storylines(images)
    organize(OUT_JSON, STATIC_DIR, OUT_TREE)
