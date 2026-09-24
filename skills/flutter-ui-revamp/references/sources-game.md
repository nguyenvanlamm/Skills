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
| **Pixel Frog** — *Pixel Adventure 1/2* | pixelfrog-assets.itch.io/pixel-adventure-1 | **CC0** (stated on the page) | ✅ | Complete 32px platformer: characters, enemies, terrain, items, UI buttons, 20 FPS animation strips. Do not confuse it with Pixel Frog's *Tiny Swords*, which has its own terms (next row). |
| **Pixel Frog** — *Tiny Swords* (Free Pack) | pixelfrog-assets.itch.io/tiny-swords | custom: personal + commercial, credit optional; **no redistribution, resale or repackaging, even modified** | ✅ | 64px top-down RTS kit: units in 5 faction colours, buildings, terrain, FX, and a UI set whose banners, panels and buttons are drawn to stretch (9-slice them; see `integration-flutter.md § 9-slice`). The page also offers a file named `TS_old version_CC0 Licensed` — the **old** version is CC0; the current Free Pack is not. The Enemy Pack is paid. |
| **Brackeys' Platformer Bundle** | brackeysgames.itch.io/brackeys-platformer-bundle | **CC0** (stated on the page) | ✅ small | Knight, slime, tiles, coins, platforms, plus music, SFX and a pixel font. A complete first-game kit in one 1 MB zip. |
| **Pipoya** — *FREE RPG Tileset 32x32* (and 16x16) | pipoya.itch.io | custom: commercial OK, edit freely; **no redistribution/resale** | ✅ | JRPG outdoor + indoor tiles with Tiled sample maps. |
| **Cainos** — *Pixel Art Top Down – Basic* | cainos.itch.io/pixel-art-top-down-basic | custom: commercial OK, credit optional; **no redistribution/resale** | ✅ | 32px top-down props, grass, stone and wall tilesets with separate shadow sprites. The zip includes plain textures for non-Unity engines. |
| **0x72** — *16x16 DungeonTileset II* | 0x72.itch.io/dungeontileset-ii | assets **CC0**, code MIT | ✅ | The standard free roguelike tileset, with heroes, monsters, weapons and UI hearts. |
| **Screaming Brain Studios** | screamingbrainstudios.itch.io | **CC0** (all assets, per the studio page) | ✅ per pack | Isometric tiles, procedural planets, space backgrounds, textures. |
| **itch.io, CC0 filter** | itch.io/game-assets/free/tag-cc0 | CC0 as tagged, **still confirm on the page** | varies | The tag is set by the author and is not audited. It turns itch.io from "read every readme" into "confirm one line". |
| **Open Duelyst** | github.com/open-duelyst/duelyst | **CC0** | ✅ huge | A shipped CCG's entire art drop: 600+ animated pixel-art units (idle/run/attack/death), VFX, UI, music and SFX, all under `app/resources/`. `Jordyfel/duelyst-animated-sprites-godot` repacks the sheets with parsed frame data — also CC0. |
| **Superpowers asset packs** | github.com/sparklinlabs/superpowers-asset-packs | **CC0** (`LICENSE.txt` at repo root) | ✅ per pack | ninja-adventure, space-shooter, medieval-fantasy, rpg-battle-system, top-down-shooter, western-fps-2d, prehistoric-platformer, backgrounds, plus 3 low-poly 3D packs. Fetchable from GitHub (below). |
| **pixel-boy — Ninja Adventure** | pixel-boy.itch.io/ninja-adventure-asset-pack | **CC0** | ✅ | 16×16 top-down action pack: characters, tileset, UI, icons, SFX. Continues the superpowers `ninja-adventure` pack. **Other pixel-boy packs use a custom "commercial OK, no resell" licence — check each item page.** |
| **GameArt2D freebies** | gameart2d.com/freebies.html | **CC0** (stated on the licence page) | ✅ | Tilesets, GUI packs and characters with vector sources (AI/EPS/CDR) plus PNG. Casual/mobile-flavoured. |
| **Lost Garden** | lostgarden.home.blog/tag/free-game-graphics | **CC BY 3.0** | ⚠️ per collection | Daniel Cook's classic prototyping sets (Small World, PlanetCute, Space Cute). Visible credit required, in the form the licence page gives. One clause is unusual: **do not use the art in a clone of one of his commercial games.** |
| **Ansimuz** | ansimuz.itch.io | custom: commercial OK; **no resell/redistribute, no AI/NFT, no engine tools** | ⚠️ varies | Large free pixel-art catalogue (top-down and side-view). Some packs are tagged CC0 on their own pages — the item page wins. |

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

Palettes for recolouring work: **lospec.com/palette-list** collects community-submitted palettes (Lospec states they are free to use). A palette is a colour direction, not an asset — record the palette name in CREDITS if one is used.

## Pixel fonts

| Font | Source | Licence | Notes |
|---|---|---|---|
| **Press Start 2P** | Google Fonts | OFL | The default arcade pixel face; Latin only. |
| **DotGothic16** | Google Fonts | OFL | Japanese pixel font — the only sensible choice for a pixel-art game with JP copy. |
| **Fusion Pixel** | github.com/TakWolf/fusion-pixel-font | OFL | CJK pixel font at 8/10/12 px; releases ship OTF zips (below). |
| **Cubic 11** | github.com/ACh-K/Cubic-11 | OFL | Traditional-Chinese pixel font; TTF at `fonts/ttf/Cubic_11.ttf`. |
| **Kenney Fonts** | kenney.nl/assets/kenney-fonts | **CC0** | 12 TTFs (Future, Pixel, Mini, High, Rocket, Blocks, with Square/Narrow/Mono variants) in the same voice as the Kenney UI packs. The obvious pairing for a Kenney-skinned game. Direct zip below. |
| **itch.io pixel fonts** | itch.io | per-author | m6x11, m5x7 (Daniel Linssen), VCR OSD Mono and friends — read each page. |

## Low-poly 3D

Relevant only if the project uses `flutter_scene`, `flutter_3d_controller` or a model viewer — Flame is 2D.

| Source | URL | Licence | Formats |
|---|---|---|---|
| **Quaternius** | quaternius.com | CC0 | glTF, FBX, OBJ, Blend |
| **Kay Lousberg** | kaylousberg.com | CC0 | glTF, FBX |
| **Poly Pizza** | poly.pizza | CC0 and CC BY, filterable | glTF, OBJ |
| **Sketchfab** | sketchfab.com — **filter to CC0** | per-model | glTF, USDZ |
| **market.pmnd.rs** | market.pmnd.rs | **CC0** | optimized GLB, HDRI, textures — direct CDN links on each asset page |
| **Smithsonian 3D** | 3d.si.edu | **CC0** when filtered to `media_usage:CC0` | glTF, OBJ, USD — 3 000+ museum scans; unfiltered models have usage conditions |
| **Polytope Studio free packs** | Unity Asset Store / Fab listings | store EULA — usable in end products, **no raw redistribution** | `.unitypackage` — extract by hand (it is a gzipped tar of per-GUID files) |
| **Mixamo** | mixamo.com | Adobe royalty-free for projects, games included; **no raw-file redistribution, no ML training** | FBX, glTF — rigged characters + a large animation library; Adobe ID needed |
| **TurboSquid / CGTrader / Free3D free sections** | per-marketplace | per-model royalty-free — read the model page | account required |
| **BlendSwap** | blendswap.com | per file — CC0 through CC BY-SA | `.blend` — login required |

Quaternius and Kay Lousberg are both CC0 *and* stylistically consistent across their whole catalogue, which is the rare combination.

## PBR textures

| Source | Licence | Notes |
|---|---|---|
| **ambientCG** | CC0 | Full PBR sets, 1K–8K. Ship 1K on mobile; 4K is desktop-only weight. |
| **Poly Haven** | CC0 | HDRIs, textures, models. |
| **CG Bookcase** | CC0 | Full PBR sets, 1K–4K, with all map types. |
| **3Dassets.one** | **search engine** — licence-filterable | Indexes ambientCG, Poly Haven, CG Bookcase, ShareTextures, Texture Can, PBRPX, NoEmotion HDRs and more. Search here first, filter to CC0, then fetch from the creator's site. |
| **ShareTextures** | custom licence — commercial OK, **no redistribution** | Free account needed. |
| **Textures.com free** | restrictive own licence — free daily credits, no redistribution, no OSS asset packs | Last resort; prefer the CC0 sites. |

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
| **Juhani Junkala** — *512 Sound Effects (8-bit style)* | opengameart.org/content/512-sound-effects-8-bit-style | **CC0** | 512 retro SFX in categorised folders (coins, jumps, explosions, menus). One 20 MB zip with a direct link (below). |
| **Kevin MacLeod / incompetech** | incompetech.com | **CC BY 4.0** for the free tier | Large library of music loops. The free tier needs an on-screen credit in the exact form the site gives; a paid licence removes it. The download pages are JS, so download by hand. |
| **jsfxr** | sfxr.me (github.com/chr15m/jsfxr) | tool: Unlicense | A generator, not a library. You synthesise 8-bit SFX in the browser and export WAV. The output is your own work, so there is no third-party licence to track. Record it in CREDITS.md as "generated with jsfxr". |
| **Sonniss GDC Game Audio Bundle** | sonniss.com/gameaudiogdc | sonniss.com/gdc-bundle-license: royalty-free, commercial, no attribution; **no resale as raw files**; no AI/ML training | Several GB of professional SFX each year (7.47 GB in 2026; over 200 GB in the archive). Hand download only: the site returns 403 to scripts, and the bundle is too large for `fetch_asset.py`. Take the few files you need. |
| **gamesounds.xyz** | gamesounds.xyz | **CC0 packs** (Kenney's Sound Pack, Shapeforms and friends) | A browseable directory index of royalty-free game-audio packs, with direct file links — fetchable (below). Every pack folder carries its `readme.txt`; fetch it, the licence lives there. |
| **ZapSplat** | zapsplat.com | Standard License — free tier requires **visible credit** (premium removes it) | Huge SFX/music library. Free accounts get MP3 only and a download cap. The credit must be inside the project — a Credits screen line. |
| **SoundImage (Eric Matyas)** | soundimage.org | custom attribution licence — **credit inside the game is mandatory**, e.g. `Music by Eric Matyas — www.soundimage.org` | Thousands of music tracks and SFX in OGG + MP3, plus 4 000 images. Non-attribution licences can be bought per track. |
| **99Sounds** | 99sounds.org | royalty-free, no attribution | Small catalogue of themed packs (cinematic, drones, retro). |
| **Sample Focus** | samplefocus.com | per sample — "Standard Royalty-Free" or CC0, tagged on the page | Login needed to download. |
| **Free Music Archive** | freemusicarchive.org | **per-track CC** — much of it NC or ND | Use the built-in licence filter ("commercial allowed", "remix allowed") and read the track page anyway. |
| **Musopen** | musopen.org | per recording — filter to Public Domain / CC0 | Classical recordings and sheet music; account needed. |
| **ende.app** (was filmmusic.io) | ende.app | **CC BY 4.0** — the author explicitly makes attribution voluntary | ~1 300 tracks by Sascha Ende, video game and film oriented. |
| **Audionautix** | audionautix.com | **CC BY** | Jason Shaw's genre-sorted loops. |
| **Fesliyan Studios** | fesliyanstudios.com | free **with attribution**; a paid licence removes it | Casual/mobile-friendly loops. |
| **DOVA-SYNDROME** | dova-s.jp | custom free licence — commercial use allowed (Japanese terms page) | Enormous JP-style BGM library. The terms are in Japanese; budget the translation or pick another source. |
| **Abstraction / Tallbeard Studios** — *FREE Music Loop Bundle* | tallbeard.itch.io/music-loop-bundle | **CC0** | 200+ seamless game-music loops (chiptune, ambient, upbeat), split into quarterly zips of 30–150 MB. Credit is optional ("Abstraction"). The authors ask, but the licence does not require, that the music not be used for NFT/AI projects or resold unmodified. |
| **Scott Buckley** | scottbuckley.com.au/library | **CC BY 4.0** | Orchestral, cinematic and ambient tracks with a genre/mood search. Needs an on-screen credit. Without it, his YouTube Content ID can flag the app's trailer. |
| **ChipTone** | sfbgames.itch.io/chiptone | tool is free; **sounds you make are CC0** (stated on the page) | Browser/desktop SFX generator by SFB Games, a step up from sfxr/jsfxr. Record it as "generated with ChipTone (CC0)". |
| **Bfxr** | bfxr.net (github.com/increpare/bfxr2) | tool **MIT**; output is your own work | The sfxr descendant with more synth parameters and a footstep generator. Same CREDITS treatment as jsfxr. |

**Not allowed: BBC Sound Effects.** The 16 000 BBC archive sounds are under the RemArc licence, which permits only non-commercial, personal, research or formal-education use. Any monetised or ad-funded app needs a paid licence from Pro Sound Effects. They appear in many "free SFX" lists, so reject them explicitly.

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
| **OpenGameArt** | `https://opengameart.org/sites/default/files/<filename>` from the item's "File(s)" list | whatever the uploader attached | The licence is **per submission**. Read it on the item page. The server is slow: a 20 MB zip takes about a minute. |
| **Juhani Junkala 512 SFX** | `https://opengameart.org/sites/default/files/The%20Essential%20Retro%20Video%20Game%20Sound%20Effects%20Collection%20%5B512%20sounds%5D.zip` | zip, 20 MB of WAV | There is no licence file inside; the CC0 is stated on the item page, so pass that page as `--source`. Filter by folder, e.g. `--only '(?i)/coins/' --flatten`. |
| **Pixelarticons** (pixel UI icons) | `https://raw.githubusercontent.com/halfmage/pixelarticons/master/svg/<name>.svg` | SVG | MIT. Matches pixel-art HUDs better than any app icon set. |
| **Open Duelyst** | `https://raw.githubusercontent.com/open-duelyst/duelyst/main/app/resources/<dir>/<file>` | PNG + `.plist` frame data, audio | 45 resource dirs — list them with `api.github.com/repos/open-duelyst/duelyst/contents/app/resources/<dir>`. A unit's sheet pairs a `.png` with a `.plist` of frame rects; both are needed. |
| **Superpowers packs** | `https://raw.githubusercontent.com/sparklinlabs/superpowers-asset-packs/master/<pack>/<path>` | PNG, audio | Packs: `ninja-adventure`, `space-shooter`, `medieval-fantasy`, `rpg-battle-system`, `top-down-shooter`, `western-fps-2d`, `prehistoric-platformer`, `backgrounds`. `LICENSE.txt` (CC0) sits at the repo root — fetch it once. |
| **gamesounds.xyz** | `https://gamesounds.xyz/<Pack%20Name>/<file>` | WAV / OGG / MP3 | Browseable directory index. Every pack folder has a `readme.txt` stating the licence — fetch it and keep it next to the sounds. |
| **Fusion Pixel** | `https://github.com/TakWolf/fusion-pixel-font/releases/download/<tag>/fusion-pixel-font-<size>px-<variant>-otf-v<tag>.zip` | OTF zip | Resolve `<tag>` and the asset name via `api.github.com/repos/TakWolf/fusion-pixel-font/releases/latest`. `<size>` is 8/10/12, `<variant>` e.g. `monospaced`. OFL. |
| **Cubic 11** | `https://raw.githubusercontent.com/ACh-K/Cubic-11/master/fonts/ttf/Cubic_11.ttf` | TTF | OFL — `OFL.txt` sits at the repo root. |
| **Kenney Fonts** | `https://kenney.nl/media/pages/assets/kenney-fonts/8d5435c213-1677661710/kenney_kenney-fonts.zip` | zip, 57 KB: `Fonts/*.ttf` + `License.txt` | CC0. `--only 'Kenney Future\.ttf$\|License\.txt' --flatten` gives `kenney_future.ttf` + `license.txt`. The hash changes if Kenney re-uploads the pack; if it 404s, copy the link from the Download button. *(fetched through `fetch_asset.py` on 2026-09-24)* |
| **SoundImage** | the direct `.ogg` / `.mp3` link on each track page | audio | Credit inside the app is mandatory. |
| **Openverse API** | `https://api.openverse.org/v1/images/?q=<q>&license_type=commercial` and `/v1/audio/?…` | JSON → `url` per result | Search engine, not a source — verify each result's licence on its own page. |
| **Wikimedia Commons** | `https://upload.wikimedia.org/wikipedia/commons/<h>/<hh>/<File>` | original file | Copy the "Original file" link from the file page. Licence is per file. |

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
| itch.io (including KayKit / Kay Lousberg, pixel-boy, Ansimuz), CraftPix, Quaternius, GameArt2D | The download sits behind a JS button or popup, and the page HTML has no file link |
| Glitch (OpenGameArt) | The link works, but it is a **185 MB `.7z`**. `fetch_asset.py` cannot unpack 7z/rar/tar.gz and refuses them before downloading. Extract by hand, then zip the subset you need |
| Freesound, Sample Focus, Musopen, BlendSwap | Needs a login or OAuth token (a plain request gets 401) |
| Pixabay, Uppbeat, Sketchfab | Bot-blocked (403/429) or login-gated |
| Poly Pizza | Its API (`api.poly.pizza`) returns 401 without an API key. Download models from the site |
| Pixel Frog (incl. Tiny Swords), 0x72, Screaming Brain Studios, Brackeys, Pipoya, Cainos, Tallbeard | itch.io download button (JS). Tallbeard's zips are 30–150 MB each, so take one quarter, not the whole bundle |
| Scott Buckley | Per-track download page |
| ChipTone, Bfxr, jsfxr | Generators: you export WAV from the tool, then import with `--local` |
| incompetech, Sonniss | JS download page / 403 to scripts |
| Lost Garden | Zip links scattered across blog posts — copy each file link from the post |
| ZapSplat, Free Music Archive | Login required, plus download caps on free tiers |
| Mixamo | Adobe ID + export flow in the browser |
| Polytope Studio, TurboSquid, CGTrader, Free3D | Store checkout / account even for $0 items; `.unitypackage` files need manual unpacking |
| ShareTextures, Textures.com | Account required; Textures.com also caps free daily downloads |
| Smithsonian 3D | Per-object download UI assembles multiple files |
| 99Sounds, Audionautix, ende.app, Fesliyan, DOVA-SYNDROME | Site download buttons; some route through JS or a second page |
| CG Bookcase | Download button per texture, no login — but the file URL is not published in a stable pattern |
| 3Dassets.one, Lospec | These are indexes, not hosts — they send you to the creator's site |

## Sprite hygiene, before the assets touch the project

The four rules that turn "the sprites look wrong and I can't say why" into a fixed bug:

1. **Power-of-two dimensions** for atlases (512, 1024, 2048). Non-POT textures are re-padded by some GPUs and silently waste memory.
2. **1–2 px transparent padding around every sprite in an atlas.** Without it, bilinear filtering samples the neighbour and you get a bright seam along the edge — "texture bleeding", and it only shows on some devices, which is why it survives to production.
3. **Panels and buttons need a 9-slice spec** — the four border insets, in pixels, recorded next to the file. Without it the corners stretch. Kenney documents these; for anything else, measure once and write it down.
4. **One atlas per screen or per state**, not one per sprite. Every separate image is a draw-call batch break.

## Checked and rejected

Game-asset lists recycle the same bad sources. Each of these was checked on **2026-09-23** and fails for the stated reason. Do not propose them without new evidence.

| Source | Why not |
|---|---|
| **The Spriters Resource / Textures Resource / Models Resource / Sounds Resource** (vg-resource) | Ripped commercial-game files, hosted "for reference and educational purposes". The uploader cannot grant rights the publisher owns; shipping them is plain infringement, placeholder or not. |
| **RPG Maker RTP and official DLC** | The KADOKAWA licence allows the assets only inside games built with the RPG Maker engine. A Flutter app is not one, and "it is just a placeholder" does not change that. |
| **ThreeDScans** | Beautiful museum scans, but the site publishes **no licence text** — only interviews in which the author disclaims copyright. No instrument means the default: all-rights-reserved. |
| **System fonts as pixel fonts** (W95FA, MS Sans Serif, Chicago, San Francisco) | Proprietary OS fonts; bundling them breaches the OS licence. Use Fusion Pixel, Cubic 11 or DotGothic16 instead. |
| **Orange Free Sounds** | Most files are CC BY-NC — unusable in a monetised or ad-funded app. |
| **"Free SFX pack" videos on YouTube/TikTok** | Unverifiable provenance — frequently re-uploads of copyrighted libraries. No licence page, no deal. |
| **Sprout Lands** (Cup Nooble) — free Basic Pack | *Checked 2026-09-24.* The free tier is **non-commercial only**. Commercial use needs the premium pack (≥ $3.99). It is one of the most recommended "free" farming packs, so reject it explicitly for any monetised game. |
| **FreePD** | *Checked 2026-09-24.* freepd.com shut down in 2025 ("permanently closed"). Old mirrors of its public-domain music have no provenance you can cite, so use the Tallbeard CC0 bundle instead. |
| **Universal LPC spritesheet and most LPC art** | CC BY-SA 3.0 and/or GPL — the share-alike and attribution load is real work, and the base LPC licence blocks many commercial uses. Read the licence tree before using anything tagged LPC on OpenGameArt. |

## Verification before proposing anything

Same five questions as `sources-ui.md`, plus three that are specific to games:

6. Is the pack **complete** for what the screen needs — button, panel, slider, checkbox, cursor — or will half the UI come from somewhere else?
7. Is the sprite pitch consistent with the existing art (pixel size, outline weight, palette depth)?
8. For CC BY sources (Game-icons.net, most of OpenGameArt): does the game have a Credits screen yet? If not, that screen is part of this revamp's scope, not a follow-up.
