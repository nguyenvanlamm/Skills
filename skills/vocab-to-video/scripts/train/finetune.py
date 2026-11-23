"""Teach a base model to write storyboards: a LoRA adapter trained on train.jsonl.

Usage: uv run python finetune.py <folder with train.jsonl> --out <folder> [--base Qwen/Qwen3.5-9B]

The base model is loaded in 4-bit so that a 9B model fits a 12 GB card; only the adapter is
trained and saved (<out>/adapter). Each example is laid out exactly as the model server lays
out a request with thinking off, and only the answer counts in the loss.
`--dry` stops after measuring the examples, without loading the model weights.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def encode(tokenizer, example: dict) -> dict:
    """Token ids of one example, with the prompt masked out of the loss."""
    *asked, answer = example["messages"]
    prompt = tokenizer.apply_chat_template(asked, tokenize=False, add_generation_prompt=True,
                                           enable_thinking=False)
    head = tokenizer(prompt, add_special_tokens=False)["input_ids"]
    tail = tokenizer(answer["content"] + "<|im_end|>\n", add_special_tokens=False)["input_ids"]
    return {"input_ids": head + tail, "attention_mask": [1] * (len(head) + len(tail)),
            "labels": [-100] * len(head) + tail}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("data", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--base", default="Qwen/Qwen3.5-9B")
    ap.add_argument("--epochs", type=float, default=3)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--max-tokens", type=int, default=8192,
                    help="longer examples are left out (a repair lesson is about 6500 tokens)")
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    if args.dry:
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(args.base)
    else:
        from unsloth import FastLanguageModel  # must be imported before transformers
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=args.base, max_seq_length=args.max_tokens, load_in_4bit=True, full_finetuning=False)
        tokenizer = getattr(tokenizer, "tokenizer", tokenizer)  # a processor wraps the text tokenizer

    data = [encode(tokenizer, r) for r in rows(args.data / "train.jsonl")]
    sizes = sorted(len(d["input_ids"]) for d in data)
    kept = [d for d in data if len(d["input_ids"]) <= args.max_tokens]
    print(f"{len(data)} examples, tokens min {sizes[0]} median {sizes[len(sizes) // 2]} max {sizes[-1]}; "
          f"{len(kept)} kept (limit {args.max_tokens})")
    if args.dry:
        print(tokenizer.decode(data[0]["input_ids"])[-900:])
        return 0

    import torch
    from transformers import Trainer, TrainingArguments

    model = FastLanguageModel.get_peft_model(
        model, r=args.rank, lora_alpha=args.rank, lora_dropout=0, bias="none",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        use_gradient_checkpointing="unsloth", random_state=3407, max_seq_length=args.max_tokens)

    def collate(batch: list[dict]) -> dict:
        width = max(len(b["input_ids"]) for b in batch)
        pad = {"input_ids": tokenizer.pad_token_id or 0, "attention_mask": 0, "labels": -100}
        return {k: torch.tensor([b[k] + [fill] * (width - len(b[k])) for b in batch]) for k, fill in pad.items()}

    trainer = Trainer(model=model, train_dataset=kept, data_collator=collate, args=TrainingArguments(
        output_dir=str(args.out / "checkpoints"), num_train_epochs=args.epochs,
        per_device_train_batch_size=1, gradient_accumulation_steps=4, learning_rate=args.lr,
        lr_scheduler_type="cosine", warmup_steps=5, logging_steps=5, save_strategy="epoch",
        optim="adamw_8bit", weight_decay=0.01, seed=3407, report_to="none"))
    began = time.time()
    result = trainer.train()
    model.save_pretrained(str(args.out / "adapter"))
    tokenizer.save_pretrained(str(args.out / "adapter"))
    peak = torch.cuda.max_memory_allocated() / 2**30
    summary = {"base": args.base, "examples": len(kept), "epochs": args.epochs, "rank": args.rank,
               "loss": round(result.training_loss, 4), "minutes": round((time.time() - began) / 60, 1),
               "peak_vram_gb": round(peak, 1),
               "log": [h for h in trainer.state.log_history if "loss" in h]}
    (args.out / "training.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"RESULT: PASS loss {summary['loss']} in {summary['minutes']} min, peak {summary['peak_vram_gb']} GB "
          f"-> {args.out / 'adapter'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
