"""Generate the two fixed speaker portraits once (Cloudflare FLUX via m10-mixcover's provider).

Run with m10-mixcover's interpreter, because that is where the provider and its API keys live:
  /home/lam/Documents/projects/Youtube/Youtube-music/m10-mixcover/.venv/bin/python portraits.py [--seed N] [--only lea|hugo] [--force]

Portraits are saved to assets/speakers/ and reused by every episode. Fonts are copied to assets/fonts/.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIXCOVER = Path("/home/lam/Documents/projects/Youtube/Youtube-music/m10-mixcover")

STYLE = ("Flat vector illustration, clean modern podcast avatar, soft shading, head and shoulders portrait, "
         "centered, looking at the viewer with a friendly smile, plain single-colour background, "
         "fictional adult character, no text, no logo, no watermark.")
PROMPTS = {
    "lea": ("A fictional French woman in her late twenties with shoulder-length wavy brown hair, "
            "wearing a mustard yellow sweater and small headphones around her neck, "
            "plain deep teal background. " + STYLE),
    "hugo": ("A fictional French man in his early thirties with short dark hair and a light beard, "
             "wearing a navy blue shirt and small headphones around his neck, "
             "plain warm terracotta background. " + STYLE),
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--only", choices=list(PROMPTS))
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    sys.path.insert(0, str(MIXCOVER))
    from dotenv import load_dotenv
    from mixcover.image_gen.base import ImageRequest
    from mixcover.image_gen.cloudflare_provider import CloudflareProvider

    load_dotenv(MIXCOVER / ".env")
    out_dir = ROOT / "assets" / "speakers"
    out_dir.mkdir(parents=True, exist_ok=True)
    fonts = ROOT / "assets" / "fonts"
    fonts.mkdir(parents=True, exist_ok=True)
    for name in ("BeVietnamPro-Medium.ttf", "BeVietnamPro-SemiBold.ttf", "BeVietnamPro-ExtraBold.ttf", "OFL.txt"):
        shutil.copy2(MIXCOVER / "fonts" / name, fonts / name)

    prov = CloudflareProvider({"width": 1024, "height": 1024})
    for sid, prompt in PROMPTS.items():
        if args.only and sid != args.only:
            continue
        out = out_dir / f"{sid}.png"
        if out.is_file() and not args.force:
            print(f"keep {out} (use --force to redo)")
            continue
        img = prov.generate(ImageRequest(prompt=prompt, seed=args.seed, width=1024, height=1024))
        img.convert("RGB").resize((768, 768)).save(out)
        print(f"saved {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
