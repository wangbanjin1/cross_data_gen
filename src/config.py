"""
兼容层：统一重定向至 src.config.settings
"""
from src.config.settings import (
    Config,
    BASE_DIR,
    DATA_DIR,
    WHITELIST_DIR,
    ORIGINAL_DIR,
    DEFAULT_CONFIG_FILE,
)

__all__ = [
    "Config",
    "BASE_DIR",
    "DATA_DIR",
    "WHITELIST_DIR",
    "ORIGINAL_DIR",
    "DEFAULT_CONFIG_FILE",
]
