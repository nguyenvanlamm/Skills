# Changelog

## 1.18.0 — 2026-10-29

App Review rejected Fruit Mischief 1.0.0 (3) under Guideline 4.3(a) and put its account on
Extended Review. The differentiation gate was a self-assessed table, and the pre-submission
audit called 4.3 "reviewer judgement", so nothing measured the four signs a reviewer saw first:
Suika's fruit progression, stock Fluent Emoji fruit, an emoji icon and a twist hidden until
merge 6.

Changes:
- **Rule 17 and the new sibling `appstore-spam-guard`**: `design` mode at S2 (before G1),
  `build` mode at S4 (in Verify), `submit` mode at S8 beside `appstore-review-checker` (before
  G4). A FAIL row blocks the gate. Its `market` group compares the name, icon and description
  with the ~7,000 games on the App Store charts. Its ledger records every submission and App
  Review answer per Apple team; an open 4.3 on a team holds every other game's submission to it.
- **S4**: the icon shows the game's own character or mechanic — never an emoji, a stock sprite
  or the reference game's signature object.
- **S8 step 6**: record the submission and the answer in the ledger; a 4.3 rejection follows
  the guard's "After a 4.3 rejection".
- **`references/differentiation-gate.md`**: must rows 13 (original main-object and icon art)
  and 14 (own mechanic in the first 30 seconds), the guard in "How to check", and the Fruit
  Mischief lesson.

## 1.17.1 — 2026-10-28

Cleaning up the games after 1.17.0 hit two snags:
- Auto mode refused `git push origin --delete` for merged branches as destructive, so a session
  cannot finish "Closing a branch" for a branch on GitHub. Stage branches pushed by earlier
  sessions (slipchute, nightwall) are left there for the human to delete.
- A commit from a new worktree crashed the pre-commit gate of beamfork, tiptoe-tabby and
  haboob-run: with no `.dart_tool/`, `flutter test --no-pub` fails with `Bad state: No element`
  in native assets.

Changes:
- **Closing a branch, rule 5:** only `main`, tags and a PR's branch are pushed, so a stage branch
  ends with `git branch -d`. A merged PR branch (S6) that auto mode will not delete on GitHub
  goes under `## Deferred (human)` as a command for the human, and it does not fail the S8
  branch check.
- **Background sessions:** run `flutter pub get` in a new worktree before its first commit.

## 1.17.0 — 2026-10-28

A review of the 12 games run so far and 14 background-session transcripts found three problems:
- Each game had copied the previous game's store code, so the same purchase bugs reached 11 of
  them (all fixed and merged on 2026-10-28).
- 223 of 412 failed tool calls were the worktree guard refusing a Bash command.
- Lessons kept only in the project memory never reached a session opened inside a game repo.

Changes:
- **`templates/store/`**: the store every game starts from at S5, with 35 tests and a README.
  - `shop.dart` imports no game code; the game plugs in through two seams, `StoreCatalog` and
    `StoreGrants`.
  - Each update is verified, granted and saved before it is completed, in its own try/catch.
    The save happens even when the purchase was delivered before.
  - StoreKit 2 purchases are verified against `SK2Transaction.unfinishedTransactions()`, because
    the plugin passes an unverified one on as `purchased`.
  - Ask to Buy, a stream error or a pack without a transaction id never leaves the shop stuck.
  - A failed save says the App Store will deliver the purchase again, never "Try again" (a
    second tap pays twice). A restore whose save failed says to restore again.
  - `save_store.dart`: a refused write throws, and unreadable text is kept aside. When storage
    fails at launch the game plays from memory and never writes over the device save.
    `Saved.persist` is for the shop and `Saved.save` for gameplay.
- **`templates/tool/check.sh` and `install_hooks.sh`, installed at S3:** the pre-commit gate
  (format, analyze, test) clears git's hook variables. Left set, a commit from a worktree made
  Flutter report SDK `0.0.0-unknown` and rebuild its tool, in nightwall, lowtide-locks,
  hadal-relay and brinestack. The hook goes into the shared hooks directory the global
  hooksPath dispatcher chains to, because `pre-commit install` refuses there.
- **Background sessions:**
  - one plain command per Bash call, and Edit/Write for files;
  - an empty first commit, pushed, before `EnterWorktree`, which branches from `origin/main`;
  - no `sleep`;
  - zsh quoting, and `<tb>` spelled out each time;
  - sibling skills commit on the stage worktree's branch, and `ExitWorktree` keeps the worktree
    for the merge.
- **Closing a branch** is always a local `--no-ff` merge, then `git worktree remove` and
  `git branch -d`. `gh pr merge` is refused in auto mode, and a PR closes itself as merged.
- **`Waiting on:`** is filled only at a real stop; deferred human steps sit under
  `## Deferred (human)`. A filled `Waiting on:` kept the bot from reporting that chiselturn's S9
  session had stopped with work left. Every parked game had worded its state differently; now
  there is one form: `Now: S8 · 6 waiting for the Apple steps` and
  `Waiting on: S8-apple: build VALID + Apple ID`.
- **Standard routes** are written at their stage instead of being logged as a fallback every
  run:
  - idea-validator ends PARTIAL (8 games);
  - only flutter-init's create step runs (8);
  - logo-designer runs inline with Chrome + Pillow (7);
  - issue-work-loop runs without herdr (8);
  - sibling skills commit on the worktree's branch (6);
  - aso-marketing's plan approval is folded into G4;
  - the agent-readiness scan is asked once, at G4 (6).
- **S2:** the differentiation gate gains own-portfolio rows: core verb, theme/palette/icon, IAP
  lineup, screenshot template, name. 8 of 12 games sold the same unlock + small pack + large
  pack, and slipchute was judged close to three earlier games.
- **S4:** a "close" fresh-eyes finding goes to the human as a question; the build matches the
  chosen mockup (chiselturn, 2026-10-25).
- **S8:** the Sandbox test checks that a bought pack arrives once and survives a relaunch,
  because the store code has met only fakes until then.
- **S9:** the site is listed in the root Pages repo's `robots.txt` and `llms.txt`, since crawlers
  read robots.txt only at the host root.
- **"This machine" notes:**
  - a local run is a web build in Chrome;
  - screenshots come from `tool/screenshot_main.dart`;
  - animations are checked with flutter_test filmstrips;
  - `page_width: 120`.
- **economy reference:** it no longer promises taking back refunded purchases (the plugin passes
  no revocation data), and caps apply to earned items only.
- **Telegram details** moved to `references/telegram-remote.md`; SKILL.md keeps the protocol for
  human stops.

## 1.16.3 — 2026-10-27

A phone answer could sit unread after a late button tap, a decision a session had read could be
lost with that session, and a hyperlink lost its address on the way to the agent.

- A tap the bot reads late (the machine slept, or the bot was busy with the update before it) can
  no longer be acknowledged: Telegram answers "query is too old" (logged 2026-10-26). The answer
  was already recorded, but the error skipped the settled card and the session that acts on it,
  so after a sleep the answer waited for whichever session came next. The acknowledgement is now
  best-effort, and a failed "Đã nhận" message after a typed answer no longer skips the session.
- Every decision is also appended to `.clone/telegram/decisions.jsonl`, which nothing deletes.
  The answer file goes once a session reads it: Slipchute's G4 ("Duyệt, giữ IAP như cũ",
  2026-10-26) was read by a session that then stopped on a permission prompt, and survived only
  in its transcript. Start step 5 records a decision the Gate log lacks.
- Text pasted as a hyperlink ("Link video game mới") reaches the inbox with its URL: Telegram
  keeps a `text_link` address outside the text, which is how Beamfork's S1 lost a video link.
  File captions keep theirs too.
- `/new` session names fold Vietnamese diacritics (`new-game-kho-cuc`, not `new-game-kh-c`).

## 1.16.2 — 2026-10-27

The bridge took a session the background service had retired for a running one. A background
session left an hour idle at a prompt is retired, and once no session is left the service exits,
but `claude agents` keeps listing the retired one as `blocked`. So `/stop` called `claude stop` on
it and got "couldn't confirm 0e999310 was stopped — the background service may be restarting";
`/open` replied "Đã có phiên Claude đang chạy (blocked)" and opened nothing; and a phone answer
opened no session to act on it, so it sat unread. ochrecut, haboob-run, swarm-gates and nibblume
were all listed this way.

- A session counts as running only when `claude agents` gives it a pid. `/stop`, `/open`,
  `/status`, `/games` and opening a session after a phone answer all use that; `/log` and the
  stopped-run warning still see every listed session.

## 1.16.1 — 2026-10-27

`send` delivered only the last of several files. Its `--file` kept one value, so a call with
`--file a --file b --file c` sent c alone and still exited 0. At G2 the phone showed three
direction descriptions but one screenshot, in snowpack-hop, chiselturn, slipchute and ochrecut;
chiselturn's human picked direction A without ever seeing it. G1 and G4 evidence and S4/S5
screenshots lost files the same way.

- `--file` repeats, and each `--caption` labels the `--file` right before it. Files go in order,
  one message each; a failed upload no longer stops the rest (exit 70 names it).
- Every file is checked before anything is sent (exit 66 names the missing ones).
- `send` prints `sent: text, a.png, …`, so a session sees what reached the phone.
- SKILL.md: the evidence bullet shows several captioned files; at S4 the phone gets all three
  direction screenshots, captioned, before G2 is asked.

## 1.16.0 — 2026-10-27

Telegram messages read better on a phone. Before, they were plain text: an agent's question or
reply was one block of about 350 characters (the median; nearly half ran over 400), repeated
the game and gate id the bot had just printed, and buried the action at the end; commands
could not be copied.

- Every message is a card in Telegram HTML: a bold first line with an icon, the game's name as
  status.md spells it, and the step in words (`Duyệt gói App Store (G4)`, `S8-submit` →
  `iOS + nộp`); then short lines; then a 👉 line saying what to tap or type. Commands are
  monospace, so the phone copies them on a tap. Help is grouped under headings.
- `ask` and `send` text is escaped and rendered: backticks become monospace, `**…**` bold,
  `- ` bullets `•`, and a leading "<game> · " is dropped. `send` now uses its REPO for the
  card's title.
- A question settled from the phone or at the computer becomes a card that keeps its subject
  and the decision.
- Markup Telegram rejects (a tag cut at 4000 characters) is sent again as plain text, so
  nothing is lost.
- "Writing for the phone" under "Telegram remote" tells agents how to write for the card:
  no game or gate up front, one-sentence first line, one fact per line, words the human sees,
  commands in backticks, about 600 characters.

## 1.15.0 — 2026-10-27

The Apple-step rule now holds in code. 1.14.0 only wrote it down, so a session that ignored it
could still offer a "done" button, and any reply still settled the question.

- `ask` reserves gate `S8-apple` for the deferred Apple steps: it takes only `--option "Để sau"`
  (exit 64 otherwise). A reply settles it only as that deferral or with both the build number
  and a 9–10-digit Apple ID, which the answer carries as `build` and `apple_id` and the phone
  gets read back. Any other reply ("Build VALID", "xong", a question) keeps the question open,
  reaches the session through the inbox marked `held`, and tells the phone what is missing.
  `close --answered-here` refuses the same (exit 64).
- Rule 13 and S8 step 2: ask the Apple steps as `S8-apple`, and before recording the values check
  that the game repo was cloned in the last 14 days (`gh api …/traffic/clones`). The Mac build
  starts with `git clone`, so 0 means asking once more. Chiselturn's repo had 0 clones when its
  build was reported VALID.

## 1.14.1 — 2026-10-27

The rules no longer name the games they came from. SKILL.md, PROCESS.md and the references load
into every game's session, where another game's name costs tokens, ages, and can read as
something to act on. The incidents stay in this changelog.

- Rules 5 and 13 and the stopped-session warning describe their incidents without the game.
- The repo-naming example uses a made-up name (Moss Lantern → `moss-lantern`).
- The differentiation and economy lessons keep their content without the game's name.
- Pointers to other games' files are gone: the model SPEC, the App Store doc the runbook came
  from, and the IAP fixes cited as a reference.

## 1.14.0 — 2026-10-26

The two newest games looked stuck at S8–S9, unlike the ones before them. Slipchute was: its
background session asked G4 from the S8 worktree, left that worktree with `keep` to start S9 in
`slipchute-site` (`cd`) while G4 was open, and when the answer came a minute later called
`EnterWorktree` with `path:` to go back. From the site repo that is a "permission-root
relocation" prompt auto mode cannot answer, so the session sat on it with all of S8 on an
unmerged branch, and the phone's `claude attach slipchute-site` named no session. Chiselturn's
S8 only looked finished: it was ticked on Telegram button taps, while its private repo was never
cloned onto a Mac, so no build exists and nothing reached Apple. Its pane showed ▶ S8 because of
its `Now:` line, and the resume after "Next sang s9" died at once on "Login expired" without a
warning.

- Rule 5: a background session leaves a stage's worktree only at the stage end. A gate inside
  the stage is waited for there (start `ask`, end the turn), the next stage starts after the
  merge, and a worktree is never re-entered; S8 says so at G4. Telegram sessions start `ask` in
  the background and end the turn (the old text said "in the foreground").
- Site repo (S7, S9): one recipe under Workspace, from the game repo's root without `cd`: a
  linked worktree made with `git -C <site> worktree add`, edited by absolute path and merged
  with `git -C`. A background session refuses Edit in the site's own checkout, which is what
  pushed runs into `cd` and shell-script edits. New site repos ignore `.claude/`.
- `hook`: phone-started sessions also get a PreToolUse hook that refuses `EnterWorktree` with
  `path:` and tells the agent to merge from the repo root instead. The permission-prompt message
  names the game the session works on and gives `claude attach <session id>` (a `/new` session
  is named after the idea), with `CLAUDE_CONFIG_DIR=…` when the session runs under another
  config folder (an mcc profile); the bot's other attach hints use the same form.
- Steps pane and `/games` read the newest `.clone/status.md` of the repo and its worktrees, so a
  stage running in a worktree shows its real step (the pane names the worktree), not `main`'s
  copy from the stage start. The current stage comes from `Now:` only when it starts
  `S<n> ·`: Chiselturn's `Now: S8 done: …` had shown ▶ S8 and Snowpack Hop's
  `Now: S0–S7 … done` ▶ S0. A session held by a permission prompt shows as such on `/games`,
  ahead of "chờ bạn", with its attach command.
- Rule 13 and S8 step 2: the deferred Apple steps resume only on two values the human reads off
  App Store Connect and types: the VALID build number and the app's Apple ID. Their question
  has `Để sau` as its only button. Chiselturn's offered "Build VALID" and "Có vấn đề"; one tap
  ticked the steps, `/ship` then tagged "build 1", and "Đã nộp" recorded a submission, all
  without a build. Snowpack Hop's offered "Để sau" too, and its steps are still deferred.
- The stopped-session warning also fires when an answer of yours is still unread, even with
  something in `Waiting on:` (Chiselturn had "Apple review" there).
- S9 is ticked once `search-optimizer` and `design-optimizer` ran on the game's own site;
  Chiselturn's S9 had applied Beamfork's audit fixes instead of running either. Store badges and
  post-launch checks wait under `## Deferred (human)`.

## 1.13.0 — 2026-10-19

A game that only waits on the human (Nightwall, at S8's App Store steps) stayed in `/games` with
no way to take it off: the list is every registered repo plus every `GAMES_DIR/*/.clone/status.md`.

- `/hide <game>` takes a game off the `/games` list and `/unhide <game>` brings it back; the list
  ends with `Đang ẩn: …` while any are hidden. A partial name works, as with `/use`.
- Hiding touches only the list: questions, answers, stall and stop warnings, `/use`, `/status`
  and `/log` still see the game. `/open <game>` unhides it. The hidden repos live in
  `~/.local/state/game-clone-pipeline/telegram/hidden.json`.

## 1.12.1 — 2026-10-19

`/games` on Telegram was a monospace block of raw `Now:` / `Waiting on:` lines and session
states (`busy · working`), hard to read on a phone.

- Each game is now a short card in plain HTML: bold name with one state badge (❓ asking you,
  🟢 running, ⏸ waiting on you, 🟡 Claude idle, 💤 stopped with `/open <game>`, ✅ done,
  ⚪ not started), the stage's short label (`S8 · iOS + nộp`), and the first clause of
  `Waiting on:` cut to 80 characters. `/status <game>` still shows everything.

## 1.12.0 — 2026-10-19

Fixes a Telegram run (Haboob Run) that stopped overnight at the start of S7: the session ran
`landing-page-generator`, printed its copy with the skill's own `Result: COMPLETE … Decision: No
approval needed.` block, and ended its turn before the site repo existed. A background session
that ends its turn is never prompted again, and the bot said nothing: its stall check only looked
at busy sessions, and the session, started by `/new` from `GAMES_DIR` under the idea's name, did
not count as the game's. The resume the phone started the next morning died on an expired login,
also unseen.

- Hard rule 16: only a human stop (or the Final report after S9) ends the turn; a sibling
  skill's final report closes its step, not the stage. Setup step 4 and S7 say so where it bit.
- `telegram_bridge.py`: in away mode `serve` also warns once when a game's sessions have all
  stopped 10 minutes to 24 hours ago with stages left, nothing in `Waiting on:` and no question
  pending, quoting the session's last reply (so "Login expired" reaches the phone) and
  `/open <game>`. A session `/stop`ped from the phone is left alone.
- Every subcommand run on a repo from inside a Claude session records `CLAUDE_CODE_SESSION_ID`
  in `.clone/telegram/sessions.json`, and such a session belongs to the game, so `/games`,
  `/log`, `/stop` and both warnings see `/new` sessions too.

## 1.11.0 — 2026-10-17

Fixes a Telegram run (Lowtide Locks) that sat two days at the start of S5: the session `cd`'d into
a previous game's repo to read its store code, then called `EnterWorktree` from there, and the
call held until the human was back at the computer. The phone could not see or restart it.

- Hard rule 15: stay in the game repo; read other repos by absolute path or `git -C`.
- Rule 5: a background session works each stage in one worktree, entered by name from the repo
  root and closed at the stage end like any other branch.
- S5: a missing human playtest no longer stalls G3; it is listed under `## Deferred (human)`.
- `telegram_bridge.py`: a session belongs to a game when it runs in the repo or one of its
  worktrees, or carries the game's name, so `/games`, `/log`, `/stop`, `/open` and the resume
  after a phone answer see sessions working in `.claude/worktrees/`. Resume sessions refused as
  "Workspace not trusted" start from the repo's parent with the repo path in the prompt, and the
  phone is told how to fix it for good.
- `serve` warns the phone once per stall in away mode when a busy session has written nothing for
  30 minutes with no question pending, naming its last tool call. Free text with no pending
  question is answered with the game's step and session state; `help` without a slash returns
  the command list.

## 1.10.0 — 2026-10-15

- Temporary branches no longer outlive their stage (rule 5). `test-coverage` (S3),
  `flutter-ui-revamp` (S4) and `issue-work-loop` (S6, one branch and PR per issue, which stops
  at CLEAN without merging) each leave a branch; the stage now ends by merging it into `main`
  and deleting it locally and on GitHub, with one "Closing a branch" recipe (`gh pr merge
  --squash --delete-branch`, or `merge --no-ff` + `branch -d` + remote delete) and analyze + test
  on `main` afterwards. Unmerged work is deleted only on the human's answer.
- S8 starts with a branch check: only `main`, no open PR. The status template tracks it.

## 1.9.0 — 2026-10-15

- The Telegram bot no longer lives inside a Claude session: `telegram_bridge.py serve` serves
  every game (`GAMES_DIR/*/.clone/status.md` plus `register`ed repos) and `install-service` runs it
  as a systemd user service (`KillMode=process`, carries `CLAUDE_CONFIG_DIR`), so the phone works
  with no Claude open. `watch REPO` now registers the repo and serves only when no service does.
- The phone opens Claude sessions: `/open <game>` and `/new <idea>` start `claude --bg -n <game>
  --permission-mode auto` with a resume or start prompt; an answer for a game with no live session
  starts one, which reads it with the new `answers` subcommand. `/games`, `/use`, `/log`, `/stop`
  (background sessions only). Phone-started sessions get a Notification hook (`hook` subcommand)
  that reports a waiting permission prompt; `claude attach <game>` takes over at the computer.
- Away mode and the current game are global (`~/.local/state/game-clone-pipeline/telegram/`);
  `mode` takes no repo. Questions are prefixed with the game name and route by question id.
- The setup and serve errors name a 409 Conflict as another program polling the same bot.
- Checked against a real `claude --bg` session (v2.1.300, auto mode allowed by the org policy):
  the bot reads the short id from `backgrounded · <id> · <name>` and uses it for `attach`,
  `logs` and `stop`; `/games` shows `status · state`; `/log` shows the session's last prompts,
  replies and tool calls from its transcript, because `claude logs` returns a raw screen stream.

## 1.8.0 — 2026-10-15

- Telegram remote (optional, hard rule 14): `scripts/telegram_bridge.py` (stdlib) with `setup`,
  `watch`, `ask`, `close`, `mode`, `send`, `inbox`. At the computer nothing changes; in away
  mode (`/away` on the phone or `mode away`) every human stop is also asked on Telegram
  with buttons, the first answer wins (`close --answered-here` from the chat, or the phone), and
  the gate log notes where it was decided. `/back` or an answer at the computer silences it.
- Away mode keeps the machine awake with a `systemd-inhibit` sleep lock (`caffeinate` on macOS),
  warns the phone before a sleep it cannot block, and reports on wake; queued Telegram messages
  are processed then (24 h).
- Commands `/status`, `/pause`, `/resume`, `/skip`, `/redo`, `/note` and free text land in
  `.clone/telegram/inbox.jsonl`, read at every step boundary; videos, APKs and data files sent
  to the bot are saved into the git-ignored `.clone/` folders (20 MB Bot API limit). Only the
  allowlisted chat counts; the token lives in `~/.config/game-clone-pipeline/telegram.env`.
- `templates/status.md` gains a `Remote:` line; `.clone/telegram/` is git-ignored at S0.

## 1.7.0 — 2026-10-14

- Names: the game repo (folder and GitHub) is the game's name in kebab-case (`nightwall`), the
  landing repo is `<game>-site`, and neither ever ends in `-clone`. Before G1 the repo uses a
  working slug of the idea; right after G1 it is renamed (`gh repo rename`, folder move, remote
  URL, status.md header, steps pane reopened). The S3 note no longer assumes a `<game>-clone`
  folder. PROCESS.md title now tracks the skill version (it showed 1.3.0).

## 1.6.0 — 2026-10-14

- Hard rule 13: the Apple-account steps of S8 (App Store Connect web setup, Mac build and upload,
  TestFlight test) are deferred by default and listed under `## Deferred (human)` in status.md;
  the run continues with store assets, ASO, the review check and S9 site work, and only ship,
  release upload and submission wait for them. G4 can pass as partial without a build.

## 1.5.0 — 2026-10-14

- Hard rule 12: `asc` is deferred. The agent runs no `asc` command; S8 writes
  `docs/APP-STORE-CONNECT.md` (bundle id, IAP ids and prices, URLs, review notes, checklist) and
  `store/` for the human to enter in the App Store Connect web UI. S9 review/analytics follow-up
  is read by the human. The runbook keeps its `asc` commands behind a deferral banner.

## 1.4.0 — 2026-10-14

- Hard rule 11: no GitHub Actions anywhere. No `.github/workflows/` in the game or site repo, no
  CI job; checks run on the dev machine (analyze, test, simulator, pre-commit hooks).
- S6 passes the rule to `codebase-modernizer`, so a missing CI is no longer a finding and the plan
  never schedules a workflow task (this run had added `ci.yml`, which the account could not run).
- S7 enables GitHub Pages from the `main` branch with `gh api` instead of a workflow;
  `templates/pages.yml` is removed. The site repo is public so Pages stays free.

## 1.3.0 — 2026-10-13

- S1 takes whatever the human has, one source being enough: APK (REA), game data files in the
  new git-ignored `.clone/data/`, a gameplay video of any length (short clips replace the 30–60
  min session), store pages the agent fetches, or a written description. A precedence rule
  settles conflicts (video > data > APK > description) and ❓ requests ask for the cheapest
  missing piece.
- Ideas with no original are in scope: S0 picks the 1–3 closest successful games as references,
  confirmed at G0, and SPEC and the differentiation gate compare against them. The skill
  description no longer sends such ideas to flutter-factory.
- `.gitignore` entries for `.clone/` are added at S0, since the human may hand files over at the
  start; status.md template carries the reference games and evidence sources.
- Skill description cut to 1,019 characters (it was 1,118, over the 1,024 limit).

## 1.2.0 — 2026-10-13

- Steps pane: `scripts/steps_pane.py open <repo>` splits the agent's herdr pane and shows S0–S9
  on the right (done ✓, current ▶, gate passed ✓, waiting on the human ⏸), redrawn whenever
  `.clone/status.md` changes; it reuses an open pane, and `close` removes it. Without herdr,
  `once` prints the same block for the chat.
- `status.md` gains `Now:` and `Waiting on:` lines; hard rule 10 has the agent keep them current.

## 1.1.1 — 2026-10-13

- S3 runs `flutter-init` in place inside the existing game repo: `--project-name` in snake_case
  (a `<game>-clone` folder name makes `flutter create .` exit 1), no second `git init`, and our
  `.gitignore` moved aside and appended back, because `flutter create` keeps an existing one and
  would leave `build/` and `.dart_tool/` unignored.
- Hard rule 1 names the ignored folders (`.clone/reference/`, `.clone/apk/`); `.clone/status.md`
  is tracked so a run can resume. It used to say all of `.clone/` was ignored, contradicting the
  "commit status.md" steps.
- Six gates, not five; PROCESS.md title shows the current version.

## 1.1.0 — 2026-10-13

- Drop the Google Play stage: the pipeline releases to the App Store only.
- Stages renumbered S0–S9 (landing polish is now S9).

## 1.0.0 — 2026-10-13

- First version. Eleven stages at 1.0.0 (S0–S10) with human gates G0, G0b, G1, G2, G3, G4 and a
  resumable `.clone/status.md`.
- S1 combines APK facts from REA with a human gameplay recording; `scripts/contact-sheet.sh`
  turns recordings into timestamped contact sheets for the evidence-backed SPEC.
- Differentiation gate and economy guide decided before any art (lessons from Coin Cubby).
- English-only games; commit after every stage with the `commit` skill; main + tags only.
- iOS is prepared on Ubuntu and built/uploaded on a Mac (`templates/build-ios.sh`,
  `ExportOptions.plist`, runbook with `asc` commands); no CI build.
- Landing repo templates: privacy, support, GitHub Pages workflow.
