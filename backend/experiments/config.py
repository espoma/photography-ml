"""
Experiment configurations.
Import PROMPTS and MODELS here to keep experiment scripts DRY.
"""
from app.services.ml_service import PROMPTS, FALLBACK_MODELS

# All available models in order of quality
MODELS = FALLBACK_MODELS  # ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-flash-8b"]

# Experiment matrix: each entry is one run
EXPERIMENTS = [
    # --- Prompt comparison (fixed model) ---
    {"name": "prompt_v1_baseline",   "prompt_version": "v1", "model_name": "gemini-2.5-flash"},
    {"name": "prompt_v2_detailed",   "prompt_version": "v2", "model_name": "gemini-2.5-flash"},
    {"name": "prompt_v3_structured", "prompt_version": "v3", "model_name": "gemini-2.5-flash"},

    # --- Model comparison (fixed prompt) ---
    {"name": "model_flash25",  "prompt_version": "v1", "model_name": "gemini-2.5-flash"},
    {"name": "model_flash15",  "prompt_version": "v1", "model_name": "gemini-1.5-flash"},
    {"name": "model_flash15_8b","prompt_version": "v1", "model_name": "gemini-1.5-flash-8b"},

    # --- Best prompt × best model ---
    {"name": "best_combo", "prompt_version": "v3", "model_name": "gemini-2.5-flash"},
]
