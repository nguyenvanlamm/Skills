# Changelog

## v1.3.0 — 2026-10-29

The six gaps left after v1.2.0, in the order proposed: measure the guard, see the team's live
apps, compare screenshots, read the build, find templates and forks, read other engines.

### Added
- **Measuring the guard** (`ledger.py`): a `submitted` event keeps a summary of the scan behind
  it — the latest `--mode submit` run for that bundle (scan.py leaves it in the cache) or
  `--scan FILE`, plus `--verdict` for the gate's verdict with J1–J6. `ledger.py stats` sets each
  submission's verdict against App Review's answer, counts every WARN/FAIL row by outcome and
  lists the PASSes that drew a 4.3. Until now the only true positive was the case the guard was
  built from.
- **The team's live apps** (`portfolio.store*`, `market.team_apps`): App Store lookup by
  `--artist-id`, by the team's live bundles and by the seller name (`--account-holder`), cached a
  week per team. FAIL when a live app has this game's name; FAIL/WARN on a near-identical icon
  (the `market` thresholds) or a shared description passage; WARN on ≥ 3 games released in 30
  days. Not looked up (offline, nothing cached) is WARN; looked up and nothing live is SKIP. A
  live smoke test on a public developer (11 apps) found its games and failed a probe named
  after one of them.
- **Screenshots** (`portfolio.screenshots`): any image of an App Store screenshot size, in this
  repo and in the sibling repos, plus the live apps' `screenshotUrls`; a 16×16 dHash (256 bits).
  ≤ 24 FAIL, ≤ 40 WARN. A shared template stays J1's call (J1 now looks at the sets).
- **The build** (`binary` group, `--ipa` for an .ipa, .xcarchive or .app): Info.plist (bundle ID
  and name against the project's), stock-pack markers over every bundled path (package assets
  included), the shipped icon against the bundled images (Xcode's CgBI PNGs decoded) and the
  signature fingerprints over bundled text and the strings compiled into `App.framework/App`.
- **Templates and forks**: `kind: template` packs in `stock-assets.json` — CodeCanyon/Envato,
  Buildbox, SellMyApp/Chupamobile, and Flutter's casual-games template (`markers_min` 3 of its
  screen file names) → `assets.template.*` WARN under 4.2.6. `footprint` reads GitHub's `fork`
  and `template_repository` for the game's repo.
- **Other engines**: Unity (`Assets/`, `ProjectSettings.asset`), Godot (`project.godot`,
  `export_presets.cfg`) and Xcode projects outside `ios/` — their code (C#, GDScript, Swift,
  Objective-C), art, icon, bundle IDs, team ID and name. `portfolio` compares their code too.

### Calibration (2026-10-29)
- Screenshots: 75 pairs of one screenshot exported at 6.3" and 6.9" in the local games differ by
  0–16 of 256 bits; the closest screenshots of two different games, 57 (5th percentile 67).
  An 8×8 hash could not separate them: two games in the shared `appstore-assets` layout
  (caption on top, phone frame) sat 6/64 apart. `skepfield` against its 34 siblings: closest
  60/256, PASS; a sibling's screenshot resized and saved as JPEG: FAIL.
- The 35 Flutter games, v1.2.0 against v1.3.0 on every group but `market` and `footprint`: no
  existing row changed. New rows only — screenshots PASS on 18 and SKIP on 17, no template
  marker anywhere, `portfolio.store` SKIP where no team ID is set (as `account.team` says).
- First-commit authors were considered as a fork signal and dropped: in 5 of the 35 games the
  first commit's author is not the main one — a build tool (buildwizai) or another spelling of
  the same people — and none is a fork; others start under tool names (AIFactory, Devin).

## v1.2.0 — 2026-10-29

Four throwaway games built to probe v1.1.0 passed it with real 4.3 problems: a Suika-like
whose fruits are emoji drawn with `Text('🍉')`, an icon cut from the main sprite kept in
`images/`, one game under four bundle IDs, and a plain sudoku. Each now fails or warns, and
the selftest builds all of them (its new expectations fail 12 times on v1.1.0).

### Added
- `assets.emoji-glyphs`: strings that hold only emoji (`'🍒'`) in code and game data — the
  system emoji font as the art, with no file or credit line for the pack check to find. The
  role comes from the words on the emoji's line and on the lines that open its list or call
  (`core_code_words`, `ui_code_words` in `stock-assets.json`): ≥ 3 core FAIL, else ≥ 3 WARN.
- `signature` and `metadata` read emoji by their Unicode names (`🍉` → watermelon), so a
  progression drawn in emoji counts like one spelled out: the probe matched 10 of Suika's 11
  steps in order.
- `portfolio.bundle-ids`, 4.3(a) to the letter: the bundle IDs of the Xcode project's
  application targets and its `.xcconfig` files; tests, extensions, watch apps and environment
  flavors (`.dev`, `appstaging`, IDs set only in `Debug-dev`) aside. Two or more FAIL.
- `account.same-app`: the ledger holds the same game (same name, or one inside the other) under
  another bundle ID on the team → WARN. `ledger.py check --app`.
- `metadata.saturated-genre` (4.3(b) "variants of existing app categories"): a crowded-category
  label from `generic_names` anywhere in the listing → WARN. J1 now asks what a player can do in
  the game that they cannot do in the others; J1 and J2 FAIL a plain variant of a crowded
  category. 20 labels added (hangman, reversi, trivia, sliding puzzle …);
  `generic_names_headline_only` keeps everyday words ('slots', 'pop it') to the name, subtitle
  and keywords.

### Fixed
- `icon` compared the icon only with `assets/`, and said PASS when it had compared nothing. A
  Flutter app's images are now `assets/` plus the pubspec's asset paths (other projects: the
  usual art folders), and nothing to compare is SKIP. `portfolio` fingerprints the same folders.

### Calibration (35 Flutter games in the projects folder, 2026-10-29)
- Emoji: only `gold_miner` draws emoji as text — 16, on achievements, upgrades and buttons
  (15 ui, 1 unknown) → WARN; its main objects are sprites. Reading emoji by name changed no
  `signature` row on any game.
- Bundle IDs: 32 games build one App Store app and 3 have no iOS bundle ID; the target parse
  drops `RunnerTests` on every one.
- Crowded category: no game's listing names one. Unfiltered, four matched, all wrongly: ASO-note
  tables and quoted words in `skepfield` and `slipchute` (one note keeps "sudoku", "nonogram"
  and "minesweeper" out on purpose), "two free slots" in `yarn_unravel`'s description and
  "Three slots." in Fruit Mischief's promotional text. Listing docs now skip table rows and
  quoted words.
- Fruit Mischief before the rework: the same four FAIL rows, plus `metadata.saturated-genre`
  WARN for "merge fruit" in its subtitle — the crowd it was rejected in. After: unchanged.
- `icon.bundled` goes from PASS to SKIP on 27 games that draw their art in code. `yarn_unravel`'s
  `art/levels/`, which its pubspec does not list (so the binary does not hold it), is no longer
  compared; it would have warned at 14/64.

## v1.1.0 — 2026-10-29

`signature` knew 17 games. It now knows 72 entries covering about 150 hit and trademarked
games, and a new `market` group compares each app with what actually sells on the App Store.

### Added
- `market` group (`build`: name and icon; `submit`: all) and `scripts/market.py`: an index of
  the top 100 free, paid and grossing games in all 19 game charts of us, gb, jp and vn (228
  charts; 6,902 games on 2026-10-29), plus App Store search results for the app's name,
  subtitle and keywords; cached a week in `~/.cache/appstore-spam-guard`. Rows:
  `market.name` (every storefront's name of each game), `market.crowded-name`,
  `market.listing-names` (a charting game's name in the subtitle, keywords or promo text is
  FAIL under 2.3.7; in the description WARN), `market.icon`, `market.wording`.
- `signatures.json`: 55 entries (Royal Match, Toon Blast, Playrix, merge and word hits,
  hyper-casual and .io hits, Nintendo, SEGA, Pokémon, Minecraft, board-game brands …) and 45
  generic genre names. New `markers` field: a hit's characters, items and level names — FAIL
  in the listing; in code FAIL from `markers_fail` distinct ones (Pac-Man's ghosts, Plants vs.
  Zombies' plants, Geometry Dash's levels), else WARN.
- `scan.py --countries`; the selftest gets a fixture index and runs offline.

### Calibration (6,902 charting games, 2026-10-29)
- Icons, all 23.8 million pairs: every pair from different sellers within 6/64 bits and a mean
  colour difference of 12 was one game under a regional publisher → FAIL; up to 10 bits and
  colour 15 → WARN. Nearly flat icons (4×4 luminance spread < 15, the darkest 5 %) hash as
  noise and count only within 2 bits.
- Descriptions, 400 games against all others from different sellers: the longest shared
  passage was ≤ 11 words at the 95th percentile and ≤ 19 at the 99th, the shared share ≤ 10 %
  at the 99th → WARN from 20 words or 10 %, FAIL from 30 words or 20 %. Legal sentences and
  shingles found in 3+ descriptions are ignored.
- Names: a word in 8+ names is a genre word; a name is a brand when one word is rarer and the
  phrase appears in at most 2 descriptions ('Gossip Harbor', 'Sea of Stars' are; 'Boss Fight',
  'Pixel Art', 'There Is No Game' are not). Filler is dropped only at the ends ('Gold Miner
  Classic' = 'gold miner').
- The 35 Flutter games in the projects folder: `market` fails only `gold_miner` (two charting
  "Gold Miner Classic" games); the new fingerprints warn on `declutter` (a "minecraft.jar" in a
  level) and `tile-bloom` ("after Monument Valley 2" in its theme). Fruit Mischief before and
  after the rework: `market` PASS. A fake clone with Block Blast!'s icon and two paragraphs of
  its description: icon FAIL (1/64 bits), wording FAIL (67 words in a row).
- False positives fixed on the way: "color switch" and "Phase 10" in code (now listing-only
  phrases), "clone" inside hyphenated names such as `game-clone-pipeline`, a stop word dropped
  from the middle of a store name ('Sea of Stars' read as 'sea stars'), names matched across
  commas and quotes, and storefronts overwriting each other's names for one app.

### Fixed
- `ownership` missed a copyright statement wrapped onto the next line ("Copyright is
  `2026 Luong NGUYEN`", split across two lines); the rejected Fruit Mischief build is WARN again.

## v1.0.0 — 2026-10-29

First release, built from the 4.3(a) rejection of Fruit Mischief 1.0.0 (3) on 2026-10-23
(`references/case-fruit-mischief.md`).

### Added
- `scripts/scan.py`: modes `design`, `build`, `submit`; groups `signature`, `assets`, `icon`,
  `metadata`, `portfolio`, `footprint`, `ownership`, `account`, `design`. Rows in the
  `{id, group, verdict, summary, evidence, fix}` shape; exit 0 always, 2 on a usage error.
- `scripts/ledger.py`: per-team submission ledger outside every repo; an open 4.3 on a team
  fails every other app's submission to that team.
- `scripts/selftest.py`: builds a Suika-like clone (11 expected verdicts) and an original
  (all clear), with fixture images drawn by the stdlib.
- References: guideline text and the three 4.3(a) variants, resubmission checklist and reply
  template; judgement checks J1–J6; 17 hit fingerprints; 12 stock asset packs; the case study.

### Calibration (real repos, 2026-10-29)
- Fruit Mischief before the rework (`ef76725^`): FAIL on `signature.suika.chain` (9/11 in
  order), `assets.stock.fluent-emoji`, `icon.bundled` (dHash 7/64 to the bundled watermelon) and
  `metadata.suika.phrase`. After the rework (`ef76725`): those four groups PASS (closest bundled
  image to the new icon: 33/64).
- Icon thresholds: FAIL ≤ 10, WARN ≤ 14. An unrelated UI sprite measured 16/64.
- Portfolio: games from `game-clone-pipeline` share 12–21 % of their Dart code with their
  closest sibling (the shared store template and scaffolding); Fruit Mischief shares at most
  10 %. Thresholds stay at WARN ≥ 25 %, FAIL ≥ 50 %. Watch the number as templates grow.
- False positives found and fixed on sibling games: icon matching its own source file
  (`flutter_launcher_icons` inputs are now skipped), a font licence read as the copyright line,
  fruit-named colours read as a progression (out-of-order chains are softer), "clone" inside a
  `.clone/` path, "inspired by Vietnam", and `__TEAM_ID__` placeholders taken as a team ID.
