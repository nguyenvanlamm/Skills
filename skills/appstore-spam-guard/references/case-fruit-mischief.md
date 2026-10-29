# Case: Fruit Mischief, rejected under 4.3(a)

The case this skill was built from. Repo: `trai_cay_roi` (Flutter, iOS). Use it to calibrate a
verdict: if a game resembles the "before" column, it will likely be rejected the same way.

## What happened

- 2026-10-23: App Review rejected Fruit Mischief 1.0.0 (3) under **Guideline 4.3(a) — Design —
  Spam**, reviewed on an iPad Air. Nothing else failed: no crash, metadata, privacy or IAP issue.
  The four IAPs were never reviewed.
- The message named all three variants: similar binary, metadata and/or concept to apps from
  other developers, to apps the account had submitted, and to apps from a terminated account.
- The account (team `6W9K2M3768`, which also holds the developer's business apps) was put on
  **Extended Review**.
- The game's own audit before submission had flagged 4.3 as a WARNING that "can't be checked
  from code". Nothing measured it, so it shipped.

## Root causes, and how the scan sees them

| Cause | Evidence in the repo | `scan.py` on the rejected build |
|---|---|---|
| Suika's progression | the 11 fruits, in order: cherry, strawberry, grapes, lemon, tangerine, apple, pear, mango, pineapple, melon, watermelon — 9 of Suika's 11 steps; two watermelons vanish | `signature.suika.chain` **FAIL** 9/11 in order |
| Stock emoji art | all 11 fruits were Microsoft Fluent Emoji (`assets/fruits/*.png`, credited) | `assets.stock.fluent-emoji` **FAIL** (main objects) |
| Emoji icon | the icon was the Fluent watermelon sprite on a purple gradient | `icon.bundled` **FAIL** (dHash 7/64 to `assets/fruits/watermelon.png`) |
| Listing in Suika's words | "an 11-tier chain, from Cherry to Watermelon"; keyword `watermelon`; subtitle "Merge fruit, …" | `metadata.suika.phrase` **FAIL**, `metadata.suika.term` WARN, `metadata.generic-name` WARN |
| Twist hidden | the roguelike blessing draft first appeared after merge 6; no onboarding | J2 **FAIL** (judgement) |
| Old public footprint | a public site repo still described the game as "Fruit Drop" | `footprint.github` WARN |
| Publisher ≠ IP owner | copyright and code by one developer, published on another's account | `ownership.publisher` WARN; J5 |
| Account pace | several games submitted to the same team around the same time | `account.cadence` (when recorded), J6 |

## What fixed it (commit `ef76725` on `ios`)

- All 11 fruits redrawn as original vector art in code; `assets/fruits/` deleted; credits say
  the art is original.
- New chain: kumquat → longan → lychee → rambutan → mangosteen → starfruit → guava → dragon fruit
  → papaya → jackfruit → durian. Two durians burst into a bonus blessing pick, not Suika's
  vanish rule.
- Every run opens on a blessing pick before the first drop.
- Icon, launch image and web splash rendered from the in-game durian.
- Listing rewritten to lead with the blessing draft; no watermelon, no "drop".

The scan on that commit: `signature`, `assets`, `icon` and `metadata` all PASS; what remains is
WARN for the old public repo description, the publisher/owner difference (to be stated in the
review notes), and the resubmission itself (`account.resubmission`).

## The lesson in one line

A real twist does not save a game whose first minute, art and listing say "the hit, again" —
make it different where a reviewer looks first, and measure it before submitting.
