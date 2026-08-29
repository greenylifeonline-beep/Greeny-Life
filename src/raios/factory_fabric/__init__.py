"""RAIOS Factory Fabric.

Canonical orchestration layer over existing Resource Factory, Training Factory,
Assimilation Factory, and Expert Foundry capabilities. Runtime state is externalized
under ~/.raios/runtime/factory-fabric; it does not create a second scheduler,
resource authority, or canonical promotion path.
"""

from .orchestrator import run_all
from .state_import import import_factory_estate

__all__ = ["run_all", "import_factory_estate"]
