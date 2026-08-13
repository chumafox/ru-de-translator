#!/usr/bin/env python3
"""Download the tokenizer and build the quantized CTranslate2 model."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from transformers import AutoTokenizer

MODEL_ID = "Helsinki-NLP/opus-mt-tc-big-zle-de"
CONFIG_DIR = Path.home() / ".config" / "ru_de_translator"
MODEL_DIR = CONFIG_DIR / "opus-zle-de-ct2"
TOKENIZER_DIR = CONFIG_DIR / "tokenizer"


def main() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not (TOKENIZER_DIR / "tokenizer_config.json").exists():
        print(f"Downloading tokenizer: {MODEL_ID}")
        AutoTokenizer.from_pretrained(MODEL_ID).save_pretrained(TOKENIZER_DIR)
    else:
        print(f"Tokenizer already exists: {TOKENIZER_DIR}")

    if (MODEL_DIR / "model.bin").exists():
        print(f"CTranslate2 model already exists: {MODEL_DIR}")
        return

    converter = shutil.which("ct2-transformers-converter")
    if converter is None:
        raise SystemExit("ct2-transformers-converter was not installed by ctranslate2")
    print(f"Converting and quantizing model into: {MODEL_DIR}")
    subprocess.run(
        [
            converter,
            "--model",
            MODEL_ID,
            "--output_dir",
            str(MODEL_DIR),
            "--quantization",
            "int8",
            "--force",
        ],
        check=True,
    )
    print("Translation model is ready.")


if __name__ == "__main__":
    main()
