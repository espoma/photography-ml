"""
Experiment runner for prompt/model comparisons.

Usage (from backend/):
    # Compare all prompt variants on one image
    python -m experiments.run_experiment --mode prompts --image path/to/photo.jpg

    # Compare all models on one image
    python -m experiments.run_experiment --mode models --image path/to/photo.jpg

    # Run everything
    python -m experiments.run_experiment --mode all --image path/to/photo.jpg

Each run is traced in LangSmith under the project set by LANGSMITH_PROJECT env var.
Set LANGSMITH_PROJECT=photography-ml-experiments in your .env for isolation.
"""
import argparse
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Load backend/.env so DATABASE_URL, GEMINI_API_KEY, LANGSMITH_* are available
load_dotenv(Path(__file__).parent.parent / ".env")

# Add backend root to path so `app.*` imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.ml_service import generate_tags, PROMPTS, FALLBACK_MODELS
from experiments.config import EXPERIMENTS


def run_single(image_path: str, name: str, prompt_version: str, model_name: str) -> dict:
    print(f"\n── {name} ──────────────────────────────")
    print(f"   prompt={prompt_version}  model={model_name}")
    tags = generate_tags(
        image_path,
        prompt_version=prompt_version,
        model_name=model_name,
    )
    print(f"   tags: {tags}")
    return {"name": name, "prompt_version": prompt_version, "model_name": model_name, "tags": tags}


def main():
    parser = argparse.ArgumentParser(description="Run tagging experiments")
    parser.add_argument("--image", required=True, help="Path to the image file")
    parser.add_argument(
        "--mode",
        choices=["prompts", "models", "all"],
        default="all",
        help="Which experiment set to run",
    )
    parser.add_argument("--output", default=None, help="Optional JSON file to write results")
    args = parser.parse_args()

    if not Path(args.image).exists():
        print(f"Image not found: {args.image}")
        sys.exit(1)

    # Select subset based on mode
    if args.mode == "prompts":
        configs = [e for e in EXPERIMENTS if e["name"].startswith("prompt_")]
    elif args.mode == "models":
        configs = [e for e in EXPERIMENTS if e["name"].startswith("model_")]
    else:
        configs = EXPERIMENTS

    print(f"Running {len(configs)} experiments on: {args.image}")
    results = [run_single(args.image, **cfg) for cfg in configs]

    # Summary table
    print("\n── Results Summary ──────────────────────────────────")
    print(f"{'Name':<25} {'Prompt':<8} {'Model':<20} {'# Tags'}")
    print("-" * 65)
    for r in results:
        print(f"{r['name']:<25} {r['prompt_version']:<8} {r['model_name']:<20} {len(r['tags'])}")

    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults written to {args.output}")

    print("\nAll runs are visible in LangSmith dashboard under project:", os.getenv("LANGSMITH_PROJECT", "default"))


if __name__ == "__main__":
    main()
