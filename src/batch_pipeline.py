"""
兼容层：统一重定向至 src.pipeline.batch_pipeline
"""
from src.pipeline.batch_pipeline import BatchPipeline

__all__ = ["BatchPipeline"]
