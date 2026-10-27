# SPEC.md template (stage S1)

Copy the skeleton below to `SPEC.md` at the game repo root and fill it. Internal docs may be
written in Vietnamese; quoted on-screen text stays as it appears.

Rules for every SPEC:

- **Use what exists.** A SPEC can stand on any mix of sources: APK, game data files, a short
  video, store pages, the human's description. Fill the sections the sources reach; the rest are ❓.
- **Every rule cites evidence**: a timestamp from a recording (`rec2 03:14.5`), a contact-sheet
  tile, a store screenshot, an APK path (`assets/config/levels.json`), a data file and key
  (`.clone/data/levels.json → levels[12].capacity`), or `description`. No evidence → mark ❓.
- **Mechanics and numbers, never expression.** Write "capacity 10 coins per pocket", not the
  original's level files, art, sounds, strings or code. Nothing from `.clone/reference/`,
  `.clone/data/` or the APK is copied into the game.
- **Which source wins.** Video beats data files and the APK (remote config may override the
  shipped value); data files beat numbers estimated from a video; a description loses to any
  of them. Note both values when they disagree.
- **Ads are not the game.** Playable ads and store videos are scripted; flag rules seen only there.

---

```markdown
# <Game name> clone: research spec

> Sources (list only those used): recordings `.clone/reference/rec1.mp4` (<length>, <device>,
> <date>), APK `<package>` v<version> analysed with REA on <date>, data files `.clone/data/…`
> (<what they are>), store pages (Google Play <url>, App Store <url>) fetched <date>, <n> store
> screenshots, the human's description (<date>, quoted in §4).
> ⚠️ Points marked ❓ are inferred, not seen.

Position convention: <how rows/columns/slots are numbered in this document>.

## 1. Reference game(s)

One table per reference game. For an idea with no original, the closest hits confirmed at G0.

| Item | Value |
|---|---|
| Name / package | |
| Developer / publisher | |
| Installs, rating (Play / App Store) | |
| Age rating | |
| Monetization (ads, IAP types, prices from the store page) | |
| Last update / version | |
| Store description, short | |
| Features claimed in the description | |

## 2. From the APK (REA) and data files

Skip the rows no source reaches.

| Fact | Value | Evidence (REA tool + path, or data file + key) |
|---|---|---|
| Engine | Unity IL2CPP / Unity Mono / Flutter / native | `lib/arm64-v8a/libil2cpp.so` present … |
| SDKs: ads, mediation, analytics, attribution | | manifest / class prefixes |
| IAP product IDs and types | | strings / manifest |
| Permissions | | manifest |
| Readable config (balance numbers, level counts) | | `assets/…` |
| Numbers from data files (sizes, spawn tables, timers, prices, difficulty per band) | | `.clone/data/…` → key |
| Not recoverable from the APK | e.g. "balance is remote config", "logic in IL2CPP" | |

## 3. Look and UI layout (to be AVOIDED, recorded only so DESIGN.md can differ)

- Screen layout, HUD, board, buttons, colours per value/type, feedback words and effects.
- Every item here gets a "ours differs by…" answer in DESIGN.md (references/differentiation-gate.md).

## 4. Rules

Quote the human's description here rule by rule when there is one; video, data or APK evidence
confirms or replaces it.

| # | Rule | Evidence |
|---|---|---|
| 1 | | rec1 00:12.0–00:13.5 |
| 2 | | description |

## 5. Economy and monetization of the reference game(s)

- Fail state: what happens, what is offered (continue, booster, ad, lives).
- Currencies, sources and sinks; booster list and prices; where ads appear (interstitial after
  level N?, rewarded for what?); IAP offers and when they are shown; lives/energy.
- Difficulty curve: what changes per level or tier.

## 6. Open questions ❓

Turn each one into a concrete request for the human (stage S1, gate G0b):

| # | Question | How to resolve |
|---|---|---|
| 1 | What happens when the board is full? | A 1-minute clip: fill every pocket and keep playing |

## 7. Reference files (internal, git-ignored)

| File | Content |
|---|---|
| `.clone/reference/rec1.mp4` | |
| `.clone/reference/sheets/contact_01.jpg` | 0–20 s, 1 fps |
| `.clone/data/…` | |

## 8. Legal notes

- Mechanics are not protected; the original's name, logo, art, audio, text, level data and
  code are. None of them enters the build. `.clone/reference/`, `.clone/apk/` and `.clone/data/`
  are git-ignored.
```
