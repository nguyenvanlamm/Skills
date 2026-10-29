# Judgement checks (J1–J6)

What `scan.py` cannot measure. Each check names its evidence, the verdict rule and the fix.
Record every answer in the report with the evidence you used; "looks fine" is not evidence.

## J1 — Fresh-eyes comparison

**Evidence**: a screenshot of the game screen (or the chosen mockup before the build exists),
the store screenshots of each reference game, a screenshot of the developer's closest
earlier game (the `portfolio` group names it), the store pages of the games the `market`
rows name (the closest icon, any name or wording match), and — when `metadata.saturated-genre`
names a crowded category — the screenshots of that category's top three games on the store.

**How**: give the images to a fresh subagent that has seen no design discussion and ask only:

> Here are screenshots of several mobile games. For each pair (A with B, A with C, …): would a
> player think these are the same game, the same brand, or different games in the same genre?
> Answer per pair: same game / same brand / same genre / unrelated, with one sentence of why.
> Then: what can a player do in A that they cannot do in any of the others? One sentence, or
> "nothing".

**Verdict**: "same game" with any reference → FAIL; "same brand" with an earlier own game →
FAIL; "same game" or "same brand" disputed by what the scan found → WARN and show the human.
"Same genre" passes only with an answer to the last question: "nothing" in a crowded category
(`metadata.saturated-genre`) → FAIL, elsewhere → WARN. 4.3(b) turns away "variants of existing
app categories", not only copies of one app.

**Fix**: change what the subagent named (object theme, palette, board, HUD), then ask again.

## J2 — The own mechanic in the first 30 seconds

A reviewer gives a new app about a minute. If the first 30 seconds look like the hit, the
review is over before the twist shows.

**Evidence**: the launch flow in code (what the first screen shows, what unlocks when — search
for thresholds such as `firstDraftAt`, `unlockAtLevel`, `tutorialAfter`), the onboarding, the
first two store screenshots, the subtitle and the description's first sentence.

**Verdict**:
- There is no own mechanic: the game is its genre's standard (the classic rules plus levels,
  hints, themes or daily puzzles) → **FAIL** in a crowded category (`metadata.saturated-genre`),
  WARN elsewhere. Polish is not a mechanic.
- The own mechanic is not on the first screen and not reachable in the first interaction
  (e.g. offered only after merge 6, level 3, or a minute of play) → **FAIL**.
- It is reachable early but the first two screenshots or the first sentence lead with the
  genre's core loop instead → **WARN**.
- Otherwise → PASS.

**Fix**: put the mechanic first (Fruit Mischief now opens every run on a blessing pick), and
lead screenshots and copy with it.

## J3 — The icon's subject

**Evidence**: the 1024 icon (path in the `icon` row), the reference games' icons, the icons of
the developer's other apps, and `icon_subjects` in `signatures.json`.

**Verdict**:
- Emoji or clip-art, stock or redrawn in the same style → **FAIL**.
- The hit's signature object (a watermelon for a Suika-like, a numbered tile for a 2048-like) →
  **FAIL**.
- Same subject and style as another of the developer's icons → **FAIL**.
- A single generic object on a plain background → **WARN**.
- The game's own character, tool or mechanic → PASS.

**Fix**: draw the icon from the game's own art (Fruit Mischief renders its icon from the
in-game durian with `tool/render_brand_art.dart`); no alpha channel on iOS.

## J4 — The listing's voice

**Evidence**: the `metadata` rows, the listing files, the screenshot captions.

**Verdict**: any `metadata` FAIL stands. Beyond that: the subtitle or the first paragraph is the
genre loop rather than the own mechanic → WARN; the listing compares the app with another app
or promises "the game you know" → FAIL.

**Fix**: subtitle and first sentence name the own mechanic; keywords carry the mechanic and
theme, not the hit's objects; captions follow the same order.

## J5 — Who owns it, who publishes it

**Evidence**: the `ownership` row, the App Store copyright line, the seller (account holder),
the privacy-policy contact, and any publishing agreement.

**Verdict**: owner and publisher differ with no written authorization → **FAIL** (5.2.1);
they differ with an authorization, but the review notes do not say so → **WARN**; they are the
same → PASS.

**Fix**: keep the authorization ready, name the IP owner in the review notes, and make the
copyright line, privacy contact and support page agree.

## J6 — The account's pace and portfolio

**Evidence**: `ledger.py check --team <team>`, the `portfolio` rows, and the human's list of
apps in review or about to be submitted on the same team.

**Verdict**: the team has an open 4.3 on another app → **FAIL** (hold this submission);
another look-alike app from the same developer is in review now → **WARN**; three or more
submissions in 14 days → WARN.

**Fix**: hold, space submissions out, and keep each game its own (art, icon, screenshot
template, IAP lineup). Record every submission and every answer with `ledger.py record`.
