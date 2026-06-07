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

EMBEDDING_MODEL = "models/text-embedding-004"


# ── Tag generation ────────────────────────────────────────────────────────────

@traceable(name="generate_tags", tags=["gemini", "photography"])
def generate_tags(
    image_path: str,
    prompt_version: str = "v1",
    model_name: str = "gemini-2.5-flash",
) -> List[str]:
    """Generate descriptive tags for a photo using Gemini."""
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


# ── Embedding generation ───────────────────────────────────────────────────────

@traceable(name="generate_embedding", tags=["gemini", "embedding"])
def generate_embedding(tags: List[str], description: Optional[str] = None) -> Optional[List[float]]:
    """
    Generate a 768-dim semantic embedding from image tags + description.

    Uses Gemini text-embedding-004. Returns None on failure so the upload
    still succeeds — embedding can be backfilled later.

    Future upgrade: replace with CLIP for visual embeddings.
    """
    text = ", ".join(tags)
    if description:
        text = f"{description}. Tags: {text}"

    try:
        client = genai.Client()
        result = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text,
        )
        return list(result.embeddings[0].values)
    except Exception as e:
        print(f"Embedding generation failed (non-fatal): {e}")
        return None
