"""
DEPRECATED: This file is kept for backwards compatibility.
Use the modular version in the analytics/ directory instead.

To run analytics, use:
    python -m analytics.main
or:
    from analytics import run_full_analysis
    run_full_analysis()
"""

from analytics import run_full_analysis

if __name__ == "__main__":
    run_full_analysis()
