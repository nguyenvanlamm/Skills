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
| **Glitch** | glitchthegame.com/public-domain-game-art | **CC0** | ✅ | The entire art library of a shut-down MMO. Distinctive, hand-painted, huge. |

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

Format targets for a Flutter game — the numbers `optimize_flutter.py` enforces:

| Kind | Format | Channels | Rate | Budget |
|---|---|---|---|---|
| SFX | OGG Vorbis (q3) | mono | 44.1 kHz | < 50 KB each |
| Music loop | OGG Vorbis | stereo | 44.1 kHz @ ~128 kbps | < 1 MB per minute |

Mono for SFX is not a compromise — game SFX are positioned by the engine, and stereo doubles the bytes for information the mixer discards.

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
