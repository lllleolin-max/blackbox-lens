"""Black-box behavioral experiments; no access to hidden model reasoning."""

__version__ = "0.2.0"

from .suite import Suite, SuiteError, load_suite
from .engine import analyze_run, create_plan, run_suite
from .adapters import OpenAICompatible, Reply, SyntheticAdapter

__all__ = ["Suite", "SuiteError", "load_suite", "create_plan", "run_suite",
           "analyze_run", "OpenAICompatible", "Reply", "SyntheticAdapter"]
