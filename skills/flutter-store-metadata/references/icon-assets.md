# Icon and feature graphic

## App icon

Two separate deliverables, often confused:

| Deliverable | Spec | Where it goes |
|-------------|------|---------------|
| Play listing icon | 512×512, 32-bit PNG (alpha allowed) | Uploaded in Console; keep at `store-metadata/icon/icon-512.png` |
| Launcher icon | Adaptive: 108×108 dp layers, 66 dp safe zone | `android/app/src/main/res/mipmap-*` in the project |

### Generate with flutter_launcher_icons

Use this rather than resizing a square with ImageMagick. Since Android 8 the launcher applies its own mask to an adaptive icon's foreground/background layers; a flat square dropped into `mipmap-*` gets cropped or letterboxed, and creating an empty `mipmap-anydpi-v26/` directory without the XML inside does nothing at all.

```yaml
dev_dependencies:
  flutter_launcher_icons: ^0.14.1

flutter_launcher_icons:
  android: true
  image_path: "store-metadata/icon/icon-512.png"
  adaptive_icon_background: "#FFFFFF"
  adaptive_icon_foreground: "store-metadata/icon/icon-foreground.png"
  adaptive_icon_monochrome: "store-metadata/icon/icon-monochrome.png"
  min_sdk_android: 23
```

```bash
flutter pub get && dart run flutter_launcher_icons
```

This writes every density, the `mipmap-anydpi-v26/ic_launcher.xml`, and the round variant.

- **Foreground layer**: artwork must sit inside the centre 66 of 108 dp — roughly the middle 61%. Anything outside can be clipped by a circular or squircle mask.
- **Monochrome layer**: a single-colour silhouette used by Android 13+ themed icons. Optional, but its absence is visible on modern launchers.

Source artwork: if the project has no icon yet, the `logo-designer` skill produces the variants this config expects.

### Verify

```bash
identify -format '%wx%h %[channels]\n' store-metadata/icon/icon-512.png   # expect 512x512
ls android/app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml             # must exist
```

An icon that is not exactly 512×512 is rejected at upload.

## Feature graphic

**Required for every listing.** Play will not publish a store listing without one — it appears at the top of the listing page and in promotional placements.

| Property | Rule |
|----------|------|
| Size | Exactly 1024×500 |
| Format | JPEG or 24-bit PNG |
| Alpha | **Not allowed** — a PNG with an alpha channel is rejected |

Design constraints worth passing to the user: the centre is cropped on some surfaces, so keep the logo and any text within the middle ~50%; and it must not look like a screenshot or contain a fake "Install" button — both read as deceptive.

Compose it from the icon and app name, then flatten the alpha:

```bash
magick -size 1024x500 gradient:'#4F46E5-#7C3AED' \
  \( store-metadata/icon/icon-512.png -resize 200x200 \) -gravity center -composite \
  -alpha remove -alpha off \
  store-metadata/icon/feature-graphic.png
```

On ImageMagick 6 the command is `convert` instead of `magick`. Check which is installed — `magick -version || convert -version` — rather than assuming.

Verify:

```bash
identify -format '%wx%h %[channels]\n' store-metadata/icon/feature-graphic.png
# expect: 1024x500 srgb    (NOT srgba — an "a" means alpha is still present)
```
