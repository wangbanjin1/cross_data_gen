"""
兼容层：统一重定向至 src.core.memory_tracker
"""
from src.core.memory_tracker import MemoryTracker

__all__ = ["MemoryTracker"]
