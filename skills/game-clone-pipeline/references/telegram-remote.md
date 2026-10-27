# Telegram remote (optional, SKILL.md rule 14)

Read once per session when `~/.config/game-clone-pipeline/telegram.env` exists (SKILL.md,
Start step 5). The protocol for every human stop (`ask` in the background, the same question in
the chat) stays in SKILL.md under "Telegram remote"; this file is the rest.

The human decides at the computer while they sit there and on the phone while they are away.
`scripts/telegram_bridge.py serve` is the only reader of the bot and serves every game
(`GAMES_DIR/*/.clone/status.md` plus registered repos). Installed once with `install-service`
it runs as a systemd user service, so the phone works even with no Claude session open; without
it, `watch` serves from inside the session. The agent talks to it through these subcommands
(`<tb>` = `python3 <skill-dir>/scripts/telegram_bridge.py`):

- **Sessions from the phone.** `/open <game>` starts `claude --bg -n <game> --permission-mode
  auto` in that repo with a resume prompt; `/new <idea or store URL>` starts one in `GAMES_DIR`;
  a Telegram answer for a game with no live session starts a resume session too. Such sessions
  carry a hook that tells the phone when a permission prompt is waiting (naming the game and the
  session id) and refuses `EnterWorktree` with `path:` (SKILL.md rule 5). At the computer,
  `claude attach <id>` with the id the bot sends takes the session over (a `/new` session is
  named after the idea, not the game). The bot counts a session as a game's
  when it runs in the repo or one of its worktrees, or is named after the game. `claude --bg`
  refuses a folder Claude was never opened in ("Workspace not trusted"), which is every repo the
  pipeline created from the phone: the bot then starts the session from the repo's parent with the
  repo path in the prompt and tells the phone; running `claude` once in the repo at the computer
  fixes it for good.
- **Stalls and status.** In away mode the bot warns the phone once when a busy session has
  written nothing for 30 minutes while no question is pending (most likely a prompt only the
  computer can answer), naming the last tool call and how to `/log`, `/stop` + `/open`, or
  attach. It also warns once when a game's sessions have all stopped 10 minutes to 24 hours
  ago with stages left, no question pending, and nothing in `Waiting on:` or an answer still
  unread (the session quit without asking, or died on an expired login before reading the
  answer), quoting the session's last reply and
  `/open <game>`. A session counts as the game's once it runs any subcommand on the repo
  (`register`, `inbox`, `ask`, …), so a `/new` session working from `GAMES_DIR` under the
  idea's name is seen too. Free text with no pending question is answered with the game's `Now:`, `Waiting on:`
  and session state; `help` without the slash returns the command list.
- **A session started from Telegram** (its prompt says so): the human is away, so run
  `answers` and `inbox` first, ask every human stop with `ask` started as in SKILL.md's "Every human stop" step 1, then
  end the turn (no chat-only question; inside a stage, from its worktree, SKILL.md rule 5), and send the
  evidence with `send`. For `/new`, create the repo under `GAMES_DIR`
  with a working slug without asking for the parent folder, run `<tb> register <repo>`, then ask
  the remaining start questions (sources, reference games) through `ask`.
- **Modes.** `here` (default): Telegram stays silent. `away`: the human typed `/away` on the
  phone, or said in the chat that they are leaving (then run `<tb> mode away`). In away
  mode the bot asks the pending question, pushes `Now:` / `Waiting on:` changes and keeps the
  machine awake (a `systemd-inhibit` sleep lock; the screen may still lock). `/back`, or any
  answer typed at the computer, returns to `here`. A machine that sleeps anyway runs nothing:
  messages wait on Telegram (24 h) and the bot reports them when it wakes.
- **Writing for the phone.** `ask` and `send` text lands in a card whose bold first line
  already names the game and the step, and a question gets a 👉 line for its buttons. So no
  game name or gate id up front. First line: what happened or what you need, one sentence.
  Then short lines, `- ` bullets or numbered steps, one fact each, a blank line between
  blocks. Use the words the human sees on screen, not stage codes or files they will not open;
  commands in backticks (the phone copies them on a tap), `**…**` for the one thing that
  matters. Buttons of 1–3 words. Keep it near 600 characters; send the rest as a file.
- **Evidence for a gate** while away: `<tb> send <repo> "<summary>" --file <path> --caption "<what
  it shows>"` with what the human would look at (SPEC excerpt, S4 direction screenshots, simulator
  numbers, the review report). Repeat `--file`, each followed by its own `--caption`, to send
  several in one call: they arrive in order, one message each. The command prints `sent: …`, and
  every file must be in that line. Up to 50 MB per file.
- **Inbox.** `<tb> inbox <repo>` prints unread JSON lines; run it at every stage and numbered
  step boundary and before each human stop. `/pause` → stop after the current step with
  `Waiting on: resume` (ask for it as a human stop); `/resume` → continue; `/skip <step>`,
  `/redo <stage>` → do it when it is not a human-only decision (SKILL.md rule 9) and log it under
  Fallbacks and deviations; `/note` and free text → act on them like a chat message; `file` →
  a new S1 source, already saved under `.clone/`; `file_too_big` → ask for a link or a shorter
  clip.
