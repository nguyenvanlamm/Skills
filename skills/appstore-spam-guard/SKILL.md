---
name: appstore-spam-guard
description: >-
  Catch App Store Guideline 4.3 (spam) and 4.1 (copycat) risks before an iOS game is submitted:
  a hit's progression, name or wording in code, build or listing; a name, icon or text matching
  ~7,000 charting games; stock or emoji art for main objects; an icon cut from a sprite; a plain
  variant of a crowded genre; a twist hidden past 30 seconds; one game under several bundle IDs;
  code, art, icons or screenshots shared with the team's games; templates and forks; stale
  pages; an IP owner who isn't the publisher; an open 4.3 on the team. Flutter, Unity, Godot or
  Xcode. Scripted PASS/WARN/FAIL scans with fixes, six judgement checks, a team ledger scored
  against App Review's answers. Use before every submission, at a clone pipeline's design, art
  and submit gates, after a 4.3 rejection, or when asked "check 4.3", "spam check", "kiểm tra
  4.3", "có bị reject spam không". Don't use for other guidelines (appstore-review-checker),
  Google Play (flutter-store-compliance), or name and trademark checks (brand-name-checker).
license: MIT
effort: medium
capabilities:
  - app-store
  - audit
metadata:
  version: 1.3.0
---

# appstore-spam-guard

Fruit Mischief, a Suika-like with a real roguelike twist, was rejected under 4.3(a) and its
account put on Extended Review. Its own pre-submission audit had called 4.3 "reviewer judgement,
can't be checked from code". Most of it can: run on the rejected build, this skill fails on the
four things the reviewer saw first (`references/case-fruit-mischief.md`).

## Core principle

> **4.3 is decided in the first minute and across the whole account.** What a reviewer sees
> first — the art, the icon, the opening screen, the listing — and what the developer's other
> apps look like are evidence, not opinion. Measure them before submitting; never wave 4.3
> through as "depends on the reviewer".

## Verdict vocabulary

| Verdict | Meaning | Effect |
|---|---|---|
| `PASS` | checked, no 4.3 signal | — |
| `WARN` | a signal, or not verifiable here | the human decides, with the evidence |
| `FAIL` | the pattern App Review rejects | **submission blocked** |
| `SKIP` | does not apply (no listing yet, no URLs) | never a pass; say why |

Overall is FAIL if any check fails, else WARN if any warns, else PASS. A missing tool (Pillow,
the network) is WARN, never PASS.

## Modes

| Mode | When | Groups |
|---|---|---|
| `design` | the design doc is written, before any art (a clone pipeline's S2) | `design`: the hit's progression or stock art in our design's "Ours" column |
| `build` | the real art and icon are in (S4) | `signature`, `assets`, `icon`, `market` (name and icon) |
| `submit` | before **every** submission and resubmission (S8) | all nine below, and `binary` with `--ipa` |

| Group | Looks at | FAIL when |
|---|---|---|
| `signature` | code, localisation, game data (emoji read by their Unicode names: 🍉 is watermelon) vs `references/signatures.json`: 72 entries, about 150 hit and trademarked games | a hit's progression in order (Suika: ≥6 of 11 steps), or its characters, items or level names (`markers`) |
| `assets` | credits, README, strings, file names vs `references/stock-assets.json`; emoji drawn as text in code and game data | an emoji/art pack, or ≥ 3 emoji drawn as text, draws the main objects (WARN: emoji only in UI; a game template — CodeCanyon, Buildbox, Flutter's games template — under 4.2.6) |
| `icon` | the 1024 icon vs every bundled image: `assets/` and the pubspec's asset paths, Unity's `Assets/`, a Godot or Xcode project's art (dHash; needs Pillow; SKIP when there is none) | the icon reproduces a bundled sprite (distance ≤ 10/64) |
| `metadata` | name, subtitle, keywords, description, promo text, listing docs | the listing names the hit or uses its signature wording or names (WARN: a crowded category under 4.3(b), for J1 and J2 to judge) |
| `market` | the live App Store: top 100 free, paid and grossing of all 19 game charts in us, gb, jp, vn (about 7,000 games, every storefront's name) plus App Store search for our name, subtitle and keywords | the name is a charting game's; the subtitle, keywords or promo text use one's name; the icon is near-identical to one (≤ 6/64 bits, colour ≤ 12); the description repeats one's (≥ 30 words in a row or ≥ 20 %) |
| `portfolio` | the bundle IDs of the app targets (Xcode, Unity, Godot); sibling app repos in the parent folder; the team's live apps (App Store lookup by `--artist-id`, the seller name or a live bundle); store screenshots (any file of an App Store screenshot size) | the project builds ≥ 2 App Store apps (4.3(a); environment flavors, tests and extensions aside); ≥ 50 % of our code, or the icon or main art, shared with a sibling; a live app of the team has our name, a near-identical icon or our description; a store screenshot is one of another own game's (16×16 dHash ≤ 24/256) — WARN: a burst of ≥ 3 games in 30 days |
| `footprint` | privacy/support/marketing pages; GitHub repos they link | — (WARN: page down, old name, public source, a fork or a template repo) |
| `ownership` | copyright vs account holder (or bundle-id owner) | — (WARN: 5.2.1, state the authorization) |
| `account` | the ledger for the Apple team | the team has an open 4.3 on another app (WARN: the same game already on the team under another bundle ID) |
| `binary` | with `--ipa`: the .ipa, .xcarchive or .app to upload — Info.plist, every bundled file (package assets too), the shipped icon, the text compiled into the Dart code | a stock pack draws main objects; the shipped icon reproduces a bundled image; a hit's progression or names in the build (WARN: another bundle ID or name than the project's) |

## Workflow

### Step 1 — Run the scan

```bash
python3 <skill-dir>/scripts/scan.py --project . --mode submit \
  --team <APPLE_TEAM_ID> --account-holder "<seller name>" --artist-id <developer id> \
  --ipa <build>.ipa --out spam-guard.json
```

Optional: `--listing <files or folder>` (default: JSON/TXT in `store/`, `docs/store/`,
`fastlane/metadata/`, `store-metadata/`, plus `docs/*app-store*.md`, `*listing*.md`),
`--portfolio <folder of your other apps>` (default: the project's parent), `--url <privacy>
<support>` (default: found in `docs/store/`, `store/`, README), `--old-name "<earlier name>"`
(added to the names found in the bundle's git history), `--countries us,gb,jp,vn` (the
storefronts `market` reads), `--offline`, `--groups a,b`. The team comes from `--team`,
`$TEAM_ID`, the Xcode project, `ExportOptions.plist` or the engine's settings, in that order.
`--artist-id` is the number in the team's App Store developer page (`…/developer/…/id<N>`);
without it the live apps are found from the seller name and the team's live bundles, and the
ids found are cached for the team. `--ipa` takes the build that will be uploaded — on the Mac,
right after the archive — and adds the `binary` group: what App Review compares is the build.

`market` fetches the charts on its first run (228 charts, about 3 minutes with the icons), then
reuses them for a week from `~/.cache/appstore-spam-guard` (`$APPSTORE_SPAM_GUARD_CACHE`); its
searches go at Apple's pace of about 20 a minute. `scripts/market.py refresh | search <terms> |
stats` manages the cache by hand. `--offline` uses the cache as it is; no cache is WARN.

Stdlib Python; Pillow adds the icon comparisons. Where a repo requires a virtualenv for Python,
activate it first. The rows are already in report shape: **copy them, do not re-derive them.**

### Step 2 — Judgement checks

Read `references/checks.md` and run what the scan cannot: J1 fresh-eyes comparison (fresh
subagent; add the closest store icons the `market` rows name and the screenshot sets the
`portfolio.screenshots` row names), J2 the own mechanic in the
first 30 seconds, J3 the icon's subject, J4 the listing's
voice, J5 owner vs publisher, J6 the account's pace. `submit` runs all six; `build` runs J1 and
J3; `design` runs J1 on the mockups. Each gives PASS/WARN/FAIL with its evidence.

### Step 3 — Report and gate

Write `spam-guard-report.md` beside the JSON: the overall verdict, one table with the script
rows and the J rows, then the fixes in order — FAIL first. **Any FAIL blocks the submission**
(and the pipeline gate that called this skill). WARN rows go to the human with their evidence;
the human accepts or fixes each.

### Step 4 — Record the submission and the answer

The account is what 4.3 punishes, so the ledger lives outside every repo
(`~/.config/appstore-spam-guard/ledger.json`, or `$APPSTORE_SPAM_GUARD_LEDGER`):

`submitted` keeps the scan with the submission: the latest `--mode submit` run for that bundle
(under 14 days), or `--scan spam-guard.json`; add `--verdict` when J1–J6 changed the verdict.

```bash
python3 <skill-dir>/scripts/ledger.py record --team <T> --app "<App>" --bundle <id> --event submitted
python3 <skill-dir>/scripts/ledger.py record --team <T> --app "<App>" --bundle <id> --event approved
python3 <skill-dir>/scripts/ledger.py record --team <T> --app "<App>" --bundle <id> --event rejected \
  --guideline "4.3(a)" --extended-review --note "<what the message named>"
```

`ledger.py check --team <T> --bundle <id> --app "<App>"` shows what the `account` group sees;
`show` prints the ledger. `ledger.py stats` sets every scanned submission against App Review's
answer — verdict by outcome, each WARN/FAIL row by outcome, and the PASSes that drew a 4.3. Record
the team's earlier submissions too (`--date`); after 10–20 answers it says whether the guard is
enough and which WARN should become a FAIL.

## After a 4.3 rejection

1. Record it (above). From now on every other submission to that team is FAIL until this app is
   approved or withdrawn.
2. Read `references/guideline-4.3.md`: the variants, Extended Review, the resubmission
   checklist, when an appeal is worth it, and the reply template.
3. Run `--mode submit` on the rejected build to locate the causes; fix until no FAIL remains and
   J2 and J3 pass; resubmit **once**, with the reply in the Resolution Center.

## Extending

- A new hit: add it to `references/signatures.json` — aliases only when sure of the name and
  it is no everyday phrase, phrases only that game would use, its characters, items and level
  names as `markers` (each a list of spellings, counted once; `markers_fail` distinct ones fail
  in code), the progression as `chain` when it has one. A game that charts or shows up in
  search needs no entry for its name, icon or description: `market` already compares them.
- More storefronts: `--countries us,gb,jp,vn,kr,de,br` (each adds 57 charts to the index).
- A new asset pack: add its credit and file-name markers to `references/stock-assets.json`.
- A crowded category: add its label to `generic_names` in `references/signatures.json`; a label
  that is also an everyday word in a sentence ('slots') goes in `generic_names_headline_only` too.
- A game template: a `kind: template` entry in `references/stock-assets.json`, with
  `markers_min` when its file names are common one by one.
- Then `python3 scripts/selftest.py` — it builds a clone, an original, the blind-spot projects,
  three engines and an .ipa, and must still pass.

## Limits

- Apple does not publish how it compares apps; the groups are proxies for what a reviewer sees
  and what a diff of two bundles shows. A PASS lowers the risk; it does not promise approval.
- The ledger knows only what was recorded; a match against a terminated account cannot be
  checked from here — `footprint` (forks, public source) and the template markers only reduce
  the exposure. A public repo the game was copied from without a fork is not found.
- Code similarity reads Dart under `lib/` for Flutter, and C#, GDScript, Swift and Objective-C
  for the other engines. Screenshots are compared image by image (a reused one fails); a shared
  template across your games is J1's call — the hash cannot tell it from two dark screens.
  App previews (video) are not compared. `binary` reads a build's files and text, not its
  machine code; PNGs Xcode crushed (CgBI) are decoded for the icon.
- `market` sees the top 100 of each chart and what search returns for the app's own words —
  about 7,000 games, not the million below them. It catches a taken name, a copied icon and
  copied text; a similar style is J1's job. Names that are plain English or genre words
  ('Boss Fight', 'Pixel Art', 'Block Blast') do not count as brands there; the curated list
  covers the famous ones.
- Emoji count when a string (or a YAML/CSV value) holds only emoji; emoji painted into image
  files are the pack and icon checks' job. A crowded category stays WARN: only J1 and J2 can
  tell a meaningfully different game from a variant. Bundle IDs come from the Xcode project's
  app targets and its `.xcconfig` files; one set by a script at archive time is not seen.

## Files

| File | Purpose |
|---|---|
| `scripts/scan.py` | the nine scripted groups, `design` and `binary`; JSON rows `{id, group, verdict, summary, evidence, fix}` |
| `scripts/market.py` | the App Store index behind `market` (charts, search, icon and screenshot prints), the team's live apps, and the comparisons; `refresh`, `search`, `stats` |
| `scripts/ledger.py` | per-team submission ledger: `record` (with the scan behind each submission), `check`, `show`, `stats` |
| `scripts/selftest.py` | builds a Suika-like clone, an original, blind-spot projects, Unity/Godot/Xcode projects and an .ipa with a fixture App Store index; checks every verdict offline |
| `references/signatures.json` | fingerprints of 72 hits and trademarked games: names, wording, characters, progressions |
| `references/stock-assets.json` | stock packs, their markers, and path words for main objects vs UI |
| `references/checks.md` | judgement checks J1–J6 |
| `references/guideline-4.3.md` | guideline text, rejection variants, resubmission, appeal, reply template |
| `references/case-fruit-mischief.md` | the case this skill comes from, before and after |
