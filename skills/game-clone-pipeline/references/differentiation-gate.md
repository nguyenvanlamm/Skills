# Differentiation gate (stage S2 → gate G1, re-checked at S4 and before S8)

Why: Apple rejects copycats (App Review Guideline 4.1) and repetitive or saturated apps (4.3).
A redraw that keeps the original's look can still be "substantially similar" (trade dress;
see Tetris Holding v. Xio Interactive, 2012). Rules are free to reuse; the expression is not.
"Change a little" is not enough. Each row below needs a concrete answer in `DESIGN.md`.

## Checklist

Write `DESIGN.md` §Differentiation as this table, against every reference game chosen at S0
(for an idea with no original, the closest hits). G1 passes only when every **must** row is
"different", and at least one **own mechanic** exists.

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

## Hard "no" list (fails the gate on sight)

- Any file, frame, sound, font or string taken from the original, its APK, data files, ads or
  store page.
- The original's name, publisher name or recognisable parts of either in the app name,
  subtitle, keywords, icon or screenshots.
- Same palette **and** same object **and** same board presentation, even if redrawn.
- Store screenshots composed like the original's (same captions, same order of claims).

## How to check

1. Put a screenshot of our build (or the chosen HTML direction at S4) next to each reference
   game's store screenshot. Ask a fresh subagent that has seen neither design discussion: "Would a
   player think these are the same game or the same brand?" Record its answer in DESIGN.md.
2. Run `brand-name-checker` on the chosen name; act on its Proceed/Modify/Abandon verdict.
3. At S8, `appstore-review-checker` re-checks 4.1/4.3 on the real build and listing.

## Lesson from an earlier clone

An earlier clone redrew everything in code yet kept the wooden 3×5 tray with gold padlocks, the
curtain backdrop, the same value→colour mapping, a green "Deal!" button with a coin icon, a
blue bar with a red gift box and the same praise words. That is the pattern this gate exists to
stop: decide theme and look at S2, build the core on placeholder art, apply the chosen look at S4.
