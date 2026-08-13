import json
from pathlib import Path

import ru_de_translator.config as config_module


def test_normalize_config_migrates_and_clamps_values():
    config = config_module.normalize_config(
        {
            "translation_provider": "invalid",
            "tts_provider": "invalid",
            "ctranslate2_tokenizer_name": "~/old-tokenizer",
            "practice_repeats": 999,
            "practice_pause": -2,
        }
    )

    assert config["translation_provider"] == "ctranslate2"
    assert config["tts_provider"] == "edge_tts"
    assert config["ctranslate2_tokenizer_path"] == "~/old-tokenizer"
    assert "ctranslate2_tokenizer_name" not in config
    assert config["practice_repeats"] == 20
    assert config["practice_pause"] == 0.0


def test_save_is_atomic_and_load_merges_defaults(tmp_path, monkeypatch):
    config_file = tmp_path / "config.json"
    monkeypatch.setattr(config_module, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(config_module, "CONFIG_FILE", config_file)

    config_module.save_config({"practice_repeats": 5, "gemini_api_key": "secret"})
    loaded = config_module.load_config()

    assert loaded["practice_repeats"] == 5
    assert loaded["gemini_api_key"] == "secret"
    assert loaded["translation_provider"] == "ctranslate2"
    assert json.loads(config_file.read_text())["practice_repeats"] == 5
    assert list(Path(tmp_path).glob("config-*.json")) == []


def test_load_recovers_from_non_object_json(tmp_path, monkeypatch):
    config_file = tmp_path / "config.json"
    config_file.write_text("[]")
    monkeypatch.setattr(config_module, "CONFIG_FILE", config_file)

    assert config_module.load_config()["translation_provider"] == "ctranslate2"
