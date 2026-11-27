# The storyboard model on this machine

`scenes` can be written by a language model running on this machine instead of by hand. The
model only writes the storyboard: the dialogue, `metadata.json` and the look at the check images
still need a person or an assistant.

## How the pipeline uses it

`scripts/pipeline/config.json` → `storyboard`:

```json
"storyboard": {"provider": "ollama", "url": "http://127.0.0.1:11434", "model": "storyboard-qwen35:r3",
               "retries": 3, "temperature": 0.4, "num_ctx": 8192, "timeout_s": 300}
```

- `provider: "none"` (the default) turns it off: nothing changes.
- When `dialogue.json` has no `scenes`, `run.py` asks the model before `validate` and writes its
  storyboard into `dialogue.json`. A storyboard already in the file is never replaced.
- The answer is held to a JSON schema built from `scripts/video/src/toon/rig.json`, so names
  (poses, sets, characters) are always valid. It is then checked by the same validator as a
  hand-written storyboard; errors and warnings go back to the model, `retries` more times
  (fewer when it gives the same answer twice).
- Tries used up with cue errors left: the beats whose word is not said in their scene are
  dropped and such labels move to the scene that says the word (`WARN ... cue(s) were not
  said`), so one wrong word does not cost the whole storyboard.
- No valid answer (or no server): a `WARN`, and the plain generated storyboard is used.
- `uv run python run.py <level> --storyboard-only` writes the storyboard and stops;
  `uv run python storyboard.py <level>` does the same without the dialogue checks.

## Running the server

Ollama, installed without root:

```bash
mkdir -p ~/.local/opt/ollama && cd ~/.local/opt/ollama
curl -fsSL https://ollama.com/download/ollama-linux-amd64.tar.zst | tar --zstd -x
nohup ./bin/ollama serve > serve.log 2>&1 &
```

The official install extracts the same archive into `/usr` with `sudo`. The model
file itself is not in the repository; rebuild it with the steps below, or copy
`model-Q4_K_M.gguf` and its `Modelfile` from the machine that made it and run
`ollama create <name> -f Modelfile`.

## Training

Everything lives in `scripts/train/` (its own `uv` project: torch, unsloth, transformers 5).

1. **Examples.** Dialogues with storyboards that pass the validator with no warning, one folder
   per episode (`<data>/<slug>/<LEVEL>/dialogue.json`). `scripts/train/dataset-brief.md` is
   the brief to have them written in batches (seven themes each, in parallel): both rules
   files, eight new words per theme, A2 and B1 as two conversations, varied sets, times, kinds,
   poses and emotions, the validator rerun until `RESULT: PASS` with no `WARN`.
2. **Dataset.** `python3 make_dataset.py <data>` writes `_jsonl/train.jsonl` and `eval.jsonl`.
   Whole episodes go to one side. Once `eval.jsonl` exists it stays the evaluation set, so
   numbers stay comparable as the data grows (`--resplit` draws it again).
   `--repairs 30` (the default) also turns 30% of the training levels into repair lessons:
   a storyboard with typical mistakes put in (a misspelt cue, a cue from another scene, a label
   in the wrong scene, a cue said twice, a missing line, a beat for someone absent, a scene too
   long), the checker's words about it, and the right storyboard. Without them a model rarely
   uses the checker's words and tends to send the same answer back.
3. **Train.** `uv run python finetune.py <data>/_jsonl --out <run> [--epochs 3]`: a LoRA adapter
   on the base model loaded in 4-bit (`Qwen/Qwen3.5-9B` by default). Each example is laid out
   as the server lays out a request with thinking off; only the answer counts in the loss.
   On a 12 GB card: about 8 GB at peak, about 9 s per example per epoch (a repair lesson is
   about 6500 tokens, half as long again). `--dry` only counts tokens.
4. **Export.** `uv run python export.py <run> --name storyboard-qwen35:rN`: adds the adapter
   into the base weights, converts to GGUF, quantizes to Q4_K_M and registers the model in
   Ollama with the base family's renderer and parser. Ollama no longer loads LoRA adapters,
   hence the merge.
   - Needs llama.cpp (`LLAMA_CPP`, default `~/.local/opt/llama.cpp`) with `llama-quantize` built
     (`cmake -B build -DGGML_CUDA=OFF && cmake --build build --target llama-quantize`; `cmake`
     can come from `uv tool install cmake`).
   - The llama.cpp checkout must write the tensor layout the llama.cpp inside Ollama reads.
     Newer llama.cpp merges Qwen3.5 tensors on convert (`attn_qkv_gate`, `ssm_beta_alpha`) and
     an older Ollama then fails with `tensor 'blk.0.ssm_beta.weight' not found`: use a
     `git worktree` of the commit before that change and point `LLAMA_CPP` at it.
5. **Measure.** `python3 eval_storyboard.py <data> --models <name> --out <file>` runs the model
   on the evaluation dialogues and prints: valid (after repairs), first try, salvaged (valid
   only after dropping cues), tries, seconds,
   and the shape of the storyboards (scenes, places, beats per scene, poses, emotions, labels),
   next to the plain storyboard (floor) and the stored one (ceiling). `--out` keeps every
   answer and the validator's last complaints for each failure.

## Training again later

A run starts from the base model unless `--init-adapter <run>/adapter` is given; then it carries
on from that adapter (same `--rank`). One more epoch at `--lr 1e-4` from r3's adapter on r3's data
(r4) took first try from 33% to 50% over two passes; a second such epoch (r5) gained nothing.
Training from the base model on 1211 dialogues instead of 707 (r7) tied r4 (50%) on these 12
dialogues, and one more epoch from r7 (r8) stayed there too: more of the same kind of data did not
help by itself. With new data, start from the base model: add new themes to `<data>`,
rerun `make_dataset.py` (the evaluation set stays the same), train with a new `--out`, export
under a new tag (`storyboard-qwen35:r4`), measure, and compare the rows. Keep `_jsonl/eval.jsonl`
and each run's `training.json` and `eval-<run>.json`: they are what makes the next run
comparable. On a 12 GB card about 700 dialogues plus 30% repair lessons took 5.3 hours for
two epochs, at 8.2 GB; 1211 dialogues plus repairs took 8.4 hours. `export.py` needs about 45 GB
of free disk while it runs (merged weights, a bf16 GGUF, the Q4 file and Ollama's copy of it); with
less, `llama-quantize` stops with "iostream error".

## What to look at before turning it on

- `valid` close to 1 and `first_try` high: each extra try costs about half a minute. The model
  samples with no seed, so one pass over 12 dialogues can swing by 4 in `first_try`: measure each
  run twice before comparing.
- `beats_per_scene`, `poses`, `label_cover` close to the reference row: a valid but empty
  storyboard is not better than the plain one.
- Render one or two episodes with a model storyboard and look at the contact sheets.
