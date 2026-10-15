# Changelog

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
