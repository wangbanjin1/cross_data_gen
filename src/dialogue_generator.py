"""
兼容层：统一重定向至 src.generation.dialogue_generator
"""
from src.generation.dialogue_generator import DialogueGenerator

__all__ = ["DialogueGenerator"]
