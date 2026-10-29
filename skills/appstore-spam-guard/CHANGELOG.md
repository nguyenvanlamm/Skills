# Changelog

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
