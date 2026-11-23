"""Turn a trained adapter into a model Ollama can run.

Usage: uv run python export.py <run folder> --name storyboard-qwen35:r1 [--base Qwen/Qwen3.5-9B]

<run folder> is the --out folder of finetune.py (it holds adapter/). Ollama no longer loads
LoRA adapters, so the adapter is added into the base weights shard by shard (little memory),
the result is converted to GGUF and quantized with llama.cpp, and the model is registered in
Ollama with the chat renderer and parser of the base family, so a request is laid out exactly
as during training. Needs llama.cpp (LLAMA_CPP, default ~/.local/opt/llama.cpp) with
build/bin/llama-quantize built, and the ollama binary (OLLAMA, default: on the PATH or
~/.local/opt/ollama/bin/ollama). Large intermediate files are deleted unless --keep.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

LLAMA = Path(os.environ.get("LLAMA_CPP", Path.home() / ".local/opt/llama.cpp"))


def ollama_bin() -> str:
    found = os.environ.get("OLLAMA") or shutil.which("ollama")
    return found or str(Path.home() / ".local/opt/ollama/bin/ollama")


def merge(base: Path, adapter: Path, out: Path) -> int:
    """Write base + adapter as full weights; returns how many matrices changed."""
    import torch
    from safetensors import safe_open
    from safetensors.torch import save_file

    config = json.loads((adapter / "adapter_config.json").read_text())
    scale = config["lora_alpha"] / config["r"]
    lora: dict[str, dict[str, torch.Tensor]] = {}
    with safe_open(str(adapter / "adapter_model.safetensors"), "pt") as f:
        for key in f.keys():
            m = re.fullmatch(r"base_model\.model\.(.+)\.lora_([AB])\.weight", key)
            if not m:
                raise SystemExit(f"unexpected adapter tensor {key}")
            lora.setdefault(m[1] + ".weight", {})[m[2]] = f.get_tensor(key)
    out.mkdir(parents=True, exist_ok=True)
    changed = 0
    for shard in sorted(base.glob("*.safetensors")):
        tensors = {}
        with safe_open(str(shard), "pt") as f:
            for key in f.keys():
                w = f.get_tensor(key)
                if key in lora:
                    delta = (lora[key]["B"].float() @ lora[key]["A"].float()) * scale
                    w = (w.float() + delta).to(w.dtype)
                    changed += 1
                tensors[key] = w
        save_file(tensors, str(out / shard.name), metadata={"format": "pt"})
        print(f"  merged {shard.name}")
    for extra in base.iterdir():
        if extra.suffix != ".safetensors" and extra.is_file():
            shutil.copy(extra, out / extra.name)
    if changed != len(lora):
        raise SystemExit(f"only {changed} of {len(lora)} adapter matrices found in the base")
    return changed


def run(cmd: list[str]) -> None:
    print("  $ " + " ".join(cmd))
    env = {**os.environ, "PYTHONPATH": str(LLAMA / "gguf-py")}  # llama.cpp's own gguf package
    subprocess.run(cmd, check=True, env=env)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--name", required=True, help="the Ollama model name, e.g. storyboard-qwen35:r1")
    ap.add_argument("--base", default="Qwen/Qwen3.5-9B")
    ap.add_argument("--quant", default="Q4_K_M")
    ap.add_argument("--renderer", default="qwen3.5", help="Ollama renderer and parser of the base family")
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()

    from huggingface_hub import snapshot_download
    base = Path(snapshot_download(args.base))
    quantize = LLAMA / "build/bin/llama-quantize"
    if not quantize.exists():
        print(f"FAIL {quantize} is missing: build it (see references/local-model.md)")
        return 1
    work = args.run_dir.resolve()
    merged, wide = work / "merged", work / "merged-bf16.gguf"
    final = work / f"model-{args.quant}.gguf"

    print(f"[merge] {merge(base, work / 'adapter', merged)} matrices")
    run([sys.executable, str(LLAMA / "convert_hf_to_gguf.py"), str(merged), "--outtype", "bf16",
         "--outfile", str(wide)])
    run([str(quantize), str(wide), str(final), args.quant])
    (work / "Modelfile").write_text(
        f"FROM {final}\nRENDERER {args.renderer}\nPARSER {args.renderer}\n"
        "PARAMETER temperature 0.4\nPARAMETER top_k 20\nPARAMETER top_p 0.95\n", encoding="utf-8")
    run([ollama_bin(), "create", args.name, "-f", str(work / "Modelfile")])
    if not args.keep:
        shutil.rmtree(merged)
        wide.unlink()
    print(f"RESULT: PASS {args.name} <- {final} ({final.stat().st_size / 2**30:.1f} GB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
