"""
ML service: tag generation + embedding generation.

Embedding backends (set EMBEDDING_BACKEND env var):
  clip      — visual image embeddings via CLIP ViT-B/32 (local, 512-dim, best for photo similarity)
  sentence  — semantic text embeddings via all-MiniLM-L6-v2 (local, 384-dim, fast)
  gemini    — text embeddings via Gemini text-embedding-004 (API, 768-dim)

Tagging/description backends (set TAGGING_BACKEND env var):
  ollama    — fully local via Ollama, images never leave the machine (default)
              OLLAMA_VISION_MODEL: llava (7B, accurate) | llava-phi3 (3.8B, faster)
  gemini    — Google Gemini API, sends images to Google
              GEMINI_TAG_MODEL: gemini-2.5-flash | gemini-1.5-flash | gemini-1.5-flash-8b
"""
import base64
import json
import mimetypes
import os
from typing import List, Optional

import requests
from google import genai
from google.genai import types
from langsmith import traceable
from langsmith.run_helpers import get_current_run_tree

TAGGING_BACKEND = os.getenv("TAGGING_BACKEND", "ollama")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_VISION_MODEL = os.getenv("OLLAMA_VISION_MODEL", "llava-phi3")
GEMINI_TAG_MODEL = os.getenv("GEMINI_TAG_MODEL", "gemini-2.5-flash")

# ── Prompt library ────────────────────────────────────────────────────────────

PROMPTS: dict[str, str] = {
    # ── Tagging prompts ───────────────────────────────────────────────────────
    # Observational only — describe what is literally present, no aesthetic opinion.
    "v1": (
        "Look at this photo and list 5-10 tags describing exactly what you see: "
        "who or what is in the frame, the light source and quality, colours present, "
        "background or setting, and any visible technical choices (shallow depth, motion blur, etc.). "
        "Do not judge or interpret — only observe. Lowercase only."
    ),
    "v2": (
        "Describe this photo using 5-10 lowercase tags. Cover: subject (what/who), "
        "light (source, direction, quality), colours, setting or background, "
        "camera distance (close-up/mid/wide), and any visible post-processing (B&W, grain, etc.). "
        "State only what you can see. No aesthetic opinions."
    ),
    "v3": (
        "List exactly 8 lowercase tags for this photo. One tag each for: "
        "primary subject, secondary elements in frame, light source, light quality, "
        "dominant colour(s), background/setting, camera-to-subject distance, "
        "and any visible processing or format choice. Observe only — no interpretation."
    ),

    # ── Cluster description prompt ────────────────────────────────────────────
    # Used in describe_cluster(). {user_context} and {n_images} are filled at call time.
    "cluster_description": (
        "You are helping a photographer understand their own work.\n\n"
        "You are looking at {n_images} photos the photographer grouped together. "
        "Your job is to describe — as neutrally and specifically as possible — "
        "what these photos visually have in common.\n\n"
        "{user_context}"
        "Tasks:\n"
        "1. Write a SHORT TITLE (3-5 words) that names the shared visual element or situation "
        "you actually see — not a poetic interpretation.\n"
        "2. Write 1-2 sentences stating the concrete visual or situational thread: "
        "what subject, light condition, setting, or framing recurs across these photos.\n\n"
        "Do not impose meaning, narrative, or aesthetic judgment. "
        "Describe what the photographer chose to photograph, not what it 'means'.\n\n"
        'Respond in JSON: {{"title": "...", "description": "..."}}'
    ),
}

FALLBACK_MODELS = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-flash-8b"]
GEMINI_EMBED_MODEL = "models/text-embedding-004"


# ── Ollama helpers ────────────────────────────────────────────────────────────

def _ollama_vision(image_paths: List[str], prompt: str, model: str = OLLAMA_VISION_MODEL) -> str:
    """Call Ollama /api/generate with one or more images (base64-encoded). Returns raw text."""
    images_b64 = []
    for path in image_paths:
        with open(path, "rb") as f:
            images_b64.append(base64.b64encode(f.read()).decode())

    payload = {
        "model": model,
        "prompt": prompt,
        "images": images_b64,
        "stream": False,
    }
    resp = requests.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json().get("response", "")


def _parse_json_tolerant(raw: str) -> list:
    """Parse a JSON array from llava output, tolerating trailing commas."""
    import re as _re
    start, end = raw.find("["), raw.rfind("]")
    if start == -1 or end == -1:
        return []
    chunk = raw[start : end + 1]
    # Strip trailing commas before ] or }
    chunk = _re.sub(r",\s*([\]}])", r"\1", chunk)
    return json.loads(chunk)


def _tags_via_ollama(image_path: str, prompt_version: str = "v1") -> List[str]:
    prompt = (
        PROMPTS.get(prompt_version, PROMPTS["v1"])
        + "\nReturn ONLY a JSON array of lowercase strings, e.g. [\"tag1\", \"tag2\"]."
    )
    raw = _ollama_vision([image_path], prompt)
    result = _parse_json_tolerant(raw)
    return result if result else ["photography"]


def _describe_cluster_via_ollama(
    image_paths: List[str],
    user_preferences: Optional[dict],
    user_prompt: Optional[str],
    n_images: int = 4,
) -> dict:
    sampled = image_paths[:n_images]

    context_lines = []
    if user_prompt:
        context_lines.append(f"The photographer's intent: {user_prompt}")
    if user_preferences:
        readable = "; ".join(f"{k}: {v}" for k, v in user_preferences.items())
        context_lines.append(f"Their known preferences: {readable}")
    user_context = ("\n".join(context_lines) + "\n\n") if context_lines else ""

    prompt_text = (
        PROMPTS["cluster_description"].format(n_images=len(sampled), user_context=user_context)
        + "\nReturn ONLY the JSON object, no markdown."
    )

    raw = _ollama_vision(sampled, prompt_text)
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        return {"title": "Untitled group", "description": ""}
    import re as _re
    chunk = raw[start : end + 1]
    chunk = _re.sub(r",\s*([\]}])", r"\1", chunk)
    try:
        return json.loads(chunk)
    except json.JSONDecodeError:
        return {"title": "Untitled group", "description": ""}

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

@traceable(name="generate_tags", tags=["photography"])
def generate_tags(
    image_path: str,
    prompt_version: str = "v1",
    model_name: str = GEMINI_TAG_MODEL,
    backend: Optional[str] = None,
) -> List[str]:
    """Generate descriptive tags for a photo. Backend defaults to TAGGING_BACKEND env var."""
    active_backend = backend or TAGGING_BACKEND
    print(f"ML: tagging {image_path} | backend={active_backend} prompt={prompt_version}")

    if active_backend == "ollama":
        try:
            return _tags_via_ollama(image_path, prompt_version)
        except Exception as e:
            print(f"Ollama tagging failed: {e}")
            return ["ai_generated", "photography"]

    # --- Gemini path ---
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


# ── Cluster description ───────────────────────────────────────────────────────

@traceable(name="describe_cluster", tags=["storylines"])
def describe_cluster(
    image_paths: List[str],
    user_preferences: Optional[dict] = None,
    user_prompt: Optional[str] = None,
    n_images: int = 4,
    backend: Optional[str] = None,
) -> dict:
    """
    Send representative images from a cluster to Gemini and get a coherent
    narrative title + description.

    Args:
        image_paths: paths to representative images (sorted centroid-first)
        user_preferences: dict from UserPreference table (injected as context)
        user_prompt: optional free-text intent from the request ("for Instagram", etc.)
        n_images: max images to send (keeps API cost low)

    Returns:
        {"title": str, "description": str}
    """
    active_backend = backend or TAGGING_BACKEND

    if active_backend == "ollama":
        try:
            return _describe_cluster_via_ollama(image_paths, user_preferences, user_prompt, n_images)
        except Exception as e:
            print(f"Ollama describe_cluster failed: {e}")
            return {"title": "Untitled group", "description": ""}

    sampled = image_paths[:n_images]

    # Build user context block
    context_lines = []
    if user_prompt:
        context_lines.append(f"The photographer's intent: {user_prompt}")
    if user_preferences:
        readable = "; ".join(f"{k}: {v}" for k, v in user_preferences.items())
        context_lines.append(f"Their known preferences: {readable}")
    user_context = ("\n".join(context_lines) + "\n\n") if context_lines else ""

    prompt_text = PROMPTS["cluster_description"].format(
        n_images=len(sampled),
        user_context=user_context,
    )

    try:
        client = genai.Client()
        contents = []
        for path in sampled:
            with open(path, "rb") as f:
                image_bytes = f.read()
            mime_type, _ = mimetypes.guess_type(path)
            contents.append(
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type or "image/jpeg")
            )
        contents.append(prompt_text)

        response = client.models.generate_content(
            model=GEMINI_TAG_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema={
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                    },
                    "required": ["title", "description"],
                },
            ),
        )
        return json.loads(response.text)

    except Exception as e:
        print(f"describe_cluster failed (non-fatal): {e}")
        return {"title": "Untitled group", "description": ""}


# ── Internal embedding helpers ────────────────────────────────────────────────

def _embed_gemini(tags: List[str], description: Optional[str]) -> Optional[List[float]]:
    """768-dim text embedding via Gemini API."""
    text = ", ".join(tags)
    if description:
        text = f"{description}. Tags: {text}"
    client = genai.Client()
    result = client.models.embed_content(model=GEMINI_EMBED_MODEL, contents=text)
    return list(result.embeddings[0].values)
