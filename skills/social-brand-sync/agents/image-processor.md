# Image Processor — logic reference

Implemented by `scripts/process-images.sh` (ImageMagick 6 or 7). Read this to understand the outputs; run the script rather than composing `convert` commands by hand.

## Steps

1. **Download** `logo_url` (fallback `favicon_url`) and `cover_url` into `originals/`. The file type is detected with `identify`, not trusted from the URL extension.
2. **Normalise the logo** → `originals/logo-square.png` (1024², flattened onto the brand colour, centred, padded — never stretched). Transparent logos therefore never render on black.
3. **Per platform** (from `references/platform-specs.md`):

   | Platform | Profile | Cover |
   |----------|---------|-------|
   | facebook | 360×360 | 851×315 |
   | linkedin | 400×400 | 1584×396 |
   | twitter  | 400×400 | header 1500×500 |
   | tiktok   | 200×200 | — |
   | youtube  | 800×800 | banner 2560×1440 |
   | github   | 512×512 | — |

   Cover from the original when one exists (`resize ^` + centre crop); otherwise **generated**: brand-colour field with the logo centred at a size that stays inside each platform's safe zone. Alpha is removed on every output.
4. **Validate** every file with `identify`; write `images-manifest.json` with actual vs expected size and `ok`. Exit 1 if any image is missing or wrong-sized.

## Overrides

`--logo-url`, `--cover-url`, `--color '#RRGGBB'` bypass `brand-info.json` for that field. No brand colour anywhere → neutral `#1F2937` and a warning.

## Edge cases

- Download blocked / not an image → favicon fallback for the logo; covers are generated.
- Tiny favicon as the only logo → still produced, flagged as low resolution in the log; tell the user.
- YouTube banner safe zone: content centred in 1546×423 — the generated banner keeps the logo at 300 px so it survives the TV/desktop/mobile crops.
