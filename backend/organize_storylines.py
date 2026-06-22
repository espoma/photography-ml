"""
organize_storylines.py — copy photos into a human-browsable folder tree.

Usage:
    python organize_storylines.py storylines.json [OPTIONS]

    --source-dir   DIR   Where original photos live (default: static/images/)
    --output-dir   DIR   Where to write the organised tree (default: ./storylines_output)
    --copy / --link      Copy files (default) or symlink them (faster, saves disk)

Output structure:
    storylines_output/
    └── option_1__3_themes/
        ├── theme_1__the_adorned_gaze/
        │   ├── 01_abc123.jpg
        │   └── 02_def456.jpg
        └── theme_2__sunlit_contemplation/
            └── ...
"""

import argparse
import json
import os
import re
import shutil
from pathlib import Path


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "_", text)
    return text[:50]


def organize(
    storylines_path: Path,
    source_dir: Path,
    output_dir: Path,
    use_symlinks: bool = False,
) -> None:
    with open(storylines_path) as f:
        options = json.load(f)

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    for option in options:
        opt_id = option["option_id"] + 1
        n_themes = option["n_themes"]
        opt_slug = f"option_{opt_id}__{n_themes}_themes"
        opt_dir = output_dir / opt_slug
        opt_dir.mkdir()

        # Write a short README inside each option folder
        summary_lines = [f"Option {opt_id} — {n_themes} themes\n"]
        for theme in option["themes"]:
            summary_lines.append(
                f"  Theme {theme['theme_id'] + 1}: {theme['title']}\n"
                f"    {theme['description']}\n"
                f"    {theme['image_count']} photos\n"
            )
        (opt_dir / "README.txt").write_text("\n".join(summary_lines))

        for theme in option["themes"]:
            t_id = theme["theme_id"] + 1
            t_slug = _slugify(theme["title"])
            theme_dir = opt_dir / f"theme_{t_id}__{t_slug}"
            theme_dir.mkdir()

            for i, img in enumerate(theme["images"], start=1):
                filename = img["filename"]
                src = source_dir / filename
                if not src.exists():
                    print(f"  [warn] source not found: {src}")
                    continue

                dest = theme_dir / f"{i:02d}_{filename}"
                if use_symlinks:
                    dest.symlink_to(src.resolve())
                else:
                    shutil.copy2(src, dest)

    print(f"\nOrganised {len(options)} options → {output_dir}/")
    for option in options:
        opt_id = option["option_id"] + 1
        n_themes = option["n_themes"]
        print(f"  Option {opt_id} ({n_themes} themes):")
        for theme in option["themes"]:
            print(f"    Theme {theme['theme_id'] + 1}: \"{theme['title']}\" — {theme['image_count']} photos")


def main() -> None:
    parser = argparse.ArgumentParser(description="Organise storylines JSON into browsable folders.")
    parser.add_argument("storylines_json", type=Path, help="Path to storylines JSON file")
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=Path(__file__).parent / "static" / "images",
        help="Directory containing original image files",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("storylines_output"),
        help="Where to write the organised folder tree",
    )
    parser.add_argument(
        "--link",
        action="store_true",
        default=False,
        help="Symlink files instead of copying (saves disk space)",
    )
    args = parser.parse_args()

    if not args.storylines_json.exists():
        print(f"Error: {args.storylines_json} not found")
        raise SystemExit(1)

    organize(
        storylines_path=args.storylines_json,
        source_dir=args.source_dir,
        output_dir=args.output_dir,
        use_symlinks=args.link,
    )


if __name__ == "__main__":
    main()
