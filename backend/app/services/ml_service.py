"""
ML service: tag generation + embedding generation.

Embedding backends (pick one per deployment):
  clip      — visual image embeddings via CLIP ViT-B/32 (local, 512-dim, best for photo similarity)
  sentence  — semantic text embeddings via all-MiniLM-L6-v2 (local, 384-dim, fast)
  gemini    — text embeddings via Gemini text-embedding-004 (API, 768-dim)

Models are lazy-loaded on first call so startup stays fast.
"""
import json
import mimetypes
from typing import List, Optional

from google import genai
from google.genai import types
from langsmith import traceable
from langsmith.run_helpers import get_current_run_tree

# ── Prompt library ────────────────────────────────────────────────────────────

PROMPTS: dict[str, str] = {
    "v1": (
        "You are an expert photography assistant. Analyze this image and generate 5-10 highly "
        "descriptive keywords. Focus on lighting, mood, subject matter, and composition. "
        "Only use lowercase."
    ),
    "v2": (
        "Analyze this photograph and return 5-10 descriptive tags covering: subject "
        "(person/landscape/object), lighting quality (harsh/soft/natural), mood/emotion, "
        "color palette, and photographic style. Lowercase only."
    ),
    "v3": (
        "You are a photography metadata specialist. Generate exactly 8 tags for this image. "
        "Include one tag each for: primary subject, secondary elements, lighting, mood, "
        "composition style, color temperature, photographic technique, and post-processing "
        "style. Be specific and lowercase."
    ),
}

FALLBACK_MODELS = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-flash-8b"]
GEMINI_EMBED_MODEL = "models/text-embedding-004"

# ── Model singletons (lazy-loaded) ────────────────────────────────────────────

_clip_model = None
_sentence_model = None


def _get_clip_model():
    global _clip_model
    if _clip_model is None:
        from sentence_transformers import SentenceTransformer
        print("Loading CLIP model (first call only)...")
        _clip_model = SentenceTransformer("clip-ViT-B-32")
    return _clip_model


def _get_sentence_model():
    global _sentence_model
    if _sentence_model is None:
        from sentence_transformers import SentenceTransformer
        print("Loading SentenceTransformer model (first call only)...")
        _sentence_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _sentence_model


# ── Tag generation ────────────────────────────────────────────────────────────

@traceable(name="generate_tags", tags=["gemini", "photography"])
def generate_tags(
    image_path: str,
    prompt_version: str = "v1",
    model_name: str = "gemini-2.5-flash",
) -> List[str]:
    """Generate descriptive tags for a photo using Gemini with multi-model fallback."""
    print(f"ML: tagging {image_path} | prompt={prompt_version} model={model_name}")

    prompt = PROMPTS.get(prompt_version, PROMPTS["v1"])
    models_to_try = [model_name] + [m for m in FALLBACK_MODELS if m != model_name]
    client = genai.Client()

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type:
        mime_type = "image/jpeg"

    image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)

    for model in models_to_try:
        try:
            response = client.models.generate_content(
                model=model,
                contents=[image_part, prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema={"type": "array", "items": {"type": "string"}},
                ),
            )
            tags = json.loads(response.text)

            rt = get_current_run_tree()
            if rt is not None:
                usage = getattr(response, "usage_metadata", None)
                rt.extra = rt.extra or {}
                rt.extra["metadata"] = {
                    "model_used": model,
                    "prompt_version": prompt_version,
                    "input_tokens": getattr(usage, "prompt_token_count", None),
                    "output_tokens": getattr(usage, "candidates_token_count", None),
                    "total_tokens": getattr(usage, "total_token_count", None),
                    "fallback_used": model != model_name,
                }
                rt.patch()

            return tags

        except Exception as e:
            print(f"Model {model} failed: {e}")
            if model == models_to_try[-1]:
                return ["ai_generated", "photography"]

    return ["ai_generated", "photography"]


# ── Embedding generation ──────────────────────────────────────────────────────

@traceable(name="generate_embedding", tags=["embedding"])
def generate_embedding(
    tags: List[str],
    description: Optional[str] = None,
    image_path: Optional[str] = None,
    backend: str = "clip",
) -> Optional[List[float]]:
    """
    Generate an embedding for an image.

    Backends:
      clip      — visual embedding from raw pixels (best for photo similarity)
      sentence  — semantic text embedding from tags + description (fastest)
      gemini    — text embedding from Gemini API (best semantic quality, costs quota)

    Returns None on failure so upload still succeeds.
    """
    try:
        if backend == "clip":
            return _embed_clip(image_path, tags, description)
        elif backend == "sentence":
            return _embed_sentence(tags, description)
        elif backend == "gemini":
            return _embed_gemini(tags, description)
        else:
            print(f"Unknown embedding backend '{backend}', falling back to sentence")
            return _embed_sentence(tags, description)
    except Exception as e:
        print(f"Embedding failed (non-fatal): {e}")
        return None


def _embed_clip(image_path: Optional[str], tags: List[str], description: Optional[str]) -> Optional[List[float]]:
    """512-dim visual embedding from image pixels."""
    if not image_path:
        # No image path — fall back to text via CLIP text encoder
        text = description or ", ".join(tags)
        return _get_clip_model().encode(text).tolist()

    from PIL import Image as PILImage
    img = PILImage.open(image_path).convert("RGB")
    return _get_clip_model().encode(img).tolist()


def _embed_sentence(tags: List[str], description: Optional[str]) -> List[float]:
    """384-dim semantic text embedding."""
    text = ", ".join(tags)
    if description:
        text = f"{description}. {text}"
    return _get_sentence_model().encode(text).tolist()


def _embed_gemini(tags: List[str], description: Optional[str]) -> Optional[List[float]]:
    """768-dim text embedding via Gemini API."""
    text = ", ".join(tags)
    if description:
        text = f"{description}. Tags: {text}"
    client = genai.Client()
    result = client.models.embed_content(model=GEMINI_EMBED_MODEL, contents=text)
    return list(result.embeddings[0].values)
