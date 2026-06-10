import re

file_path = "/Users/jenyanovak/Projects/active/ru-de-translator/ru_de_translator/.venv/lib/python3.13/site-packages/mlx_audio/tts/models/qwen3/qwen3.py"

with open(file_path, "r") as f:
    content = f.read()

patch = """@dataclass
class ModelConfig(Qwen3ModelConfig):
    tokenizer_name: str = None
    sample_rate: int = 24000

    @classmethod
    def from_dict(cls, config):
        if "talker_config" in config:
            merged = config.copy()
            merged.update(config["talker_config"])
            return super().from_dict(merged)
        return super().from_dict(config)
"""

content = re.sub(
    r"@dataclass\nclass ModelConfig\(Qwen3ModelConfig\):\n    tokenizer_name: str = None\n    sample_rate: int = 24000\n",
    patch,
    content,
)

with open(file_path, "w") as f:
    f.write(content)

print("Patched successfully.")
