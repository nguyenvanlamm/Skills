# SPEC.md template (stage S1)

Copy the skeleton below to `SPEC.md` at the game repo root and fill it. Internal docs may be
written in Vietnamese; quoted on-screen text stays as it appears. Model: `coin-cubby/SPEC.md`.

Rules for every SPEC:

- **Every rule cites evidence**: a timestamp from a recording (`rec2 03:14.5`), a contact-sheet
  tile, a store screenshot, or an APK path (`assets/config/levels.json`). No evidence → mark ❓.
- **Mechanics and numbers, never expression.** Write "capacity 10 coins per pocket", not the
  original's level files, art, sounds, strings or code. Nothing from `.clone/reference/` or the
  APK is copied into the game.
- **Observation beats the APK.** When an APK value and the recording disagree, trust the
  recording (remote config may override the shipped value) and note both.
- **Ads are not the game.** Playable ads and store videos are scripted; flag rules seen only there.

---

```markdown
# <Original name> clone: research spec

> Sources: recordings `.clone/reference/rec1.mp4` (<length>, <device>, <date>), APK
> `<package>` v<version> analysed with REA on <date>, store pages (Google Play <url>, App Store
> <url>) fetched <date>, <n> store screenshots.
> ⚠️ Points marked ❓ are inferred, not seen.

Position convention: <how rows/columns/slots are numbered in this document>.

## 1. Original game

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

## 2. From the APK (REA)

| Fact | Value | Evidence (REA tool + path) |
|---|---|---|
| Engine | Unity IL2CPP / Unity Mono / Flutter / native | `lib/arm64-v8a/libil2cpp.so` present … |
| SDKs: ads, mediation, analytics, attribution | | manifest / class prefixes |
| IAP product IDs and types | | strings / manifest |
| Permissions | | manifest |
| Readable config (balance numbers, level counts) | | `assets/…` |
| Not recoverable from the APK | e.g. "balance is remote config", "logic in IL2CPP" | |

## 3. Look and UI layout (to be AVOIDED, recorded only so DESIGN.md can differ)

- Screen layout, HUD, board, buttons, colours per value/type, feedback words and effects.
- Every item here gets a "ours differs by…" answer in DESIGN.md (references/differentiation-gate.md).

## 4. Observed rules

| # | Rule | Evidence |
|---|---|---|
| 1 | | rec1 00:12.0–00:13.5 |

## 5. Economy and monetization of the original

- Fail state: what happens, what is offered (continue, booster, ad, lives).
- Currencies, sources and sinks; booster list and prices; where ads appear (interstitial after
  level N?, rewarded for what?); IAP offers and when they are shown; lives/energy.
- Difficulty curve: what changes per level or tier.

## 6. Open questions ❓

Turn each one into a concrete request for the human (stage S1, gate G0b):

| # | Question | How to resolve |
|---|---|---|
| 1 | What happens when the board is full? | Record: fill every pocket and keep playing |

## 7. Reference files (internal, git-ignored)

| File | Content |
|---|---|
| `.clone/reference/rec1.mp4` | |
| `.clone/reference/sheets/contact_01.jpg` | 0–20 s, 1 fps |

## 8. Legal notes

- Mechanics are not protected; the original's name, logo, art, audio, text, level data and
  code are. None of them enters the build. `.clone/` is git-ignored.
```
