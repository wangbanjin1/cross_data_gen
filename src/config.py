import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
WHITELIST_DIR = DATA_DIR / "whitelist"
ORIGINAL_DIR = DATA_DIR / "original"

class Config:
    @classmethod
    def load_all(cls):
        with open(WHITELIST_DIR / "app_config.json", "r", encoding="utf-8") as f:
            cls.app_config = json.load(f)
        with open(WHITELIST_DIR / "app_map.json", "r", encoding="utf-8") as f:
            cls.app_map = json.load(f)
        with open(WHITELIST_DIR / "support_matrix.json", "r", encoding="utf-8") as f:
            cls.support_matrix = json.load(f)
        with open(WHITELIST_DIR / "expression_vault.json", "r", encoding="utf-8") as f:
            cls.expression_vault = json.load(f)
        return cls

Config.load_all()
