import json
import os
from pathlib import Path

# BASE_DIR 指向 cross_memory_data 根目录
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
WHITELIST_DIR = DATA_DIR / "whitelist"
ORIGINAL_DIR = DATA_DIR / "original"
DEFAULT_CONFIG_FILE = BASE_DIR / "config.json"

class Config:
    raw_persona_path = "data/original/mobile_network_personas_500.json"
    output_dir = "data/generated"
    batch_size = 5
    default_start_idx = 0
    default_count = 20
    model = "deepseek-flash"
    base_url = "https://api.deepseek.com"
    enable_thinking = False

    @classmethod
    def load_all(cls, config_file: str = None):
        cfg_path = Path(config_file) if config_file else DEFAULT_CONFIG_FILE
        if cfg_path.exists():
            with open(cfg_path, "r", encoding="utf-8-sig") as f:
                user_cfg = json.load(f)
                cls.raw_persona_path = user_cfg.get("raw_persona_path", cls.raw_persona_path)
                cls.output_dir = user_cfg.get("output_dir", cls.output_dir)
                cls.batch_size = user_cfg.get("batch_size", cls.batch_size)
                cls.default_start_idx = user_cfg.get("default_start_idx", cls.default_start_idx)
                cls.default_count = user_cfg.get("default_count", cls.default_count)
                cls.model = user_cfg.get("model", cls.model)
                cls.base_url = user_cfg.get("base_url", cls.base_url)
                cls.enable_thinking = user_cfg.get("enable_thinking", cls.enable_thinking)

        if (WHITELIST_DIR / "app_config.json").exists():
            with open(WHITELIST_DIR / "app_config.json", "r", encoding="utf-8") as f:
                cls.app_config = json.load(f)
        if (WHITELIST_DIR / "app_map.json").exists():
            with open(WHITELIST_DIR / "app_map.json", "r", encoding="utf-8") as f:
                cls.app_map = json.load(f)
        if (WHITELIST_DIR / "support_matrix.json").exists():
            with open(WHITELIST_DIR / "support_matrix.json", "r", encoding="utf-8") as f:
                cls.support_matrix = json.load(f)
        if (WHITELIST_DIR / "expression_vault.json").exists():
            with open(WHITELIST_DIR / "expression_vault.json", "r", encoding="utf-8") as f:
                cls.expression_vault = json.load(f)
        return cls

Config.load_all()
