"""
兼容层：统一重定向至 src.core.qc_validator
"""
from src.core.qc_validator import QCValidator

__all__ = ["QCValidator"]
