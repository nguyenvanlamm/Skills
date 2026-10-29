# Differentiation gate (stage S2 → gate G1, re-checked at S4 and before S8)

Why: Apple rejects copycats (App Review Guideline 4.1) and repetitive or saturated apps (4.3).
A redraw that keeps the original's look can still be "substantially similar" (trade dress;
see Tetris Holding v. Xio Interactive, 2012). Rules are free to reuse; the expression is not.
"Change a little" is not enough. Each row below needs a concrete answer in `DESIGN.md`.

## Checklist

Write `DESIGN.md` §Differentiation as this table, against every reference game chosen at S0
(for an idea with no original, the closest hits). G1 passes only when every **must** row is
"different" (rows 9 and 14: "present"), and at least one **own mechanic** exists.

| # | Aspect | Must? | Reference game(s) (from SPEC §3) | Ours | Verdict |
|---|---|---|---|---|---|
| 1 | Name, wordmark, icon subject | must | | | different / close / same |
| 2 | Setting / theme (what the objects *are*) | must | | | |
| 3 | Colour palette and the colour mapping of values/types | must | | | |
| 4 | Board / play-area presentation (material, perspective, frame) | must | | | |
| 5 | HUD layout (progress bar, currency, buttons placement) | must | | | |
| 6 | Main action button wording and icon (e.g. "Deal!") | must | | | |
| 7 | Feedback words, sounds, signature effects | must | | | |
| 8 | Store screenshots style and captions | must | | | |
| 9 | Own mechanic or twist (not in any reference game) | must | — | | present / missing |
| 10 | Structure (levels, checkpoints, endless) | should | | | |
| 11 | Economy (boosters, currencies) | should | | | |
| 12 | Onboarding / tips | should | | | |
| 13 | Main-object and icon art original — no stock or emoji pack, not redrawn in a pack's style | must | | | different / close / same |
| 14 | Own mechanic visible in a fresh install's first 30 seconds (first screen or first interaction) | must | — | | present / missing |

## Own portfolio (the developer's earlier games)

Guideline 4.3 also covers a developer's own look-alike apps. Add these rows to the table,
checked against the DESIGN.md of every earlier game in the parent folder (read in place); the
**must** rows count for G1 like the others.

| # | Aspect | Must? | Closest earlier game(s) | Ours | Verdict |
|---|---|---|---|---|---|
| P1 | Core verb (what the thumb does every few seconds) | must | | | different / close / same |
| P2 | Theme, palette and icon subject | must | | | |
| P3 | IAP lineup (products and price ladder) | should | | | |
| P4 | Store screenshot template and caption voice | should | | | |
| P5 | Name pattern and wordmark style | should | | | |

8 of the first 12 games sold the same lineup (a full unlock plus a small and a large pack of
one item), and one was judged "close" to three earlier games at once. Take the IAP shapes from
this game's own economy (`references/economy-and-monetization.md`), not from the last game's
DESIGN.md, and give each game its own screenshot template.

## Hard "no" list (fails the gate on sight)

- Any file, frame, sound, font or string taken from the original, its APK, data files, ads or
  store page.
- The original's name, publisher name or recognisable parts of either in the app name,
  subtitle, keywords, icon or screenshots.
- Same palette **and** same object **and** same board presentation, even if redrawn.
- Store screenshots composed like the original's (same captions, same order of claims).

## How to check

1. Put a screenshot of our build (or the chosen HTML direction at S4) next to each reference
   game's store screenshot, and next to the closest earlier game of our own. Ask a fresh subagent
   that has seen neither design discussion: "Would a player think these are the same game or the
   same brand?" Record its answer in DESIGN.md. At S4 a "close" answer goes to the human as a
   question before the build changes (SKILL.md S4).
2. Run `brand-name-checker` on the chosen name; act on its Proceed/Modify/Abandon verdict.
3. Run `appstore-spam-guard`: `design` mode at S2, `build` at S4, `submit` at S8 (SKILL.md rule
   17). It measures what this table asks — a hit's progression, stock art, the icon, the
   listing, your other games, the account — and compares the name, icon and description with
   the ~7,000 games on the App Store charts; a FAIL row fails the gate. Its judgement checks
   J1–J6 include the fresh-eyes comparison above and row 14.
4. At S8, `appstore-review-checker` re-checks the other guidelines on the real build and listing.

## Lesson from Fruit Mischief (4.3(a), 2026-10-23)

A Suika-like with a real roguelike twist was rejected for spam, and its account put on Extended
Review. Nine of its eleven fruits were Suika's, in order, with Suika's "two of the largest
vanish" rule; all of them were Microsoft Fluent Emoji; the icon was the emoji watermelon; the
listing said "from Cherry to Watermelon"; the twist first appeared after merge 6. The audit
before submission called 4.3 "reviewer judgement" and let it through. Rows 13 and 14 exist for
it, and `appstore-spam-guard` fails that build on all four signs
(`appstore-spam-guard/references/case-fruit-mischief.md`).

## Lesson from an earlier clone

An earlier clone redrew everything in code yet kept the wooden 3×5 tray with gold padlocks, the
curtain backdrop, the same value→colour mapping, a green "Deal!" button with a coin icon, a
blue bar with a red gift box and the same praise words. That is the pattern this gate exists to
stop: decide theme and look at S2, build the core on placeholder art, apply the chosen look at S4.
