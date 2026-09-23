"""
兼容层：统一重定向至 src.generation.llm_client
"""
from src.generation.llm_client import LLMClient

__all__ = ["LLMClient"]
