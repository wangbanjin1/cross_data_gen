"""
兼容层：统一重定向至 src.core.timeline_planner
"""
from src.core.timeline_planner import DynamicTimelinePlanner

__all__ = ["DynamicTimelinePlanner"]
