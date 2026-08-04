"""Tax computation engines.

Each module here produces a :class:`Computation` -- a result object that
carries not just a number but the workings that produced it, and the config
parameters those workings relied on. A tax figure without visible workings is
not reviewable, and anything not reviewable should not be filed.
"""

from .base import Computation, Step

__all__ = ["Computation", "Step"]
