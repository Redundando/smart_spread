"""Backwards compatibility shim for smart_spread imports."""
import warnings
from smartspread import SmartSpread, SmartTab

warnings.warn(
    "Importing from 'smart_spread' is deprecated. Use 'from smartspread import ...' instead.",
    DeprecationWarning,
    stacklevel=2
)

__all__ = ['SmartSpread', 'SmartTab']
