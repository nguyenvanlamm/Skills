# Asset sources — 2D games and Flame

Read at Step 3 when `audit.json → derived.app_type` is `flame_game`, or when the target is game UI inside a normal app.

**Pack coherence matters more here than anywhere else.** An app can survive a mismatched icon. A game cannot survive a Kenney button next to a CraftPix panel next to a hand-drawn HUD — the eye reads three different games on one screen. The `Complete pack` column below is the column that decides the download.

## 2D sprites and UI packs

| Source | URL | Licence | Complete pack | Notes |
|---|---|---|---|---|
| **Kenney** | kenney.nl/assets | **CC0** | ✅ best in class | 40 000+ assets, dozens of internally consistent packs. First choice, no exceptions worth arguing. |
| **OpenGameArt** | opengameart.org | **per-submission** — CC0 / CC BY / CC BY-SA / GPL | ⚠️ mostly loose | Filter by licence in the sidebar. CC BY-SA is viral over derived art; read `licensing.md`. |
| **itch.io** | itch.io/game-assets/free | **per-author, arbitrary** | ✅ some | Large and high quality, but "free" here frequently means *free to download, not to sell with*. Read the readme inside the zip. |
| **CraftPix free** | craftpix.net/freebies | custom — free-with-restrictions | ✅ | Free section forbids redistribution and some resale scenarios. Read the licence page, not the tag. |
| **Game-icons.net** | game-icons.net | **CC BY 3.0** | ✅ 4000+ one style | Attribution mandatory → the game needs a Credits screen. SVG, recolourable, single visual voice. |
| **Glitch** | opengameart.org/content/glitch-sprite-assets-huge-collection (+ github.com/tinyspeck, archived) | **CC0** | ✅ | The entire art library of a shut-down MMO. Distinctive, hand-painted, huge. The original glitchthegame.com page now redirects to slack.com; use the OpenGameArt PNG uploads, since much of the Tiny Speck source is Flash `.fla`. |

### Kenney UI Pack — why it is the default answer for game UI

`kenney.nl/assets/ui-pack` is CC0, ships PNG + a vector source, and — the part that matters — its panels and buttons are drawn to be **9-sliced**. The pack documents the border insets, so a panel scales from a tooltip to a full-screen dialog without the corners smearing. Reproducing that by hand is a day of work; see `integration-flutter.md § 9-slice`.

Companion packs in the same visual voice: *UI Pack: RPG Expansion*, *Game Icons*, *Onscreen Controls*, *Cursor Pack*, *Interface Sounds*. Staying inside the Kenney family is the cheapest way to hit coherence.

## Tilesets and backgrounds

| Source | Licence | Notes |
|---|---|---|
| Kenney (*Platformer Pack*, *Tiny Town*, *Pixel Platformer*) | CC0 | Tiles are power-of-two and grid-aligned — imports into Tiled with no fiddling. |
| itch.io tilesets | per-author | Check the tile size before downloading; a 17px grid is a week of pain. |
| OpenGameArt | per-submission | |

Parallax backgrounds: Kenney *Background Elements*, or itch.io "parallax background" — take a layered set, never a single flattened image, or the depth is gone.

## Low-poly 3D

Relevant only if the project uses `flutter_scene`, `flutter_3d_controller` or a model viewer — Flame is 2D.

| Source | URL | Licence | Formats |
|---|---|---|---|
| **Quaternius** | quaternius.com | CC0 | glTF, FBX, OBJ, Blend |
| **Kay Lousberg** | kaylousberg.com | CC0 | glTF, FBX |
| **Poly Pizza** | poly.pizza | CC0 and CC BY, filterable | glTF, OBJ |
| **Sketchfab** | sketchfab.com — **filter to CC0** | per-model | glTF, USDZ |

Quaternius and Kay Lousberg are both CC0 *and* stylistically consistent across their whole catalogue, which is the rare combination.

## PBR textures

| Source | Licence | Notes |
|---|---|---|
| **ambientCG** | CC0 | Full PBR sets, 1K–8K. Ship 1K on mobile; 4K is desktop-only weight. |
| **Poly Haven** | CC0 | HDRIs, textures, models. |

## Particles and VFX

| Source | Licence | Notes |
|---|---|---|
| **Kenney Particle Pack** | CC0 | Individual particle sprites; drive them from Flame's `ParticleSystemComponent` rather than shipping pre-rendered sheets. |
| **Mixkit VFX** | Mixkit free licence | Video overlays — rarely the right shape for a Flutter game. |

In Flame, prefer generating particles from one small sprite over importing an animation sheet: a 4 KB `smoke.webp` plus `AcceleratedParticle` beats a 600 KB 60-frame sheet, and it responds to game state.

## Audio

| Source | URL | Licence | Notes |
|---|---|---|---|
| **Kenney Audio** | kenney.nl/assets?q=audio | **CC0** | *Interface Sounds*, *UI Audio*, *Impact Sounds*, *Digital Audio*. First choice for SFX. |
| **Freesound** | freesound.org | **per-sound** — CC0 / CC BY / CC BY-NC | Filter by licence. CC BY-NC kills a monetised app. |
| **Mixkit SFX** | mixkit.co/free-sound-effects | Mixkit free licence | No attribution; **no redistribution as a sound pack**. |
| **Pixabay** | pixabay.com/music | Pixabay Content Licence | No attribution required. Cannot be used in a *music-focused* product. |
| **Uppbeat** | uppbeat.io | free tier **requires credit**; no-credit needs a paid plan | Read the trap in `licensing.md`. |

Format targets for a Flutter game. `optimize_flutter.py` produces these, and flags any SFX over 50 KB or music file over 1 MB:

| Kind | Format | Channels | Rate | Budget |
|---|---|---|---|---|
| SFX | AAC `.m4a` 64 kbps — or OGG Vorbis q3 if the game never ships to iOS/macOS | mono | 44.1 kHz | < 50 KB each |
| Music loop | AAC `.m4a` 128 kbps — or OGG Vorbis | source channels (≤ 2) | 44.1 kHz | < 1 MB per minute |

**OGG is silent on iOS.** `flame_audio` plays through `audioplayers`, and on iOS/macOS that means Apple's `AVPlayer`, which has no Vorbis decoder. Kenney and most free SFX packs ship `.ogg`, so a game that sounds right on Android is mute on iPhone. `optimize_flutter.py` picks `.m4a` automatically when the project has an `ios/` or `macos/` folder, and converts any `.ogg` it finds. Update the `FlameAudio.play('…')` paths to match the new filenames.

Mono for SFX is not a compromise — game SFX are positioned by the engine, and stereo doubles the bytes for information the mixer discards.

## Direct download URLs

`fetch_asset.py --url` needs a URL that returns **the file itself**, not a landing page. The patterns below were all fetched successfully on **2026-09-23**. Placeholders are in `<angle brackets>`. Read the licence on the landing page and pass that page as `--source`.

| Source | URL pattern | Returns | Notes |
|---|---|---|---|
| **Kenney** | `https://kenney.nl/media/pages/assets/<pack>/<hash>/kenney_<pack>.zip` | zip + `License.txt` (CC0) | The `<hash>` changes with each pack release, so copy the link from the Download button on `kenney.nl/assets/<pack>`. |
| **Game-icons.net** | `https://game-icons.net/archives/<fg>/<bg>/game-icons.net.svg.zip`, e.g. `000000/transparent` | zip, ~4 200 SVGs, ~4 MB | Files sit at `icons/<fg>/<bg>/1x1/<author>/<name>.svg`, and `icons/license.txt` is included. Use `--strip 4` to keep just `<author>/<name>.svg`. Keep that author folder, because attribution is per author. |
| **Mixkit SFX** | `https://assets.mixkit.co/active_storage/sfx/<id>/<id>.wav` | WAV, full quality | The `<id>` is in the page's download link (`/free-sound-effects/download/<id>/`). **Not** `<id>-preview.mp3`, which is a 35 KB low-bitrate preview; `fetch_asset.py` refuses it and prints the `.wav` URL. |
| **ambientCG** | `https://ambientcg.com/get?file=<AssetId>_<res>-<fmt>.zip`, e.g. `Bricks090_1K-PNG.zip` | zip of PBR maps | The asset ID must exist at that resolution/format; a wrong one is a plain 404. Take `1K` for mobile. |
| **Poly Haven** | Ask the API: `https://api.polyhaven.com/files/<id>` → JSON → `Diffuse.1k.png.url` (or `Normal`, `Rough`, …) | PNG per map | Map file names are not guessable (`…_diffuse_1k.png`), so always read them from the API. |
| **OpenGameArt** | `https://opengameart.org/sites/default/files/<filename>` from the item's "File(s)" list | whatever the uploader attached | The licence is **per submission**. Read it on the item page. |

Filter large packs down to what the screen actually uses:

```bash
# Kenney UI Pack: one colour, 1x sprites + licence. The pack also ships "Double"
# (2x) folders — for Flame, pick one resolution and keep it (no density buckets).
--only 'PNG/Blue/Default/|License\.txt' --flatten

# Game-icons: just the glyphs you need + the licence → lorc/crossed_swords.svg, …, license.txt
--only '/(crossed-swords|shield|health-potion)\.svg$|icons/license\.txt' --strip 4
```

Kenney audio packs (Interface Sounds, UI Audio, …) ship **OGG only**. On a project with `ios/` or `macos/`, run `optimize_flutter.py` afterwards; it converts them to `.m4a`, because AVPlayer cannot play Vorbis (see § Audio).

**Hand download only.** For these sources, download in a browser and import with `--local <file> --source <page>`:

| Source | Why |
|---|---|
| itch.io (including KayKit / Kay Lousberg), CraftPix, Quaternius | The download sits behind a JS button or popup, and the page HTML has no file link |
| Glitch (OpenGameArt) | The link works, but it is a **185 MB `.7z`**. `fetch_asset.py` cannot unpack 7z/rar/tar.gz and refuses them before downloading. Extract by hand, then zip the subset you need |
| Freesound | Needs a login or OAuth token (a plain request gets 401) |
| Pixabay, Uppbeat, Sketchfab | Bot-blocked (403/429) or login-gated |
| Poly Pizza | Not verified for direct links; treat as manual |

## Sprite hygiene, before the assets touch the project

The four rules that turn "the sprites look wrong and I can't say why" into a fixed bug:

1. **Power-of-two dimensions** for atlases (512, 1024, 2048). Non-POT textures are re-padded by some GPUs and silently waste memory.
2. **1–2 px transparent padding around every sprite in an atlas.** Without it, bilinear filtering samples the neighbour and you get a bright seam along the edge — "texture bleeding", and it only shows on some devices, which is why it survives to production.
3. **Panels and buttons need a 9-slice spec** — the four border insets, in pixels, recorded next to the file. Without it the corners stretch. Kenney documents these; for anything else, measure once and write it down.
4. **One atlas per screen or per state**, not one per sprite. Every separate image is a draw-call batch break.

## Verification before proposing anything

Same five questions as `sources-ui.md`, plus three that are specific to games:

6. Is the pack **complete** for what the screen needs — button, panel, slider, checkbox, cursor — or will half the UI come from somewhere else?
7. Is the sprite pitch consistent with the existing art (pixel size, outline weight, palette depth)?
8. For CC BY sources (Game-icons.net, most of OpenGameArt): does the game have a Credits screen yet? If not, that screen is part of this revamp's scope, not a follow-up.
