---
name: game-clone-pipeline
description: >-
  Turn a successful mobile casual/puzzle game, or a game idea set against the closest hits, into
  a differentiated, English-only Flutter game on the App Store with a landing page, in 10 gated
  stages: pick target and reference games → evidence from whatever the human has (APK via REA,
  game data, a short video, a description) → SPEC → differentiation and economy design →
  Flutter core with tests, bot and simulator → 3 UI directions (huashu-design) →
  flutter-ui-revamp + icon → IAP and playtest → codebase-modernizer, plan-to-issues, fixes →
  privacy/support pages → iOS built on a Mac → appstore-assets, aso-marketing,
  appstore-review-checker → ship and submit → search-optimizer, design-optimizer.
  Pauses at human gates, commits each stage, resumes from `.clone/status.md`. Use when
  asked to "clone a game", "make a game like X", "làm game giống X", "làm game từ ý tưởng này",
  "chạy quy trình clone". Don't use for non-game apps (flutter-factory), Kotlin games
  (android-game-forge), web apps, or a single step on its own.
license: MIT
effort: high
capabilities:
  - orchestration
  - workflow
  - human-gates
  - flutter
  - app-store
metadata:
  version: 1.17.0
  author: "Nguyen Van Lam"
permissions:
  filesystem: { read: true, write: true }
  shell: { enabled: true }
  network: { enabled: true }   # store pages, gh, pub get, Telegram Bot API (optional)
  secrets: { required: false } # Apple keys stay with the human; never written to the repo
---

# game-clone-pipeline: reference game or idea → differentiated Flutter game → App Store

The agent orchestrates; sibling skills do the specialised work. The human brings what they have
about the game (an APK, data files, a video, a description), approves six gates, and
builds/uploads on a Mac. "The original" below means the reference game(s) chosen at S0. `PROCESS.md` (Vietnamese) is the one-page
version for people; this file is the operating manual.

## Hard rules

1. **Facts and mechanics only.** APK, data files, recordings and descriptions feed `SPEC.md`
   with rules and numbers. No asset, frame, sound, font, string, level file or code from the
   original (APK, data files, ads, store page) ever enters the game repo's tracked files.
   `.clone/reference/`, `.clone/apk/` and `.clone/data/` are git-ignored; `.clone/status.md` is
   tracked so any session can resume.
2. **Differ before you draw.** Theme, palette, naming and an own mechanic are decided at S2 and
   checked against `references/differentiation-gate.md`. The core is built on placeholder art;
   the real look arrives at S4.
3. **Economy with the core loop.** Fail state, boosters, IAP and anti-farm rules are designed
   at S2 (`references/economy-and-monetization.md`), not bolted on later.
4. **English only.** All in-game text, store listing (en-US, no localization), IAP names,
   landing page, privacy and support pages. Internal docs (SPEC, DESIGN, status) may be
   Vietnamese.
5. **main + tags.** Work on `main`; releases are tags `vX.Y.Z`. No long-lived `ios` branch.
   Temporary branches come only from sibling skills (`test-coverage` at S3, `flutter-ui-revamp`
   at S4, one per issue at S6). A stage that creates a branch ends with it merged into `main`
   and deleted locally and on GitHub ("Closing a branch"); the stage is not done while one of
   its branches or PRs is open. Before S8, `git branch -a` lists only `main` and `origin/main`
   and `gh pr list --state open` is empty. A background session (`claude --bg`) must isolate its
   changes, so it works each stage in one worktree ("Background sessions"): from the game repo's
   root (check `pwd`), `EnterWorktree` with `name: s<N>-<stage>`; sibling skills commit on that
   worktree's branch instead of making their own; at the stage end `ExitWorktree` with
   `action: "keep"`, then close `worktree-s<N>-…` like any other branch. It leaves that worktree
   only at the stage end: a gate inside the stage is asked and waited for there (start `ask`, end
   the turn, carry on in the same worktree when it returns), and the next stage starts after the
   merge. A worktree is never re-entered (`path:`): from another repo that raises a permission
   prompt only the computer can answer, and a session once sat on one with a whole stage
   unmerged. Merge a worktree left early from the repo root with git.
6. **Gates advance on evidence.** A command that ran in this session and exited 0, or a human
   answer recorded in `.clone/status.md`. Never on a claim.
7. **Commit after every stage** with the `commit` skill (English conventional commit, secret
   scan, push, never `--no-verify` or force). Tags and releases are `/ship`'s job.
8. **App Store only.** No Google Play release in this pipeline; Android files in the Flutter
   project are left as generated.
9. **Human-only decisions stay human:** gates G0, G0b, G1, G2 (UI direction), G3 (prices), G4
   (submit), every App Store submission, every secret value, every paid action.
10. **Keep the steps pane current.** `.clone/status.md` drives the steps pane: rewrite its
    `Now:` line when a stage or a numbered step starts, always as `S<n> · <step>`
    (`Now: S1 · 2 contact sheets`), and its `Waiting on:` line with the human's next action only
    when the run stops for them (rule 16; `Waiting on: G0b: trả lời ❓ trong SPEC.md`), back to
    `—` once they answered. Deferred human steps are no stop: they sit under
    `## Deferred (human)` while `Waiting on:` stays `—` and the work goes on. The bot warns about
    a run that died only while `Waiting on:` is `—`, so a filled one hid a session that stopped
    with a stage left. With nothing left but the deferred Apple steps, park in one form:
    `Now: S8 · 6 waiting for the Apple steps` and `Waiting on: S8-apple: build VALID + Apple ID`,
    asked as rule 13 says. The pane and `/games` redraw by themselves from the newest copy, a
    stage worktree's included; a `Now:` in another form shows the first unchecked stage.
11. **No GitHub Actions.** No file under `.github/workflows/` in the game repo or the site repo,
    no CI job, no build on Actions. Checks run on the dev machine: `flutter analyze`,
    `flutter test`, the simulator, and pre-commit hooks once installed. Every delegate inherits
    this: a "no CI" finding is not a finding, and no task may add a workflow. GitHub Pages
    deploys from a branch, not from a workflow.
12. **`asc` is deferred.** The agent runs no `asc` command (no auth, bundle ids, IAP, metadata,
    screenshots, validate, release or reviews) until the human lifts this rule. Everything
    `asc` would push is written as files instead: `docs/APP-STORE-CONNECT.md` (bundle id, product
    ids, prices, review notes, URLs, a checklist) plus `store/` (screenshots, en-US texts), and
    the human enters it in the App Store Connect web UI. Status changes there advance on the
    human's answer, recorded in status.md.
13. **Apple account steps are deferred.** The human's App Store Connect web setup, the Mac
    build and upload, and the TestFlight test (S8 steps 2–3) are postponed by default: list them
    under `## Deferred (human)` in status.md, do not stop for them, and continue with the steps
    that need no Apple account (S8 steps 4–5, then S9's site work). Only `/ship`, the release
    upload and the submission (S8 step 6) wait until the human resumes the deferred steps.
    They resume only on what the human reads off App Store Connect, typed: the build number
    TestFlight shows as VALID and the app's Apple ID (App Information, digits). Ask as gate
    `S8-apple` with `--option "Để sau"` only; the bot enforces the rest: it refuses other
    buttons, settles only on the deferral or on both values (the answer then carries `build` and
    `apple_id`), and files any other reply in the inbox marked `held`, which is never the answer
    (a run was once tagged and recorded as submitted on taps alone, with no build made). Before
    recording the values, check `gh api repos/<owner>/<repo>/traffic/clones --jq .count` (last
    14 days): the Mac build starts with `git clone`, so 0 means asking once more and saying why;
    a second answer with both values stands.
14. **Telegram is an optional remote gate.** At the computer the human decides in the chat as
    always; Telegram only speaks up in away mode (see "Telegram remote"). Only the allowlisted
    chat counts as the human, and the gate log Notes say `via Telegram` or `tại máy`. Never ask
    for or accept a secret, password or Apple credential over Telegram (rule 9); files received
    land only in the git-ignored `.clone/` folders (rule 1); the bot token never enters a repo.
    Sessions the phone starts (`/open`, `/new`, or an answer with no session running) run as
    `claude --bg` with `--permission-mode auto`; the phone can stop only those, never a session
    at the computer. Without the config file the run behaves exactly as without this rule.
15. **Stay in the game repo.** Read another repo (an earlier game's DESIGN.md at S2, any
    reference project) by absolute path or `git -C <path>`; never `cd` into it. A session's
    working directory follows `cd`, so the next `EnterWorktree`, `git` or `flutter` command lands
    in the wrong repo. A background session once sat two days at the start of S5 this way,
    holding a call only the computer could release. The site repo is written the same way, from
    the game repo's root ("Site repo" under Workspace).
16. **Only a human stop ends the turn.** End the turn at a human stop (a gate, a ❓ round, a
    `Waiting on:` asked with `ask` or in the chat) or at the Final report after S9, never
    elsewhere. A sibling skill's closing block (`Result / Evidence / Uncertainty / Decision`)
    is input to the pipeline, not the end of the run: read it, act on it, and start the next
    step in the same turn. A background session that ends its turn stops for good, because
    nothing prompts it again. One stopped at the start of S7 this way: it printed the
    landing-page-generator copy with `Decision: No approval needed.` and ended, before the
    site repo existed.

## Roles

| Who | Does |
|---|---|
| Human | Brings what they have (APK, data files, a gameplay clip, a description), answers ❓, approves gates (in the chat, or on Telegram while away), provides Apple account access, builds and uploads on a Mac |
| Agent | Runs every other step: REA analysis, contact sheets, SPEC, DESIGN, code, tests, sibling skills, commits; prepares App Store Connect inputs as files (hard rule 12) |

## Workspace (inside the game repo)

```
SPEC.md                 # S1: evidence-backed research (references/spec-template.md)
DESIGN.md               # S2: differentiation table, economy, difficulty targets, name
.clone/status.md        # stage checklist, Now / Waiting on, gate log (from templates/) — read first
.clone/reference/       # recordings, store screenshots, contact sheets  (git-ignored)
.clone/apk/             # the original's APK and REA notes                 (git-ignored)
.clone/data/            # game data the human gave: config, levels, saves  (git-ignored)
.clone/telegram/        # Telegram remote state: mode, inbox, pending question (git-ignored)
tool/simulate.dart      # S3: plays many seeded games with a bot and a careless player
tool/check.sh           # S3: local gate (format, analyze, test) the pre-commit hook runs
lib/store/              # S5: shop and save store from templates/store/, tests in test/
scripts/build-ios.sh    # S8: from templates/, archive/export/upload on a Mac
docs/IOS-BUILD-ON-MAC.md
```

Add `.clone/reference/`, `.clone/apk/`, `.clone/data/` and `.clone/telegram/` to `.gitignore`
at S0, before anything is copied in.

**Names.** The game repo (folder and GitHub repo) carries the game's name in kebab-case,
`<game>` (Moss Lantern → `moss-lantern`); the landing repo is `<game>-site`. Never a `-clone` suffix,
in either. Until G1 fixes the name, the repo uses a working slug of the idea or target (also
without `-clone`) and is renamed right after G1 (see S2).

**Closing a branch** (rule 5), once analyze + test exit 0 on it, from the repo root on `main`:
`git merge --no-ff <branch>`, `git push`; for a worktree's branch `git worktree remove <path>`;
then `git branch -d <branch>` (it refuses unmerged work: never force it) and
`git push origin --delete <branch>` if it exists on GitHub. A PR closes as merged by itself once
its commits reach `main` on GitHub (`gh pr merge` is refused in auto mode). Then re-run
`flutter analyze` and `flutter test` on `main`. Never force-push; delete unmerged work
(`git branch -D`, closing a PR unmerged) only on the human's answer, logged in status.md.

**Site repo** (`<game>-site`, S7 and S9), worked from the game repo's root (rule 15). A
background session refuses Edit and Write in a checkout outside a worktree, so the site gets a
linked worktree of its own, made while the session is in no game worktree (an isolated session
refuses git aimed at another worktree). With `S=<parent>/<game>-site` and
`W=$S/.claude/worktrees/s<N>-site` as shorthand here (commands spell both paths out):
- `git -C $S worktree add -b worktree-s<N>-site $W`; the site's `.gitignore` lists `.claude/`
  (add it in `$W` if missing);
- edit under `$W` by absolute path (sibling skills get `$W` as their target), then
  `git -C $W add -A` and `git -C $W commit`;
- `git -C $S merge --no-ff worktree-s<N>-site`, `git -C $S push`, `git -C $S worktree remove $W`,
  `git -C $S branch -d worktree-s<N>-site`.
A new site repo has no checkout yet: S7 writes it straight into its folder, then `git -C $S init`.

**Background sessions.** A `claude --bg` session runs in auto mode, isolated in its stage
worktree (rule 5), and its guard refuses what it cannot check: 223 of 412 tool errors in 14
runs. So:
- one plain command per Bash call, written out in full: no `&&`, `;`, `|`, `$( )`, loop,
  heredoc or `cd`, and no variable standing for a path or value (`sed`, `python`, `ffmpeg`,
  `gh` and Chrome were refused on a `$VAR`); use `git -C <path>` and tool flags instead;
- files change through Edit and Write, never `sed -i`, `cat >` or `python - <<EOF` (a script
  that names git, even `.gitignore`, is refused); a longer script is written to a file and run
  as one command (`python3 tool/fix_links.py`);
- Edit and Write wait for `EnterWorktree`, which branches from `origin/main`: a new repo first
  gets an empty commit, pushed, from Bash (`git commit --allow-empty -m "chore: start <slug>"`);
- no `sleep` to wait (it is blocked): a background `ask` or command reports when it ends;
- the shell is zsh: spell `<tb>` out each time (`TB="python3 …"; $TB ask` fails, zsh does not
  split it) and quote URLs and globs (`'https://youtu.be/…?si=…'`).

**This machine** (Ubuntu): no phone or adb and no Linux desktop toolchain, so a local run is a
web build in Chrome, served on a free port (8080 is often another project's; never stop it).
Static screens come from `tool/screenshot_main.dart` in a phone-sized headless Chrome;
animations from a flutter_test filmstrip (`RepaintBoundary.toImage` around the whole app),
because Chrome's virtual time barely moves Flutter tickers. `analysis_options.yaml` sets
`formatter: page_width: 120`.

## Start or resume

1. If `.clone/status.md` exists, read it and continue at the first unchecked stage. Re-run the
   last stage's verification before trusting a checked box from an older session.
2. Otherwise ask for the target (a store URL or name, or a description of the game idea), what
   the human already has about it (S1's sources), and the parent folder; create the repo there
   under a working slug (see Names), private on GitHub (a background session pushes an empty
   first commit before `EnterWorktree`, "Background sessions"); copy
   `templates/status.md` to `.clone/status.md`, fill the header, start at S0.
3. **Steps pane**: `python3 <skill-dir>/scripts/steps_pane.py open <repo>` splits the agent's
   herdr pane and shows S0–S9 on the right with the current stage marked, reusing one already
   open. Exit 69 means no herdr: then show the output of `steps_pane.py once <repo>` in the chat
   at every stage change and gate stop instead.
4. **Sibling skills**: invoke them by name with the Skill tool. If one is missing, do its step
   inline with the same output, and log it under "Fallbacks" in status.md. A missing skill
   lowers quality; it never stops the run. Where a stage below says how to run a skill on this
   machine (only part of it, or inline), that is the standard route, not a fallback: log only
   what differs from it. When a sibling skill returns, its final report closes that skill's
   step, not the stage: carry on with the next step (hard rule 16).
5. **Telegram remote** (only when `~/.config/game-clone-pipeline/telegram.env` exists): run
   `python3 <skill-dir>/scripts/telegram_bridge.py watch <repo>` in the background once per
   session. It registers the repo; when the service already serves the bot it prints
   "already running" and exits 0, otherwise it serves until the session ends. Exit 69 = not set
   up: skip Telegram and say so once. Otherwise read `references/telegram-remote.md`, set the
   status.md `Remote:` line to `Telegram on`, then run
   `<tb> answers <repo>` and `<tb> inbox <repo>` and act on what they print. A decision in
   `.clone/telegram/decisions.jsonl` that the Gate log lacks was read by a session that stopped
   before recording it: record it now. After G1's rename, `<tb> register <new path>`.

## Telegram remote

The human decides at the computer while they sit there and on the phone while they are away
(rule 14). `scripts/telegram_bridge.py serve` (a systemd user service once `install-service`
ran) is the only reader of the bot and serves every game; `<tb>` is
`python3 <skill-dir>/scripts/telegram_bridge.py`. With Telegram set up, Start step 5 reads
`references/telegram-remote.md`: sessions the phone starts, stall warnings, away mode, how to
write for the phone, evidence with `<tb> send`, and the inbox (`<tb> inbox <repo>` at every stage
and numbered step boundary and before each human stop).

- **Every human stop** in a session at the computer (G0, G0b, G1, G2, G3, G4, a ❓ round, any `Waiting on:`):
  1. start `<tb> ask <repo> <GATE> "<question>" --option Approve --option Revise --option Reject`
     in the background (`run_in_background`, no timeout; free-text stops use no `--option`);
  2. ask the same question in the chat and end the turn, as before;
  3. answered in the chat → `<tb> close <repo> --answered-here "<answer>"`, then continue;
  4. the background `ask` finished → read its JSON line: `"event": "answer"` with `"by":
     "telegram"` is the human's decision (post "Bạn đã quyết qua Telegram: …" in the chat,
     record it, continue); `"event": "inbox"` → handle the inbox (reference) and start the same
     `ask` again (it reuses the question, it does not resend it).
  An answer that arrives while no session is waiting is kept; `<tb> answers <repo>` prints it.

## Stages

### S0 — Pick the game and its references → gate G0

- Reference games: the named original. For an idea with no original, the 1–3 closest
  successful games from `idea-validator`'s competitor list, confirmed by the human at G0.
- `idea-validator` on "a differentiated clone of <original>", or on the idea itself: demand,
  competition, feasibility. Its ideas root (`IDEAS_ROOT` or `~/.config/ideas-root.txt`) is not a
  git repo here, so it ends PARTIAL with nothing committed there: copy its report to
  `docs/idea-validation.md`. With the human away, its interview is answered from the brief and
  each answer is marked as an assumption.
- Fit check (write the answers in status.md): 2D and rule-based (Flutter + CustomPainter or
  Flame can do it), a twist is possible, the category is not flooded with near-identical clones
  (Guideline 4.3), the reference games' monetization is understood from their store pages.
- **G0**: human approves the target, the reference games and the twist hypothesis. Commit
  (`docs: start clone of …`).

### S1 — Evidence from what the human has → SPEC → gate G0b

One source is enough to start; each extra one turns ❓ into facts. Use what the human named at
the start, ask once for anything else they may have, and never wait for a source they lack.
Files sent to the Telegram bot (up to 20 MB) are saved by type into the same folders.

| Source | Put in | Read with | Best for |
|---|---|---|---|
| APK / XAPK / AAB | `.clone/apk/` | REA (step 1) | engine, SDKs, IAP product IDs, permissions, shipped config |
| Game data: config JSON/CSV, level files, remote-config or save dumps, asset bundles | `.clone/data/` | Python or `jq`; binary bundles with REA `inspect_artifact` (step 3) | exact numbers: board sizes, spawn tables, prices, timers, difficulty curve |
| Gameplay video of any length; a few minutes of the core loop is enough to start | `.clone/reference/` | `scripts/contact-sheet.sh` (step 2) | rules, flow, timings, feedback, fail state |
| Store pages, screenshots, public gameplay videos | `.clone/reference/` | fetched by the agent for every named reference game | store facts, monetization, the look to avoid |
| Written description of the game or the idea | quoted in SPEC §4 | as given (step 4) | rules as the human knows or wants them |

1. **APK via REA** (`reverse-engineer-anything`). From the human, or with a phone attached
   `pull_adb_package` (REA). Use REA's Android tools (manifest, resources via Apktool, JADX
   classes) to record: engine (Unity IL2CPP/Mono, Flutter, native), SDKs (ads, mediation,
   analytics, IAP), product IDs, permissions, readable config numbers. Logic inside
   `libil2cpp.so` or values from remote config → write "not recoverable from the APK". Record
   facts with the file path as evidence in SPEC §2. Copy nothing else. REA's own terms limit it
   to lawful research and authorized analysis; stay within them.
2. **Video**: `scripts/contact-sheet.sh <video> .clone/reference/sheets [--at t1,t2]` (1 fps
   sheets with burned-in timestamps, 4 fps strips around key moments); read the sheets with
   vision. With a cable the agent can record itself (`adb shell screenrecord` / REA
   `capture_adb_screen`). A loss and the shop/booster screens settle most economy ❓: ask for
   them as short clips, not a long session.
3. **Game data**: take numbers and distributions (colours per level band, capacity, timers,
   prices), never the level layouts themselves. Cite file and key
   (`.clone/data/levels.json → levels[12].capacity`) in SPEC §2.
4. **Description**: quote it rule by rule in SPEC §4 with "description" as the evidence;
   whatever it leaves open is ❓. For an idea, SPEC §1, §3 and §5 cover the reference games
   from their store pages and public videos.
5. Write `SPEC.md` from `references/spec-template.md`; every rule cites its source, guesses are
   ❓. When sources disagree, the video beats data files and the APK (remote config may override
   shipped values), data files beat numbers estimated from a video, a description loses to any
   of them; note both values.
6. End SPEC with the ❓ list as the cheapest concrete requests ("a 1-minute clip filling the
   board completely", "the shop screen", "the file behind …").
- **G0b**: human answers, sends more, or accepts the gaps; agent updates SPEC (at most 2
  rounds); what remains becomes an explicit assumption in DESIGN.md. Commit (`docs(spec): …`).

### S2 — Differentiation and economy → gate G1

- Fill `DESIGN.md`: the table from `references/differentiation-gate.md` (every **must** row
  "different", one own mechanic), economy per `references/economy-and-monetization.md` (fail
  state, session unit, boosters with anti-farm rules, IAP list with product IDs, ads yes/no,
  analytics yes/no), difficulty targets for the simulator, English name. Fill its "Own
  portfolio" rows too, against the DESIGN.md of every earlier game in the parent folder (read
  in place, rule 15): Guideline 4.3 also counts the developer's own look-alike apps.
- `brand-name-checker` on the name; act on Proceed/Modify/Abandon.
- **G1**: human approves DESIGN.md. Commit.
- Rename the repo to the approved name (see Names), unless it already has it:
  `gh repo rename <game>`, move the folder to `<parent>/<game>`, then
  `git remote set-url origin git@github.com:<owner>/<game>.git` and update the repo URL in the
  status.md header. Reopen the steps pane on the new path.

### S3 — Core in Flutter (placeholder art)

- New project: `flutter-init` inside the game repo (org from the user's other apps, e.g.
  `com.nguyenvanlam`), its create step only: the toolchain is installed, Android stays as
  generated (rule 8, no SDK pinning), and the code keeps pure-Dart rules in `lib/game/` and the
  UI in `lib/ui/` instead of its clean-architecture scaffold. The folder already holds `.git`,
  `.gitignore`, `.clone/`, `SPEC.md` and `DESIGN.md` from S0–S2, so:
  - when it asks about the existing directory, answer **use in place**: run its create command
    with `--project-name <snake_case> .` (a kebab-case folder name such as `<game>` with a
    hyphen is not a valid Dart package name, and `flutter create .` exits 1 on it);
  - `flutter create` keeps an existing `.gitignore`, so move ours aside first and add it back
    afterwards; otherwise `build/` and `.dart_tool/` are not ignored:
    `mv .gitignore .gitignore.clone` → create → add its lines to the new `.gitignore` with Edit
    → `rm .gitignore.clone`;
  - skip its `git init` (the repo and its remote exist since S0), keep the credential lines it
    appends to `.gitignore`;
  - before committing, `git status --short` shows nothing from `.clone/reference/`,
    `.clone/apk/`, `.clone/data/`, `build/` or `.dart_tool/`.
- Local gate (rule 11): copy `templates/tool/check.sh` and `templates/tool/install_hooks.sh`
  into `tool/` and run `bash tool/install_hooks.sh` once. Every later commit, from any worktree,
  then runs format, analyze and test with git's hook variables cleared (left set, they make
  Flutter report SDK `0.0.0-unknown` and rebuild its tool). `pre-commit install` refuses under
  the global hooksPath here; never edit git config to get around it.
- Rules in pure Dart (no Flutter imports) so tests and the simulator run on the VM; seeded,
  platform-identical RNG (xorshift-style) for deals/levels; UI replays rule "steps".
- Tests for every rule in SPEC §4 that we keep; a heuristic bot; `tool/simulate.dart` printing
  win rates of bot and careless player per difficulty band against DESIGN.md targets.
  `test-coverage` if branches are thin; at the computer it writes the tests on its own `feat/…`
  branch, so close that branch afterwards ("Closing a branch"); in a stage worktree it commits
  on the worktree's branch (rule 5).
- Verify: `flutter analyze` and `flutter test` exit 0 on `main`, no branch but `main`; simulator
  numbers recorded in DESIGN.md.
  Commit after each green milestone.

### S4 — UI direction and look → gate G2

1. `huashu-design` (default; `lam-design` if the user prefers): three real HTML directions for
   the game screen + home, using our DESIGN.md theme, not the original's. The skill stops for
   the choice: **G2**. While away, the phone gets all three screenshots before G2 is asked (one
   `send`, each `--file` followed by `--caption "A · <name>"`, then B and C). Run the
   differentiation check (fresh-eyes comparison) on the chosen one. A "close" finding is a
   question, not a fix: show it with the changes it suggests and ask (keep the mockup / apply
   them) before building; record the answer. The build then matches the chosen mockup exactly:
   a layout, palette or copy change made on the side is a design decision taken without the
   human (rule 9).
2. `flutter-ui-revamp`: give it the chosen direction so Step 2 only records it in
   `.revamp/design-direction.md`; it sources licence-verified assets, builds the design system,
   applies it to the real screens and verifies. At the computer it works on `ui-revamp/<date>`:
   close that branch once it verifies ("Closing a branch"); in a stage worktree it commits on the
   worktree's branch (rule 5). A revamp the human rejects is deleted only on their answer (its
   own rollback).
3. `logo-designer` for the app icon, run inline: its subagents and SVG rasterisers (rsvg,
   cairosvg, inkscape) are missing here, so one script draws every variant from one geometry,
   headless Chrome renders the PNGs and Pillow drops the alpha. Generate platform icons (no
   alpha for iOS).
- Verify: analyze + test exit 0 on `main`, no branch but `main`, screenshots of home and game
  captured. Commit.

### S5 — IAP, boosters, telemetry, playtest → gate G3

- Implement DESIGN.md's economy. The store starts from `templates/store/` (its README: what to
  copy, the two seams to fill, the rules for the shop screen), never from an earlier game's
  code: copying spread the same purchase bugs through 11 games. Its tests pin what must hold: a
  grant is saved before the purchase is completed, a re-delivered one too; only StoreKit
  2-verified purchases are granted; Ask to Buy, a stream error or a pack without a transaction
  id never leaves the shop stuck; without device storage the game still starts and packs pause;
  a bought pack is never clipped by a cap. Then Restore purchases, every purchase path, the
  store-unavailable message without naming platforms, anti-farm tests, no debug unlock in
  release. Analytics/crash SDK only if DESIGN.md says so (then update privacy page).
- Human playtest (3–5 people or the user): note where they get stuck or bored; re-tune with
  the simulator. It does not block G3: with none done yet (the human is away or has no testers),
  list it under `## Deferred (human)` in status.md, say so in the G3 question, and re-tune once
  notes arrive.
- **G3**: human approves the product list and price tiers. Commit.

### S6 — Codebase hardening

- `codebase-modernizer` (the "codebase optimiser" step): read-only audit → `MODERNIZATION_PLAN.md`.
  Pass it hard rule 11 in its arguments: the `CI` dimension covers local pre-commit hooks only,
  "no CI" is out of scope, and the plan must not contain a workflow task (`devops-pipeline`
  runs pre-commit only).
- `plan-to-issues`: plan → labelled GitHub issues under one epic.
- Fix them: `issue-work-loop` per issue when herdr + gh are available. A background session has
  no herdr pane: it fixes them directly in the S6 worktree, one commit per issue or batch with
  `Closes #N` (the standard route). `code-review` optional for risky changes. `issue-work-loop`
  stops at CLEAN and does not merge: close each CLEAN PR right away ("Closing a branch") and let
  it sweep its worktree. A PR that does not reach CLEAN stays open, is logged under Fallbacks,
  and is merged after a fix or closed on the human's answer before S8.
- Verify: analyze + test exit 0 on `main`, `gh pr list --state open` empty, no branch but `main`.

### S7 — Landing repo, minimal (before any submission)

- New repo `<game>-site`: `landing-page-generator` for copy, a simple English page,
  `privacy.html` and `support.html` from `templates/` filled from DESIGN.md (must match what the
  app really collects), and a `.gitignore` with `.claude/`. Written from the game repo's root, and
  changed after its first commit through a site worktree ("Site repo"). The site repo is public
  (free Pages). Enable Pages from the branch, no
  workflow (hard rule 11):
  `gh api -X POST repos/<owner>/<game>-site/pages -f 'source[branch]=main' -f 'source[path]=/'`.
  Every push to `main` republishes the site.
- landing-page-generator's copy mode only prints the copy in the chat and ends with its own
  `Result: COMPLETE` block. That ends its step, not S7 (hard rule 16): put the copy into the
  site's `index.html` right away, then the privacy and support pages, Pages and the checks.
- Verify: both URLs return 200 (`curl -sI`). Commit with `commit` in that repo.

### S8 — iOS: prepare on Ubuntu, build and upload on a Mac → gate G4

Follow `references/ios-release-runbook.md`, skipping every `asc` step (hard rule 12). In short:
0. Branch check (rule 5): only `main` / `origin/main`, no open PR; otherwise finish S6 first.
1. `flutter-ios-release` (prep-report exit 0); copy `templates/build-ios.sh` →
   `scripts/build-ios.sh`, `templates/ExportOptions.plist` → `ios/ExportOptions.plist`; write
   `docs/IOS-BUILD-ON-MAC.md` (ending with what to send back: the VALID build number and the
   app's Apple ID, rule 13) and `docs/APP-STORE-CONNECT.md` (bundle id, IAP product ids and
   prices from DESIGN.md, Support/Privacy URLs from S7, review notes, web-UI checklist). Commit.
2. *(Deferred, hard rule 13.)* Human in the App Store Connect web UI: register the bundle id,
   create the app record and the IAPs from `docs/APP-STORE-CONNECT.md`. On a Mac:
   `TEAM_ID=… scripts/build-ios.sh upload`. Human answers `S8-apple` with the VALID build
   number and the app's Apple ID (rule 13); after the clone check, record both in status.md.
3. *(Deferred, hard rule 13.)* TestFlight with a Sandbox account (runbook §3): buy every
   product, cancel one, delete and reinstall, Restore; IAP review screenshot. Until then the
   purchase code has met only fakes, so check that a bought pack arrives once and is still there
   after a relaunch: granted again on every launch means it was never completed, never granted
   means StoreKit 2 verification refused it.
4. `appstore-assets` (en-US; iPad set only if iPad is targeted) and `aso-marketing` (en-US)
   write `store/` (screenshots, name, subtitle, keywords, description); the human pastes them
   into the web UI, plus age rating and category from the checklist. aso-marketing's plan
   approval goes into the G4 question, not a stop of its own.
5. `appstore-review-checker` on the source, the iOS project and `store/` (the build too, once
   steps 2–3 are done). **G4**: human reads the report and approves the package, and answers
   once whether S9 may scan the site with isitagentready.com (an outside service); with steps
   2–3 still deferred, G4 approves everything except the build and is noted as partial. G4 is
   waited for in the S8 worktree (rule 5); with steps 2–3 deferred, that worktree ends there:
   merge it, then start S9.
6. Waits for the deferred steps 2–3. `/ship --no-auto` (version bump, changelog, tag, push; asks per step) → human uploads the
   release build from the Mac and submits in the web UI ("Add for Review" with the first IAP).
   Record in status.md, commit.

### S9 — Landing polish and follow-up

- In a site worktree ("Site repo"): `search-optimizer`, then `design-optimizer`, both run on
  this site (another game's audit is no substitute). Its agent-readiness scan runs only on the
  yes recorded at G4; without one it is skipped, with no Fallback row. Merge; Pages redeploys on
  push.
- List the site in the root Pages repo `<parent>/<owner>.github.io` (worked like the site repo):
  `robots.txt` gets `Sitemap: https://<owner>.github.io/<game>-site/sitemap.xml` and `llms.txt`
  gets `- [<Game>](https://<owner>.github.io/<game>-site/llms.txt): <one-line pitch>, coming
  soon`, in one commit (`chore: list <Game> in root robots.txt and llms.txt`), pushed. Crawlers
  read robots.txt only at the host root, so the site's own sitemap counts only through it.
- Tick S9 then; store badges, links and dropping "coming soon" wait for the live app under
  `## Deferred (human)`.
- After launch: the human reads reviews and analytics in App Store Connect (no `asc`, hard rule
  12) and passes findings back; file them as issues.

## Final report (end of each session)

Stage reached, gates passed with dates, commands run and their exit codes, fallbacks, open
assumptions, what the human must do next (record, approve, build on the Mac). Tick boxes in
`.clone/status.md` and commit it. Once S9 is done, `steps_pane.py close <repo>` and stop the
Telegram `watch` process if this session started one; before that
leave the pane open.

## Files in this skill

| Path | Use |
|---|---|
| `PROCESS.md` | Vietnamese one-page process for people |
| `references/spec-template.md` | SPEC skeleton and evidence rules (S1) |
| `references/differentiation-gate.md` | similarity checklist, hard "no" list (S2, S4, S8) |
| `references/economy-and-monetization.md` | fail state, boosters, IAP, ads, analytics (S2, S5) |
| `references/ios-release-runbook.md` | Ubuntu prep + Mac build/upload (S8); its `asc` commands are deferred by hard rule 12 |
| `references/telegram-remote.md` | the Telegram bot in detail: phone sessions, stall warnings, away mode, writing for the phone, evidence, inbox (rule 14) |
| `scripts/contact-sheet.sh` | recording → timestamped contact sheets and strips (S1) |
| `scripts/steps_pane.py` | steps pane in herdr, redrawn from the newest status.md (a stage worktree's included): `open`, `close`, `once` (all stages) |
| `scripts/telegram_bridge.py` | optional Telegram remote (rule 14): `setup`, `install-service`, `serve`/`watch`, `register`, `ask`, `close`, `answers`, `inbox`, `mode`, `send`, `hook` |
| `templates/status.md` | `.clone/status.md` starter |
| `templates/tool/check.sh`, `templates/tool/install_hooks.sh` | local pre-commit gate (format, analyze, test) with git's hook variables cleared (S3) |
| `templates/store/` | store code every game starts from, with its tests and a README (S5): save before completing, StoreKit 2 verification, never stuck |
| `templates/build-ios.sh`, `templates/ExportOptions.plist` | Mac archive/export/upload kit (S8) |
| `templates/privacy.html`, `templates/support.html` | App Store privacy and support pages (S7) |
