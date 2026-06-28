"""
Analytics module for processing and visualizing job market data.

This module provides data cleaning, statistical analysis, and visualization
of scraped job vacancy data.

Usage:
    python -m analytics
    # OR
    from analytics import run_full_analysis
    run_full_analysis()
"""

__all__ = ["run_full_analysis"]


def __getattr__(name):
    """Lazy import to avoid RuntimeWarning when using python -m analytics."""
    if name == "run_full_analysis":
        from .__main__ import run_full_analysis

        return run_full_analysis
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
