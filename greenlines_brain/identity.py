# greenlines_brain/identity.py
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum

class EntityScope(Enum):
    EGYPT = "egypt"
    NORWAY = "norway"
    GULF = "gulf"
    GLOBAL = "global"

@dataclass
class Identity:
    """هوية الكيان الذي يعمل باسمه العقل."""
    scope: EntityScope
    legal_name: str
    country: str
    currency: str
    regulations: List[str] = field(default_factory=list)
    local_context: Dict = field(default_factory=dict)
    
    def __post_init__(self):
        # التحقق من أن السياق يحتوي على الحقول المطلوبة
        if "allowed_exports" not in self.local_context:
            self.local_context["allowed_exports"] = []
        if "local_suppliers" not in self.local_context:
            self.local_context["local_suppliers"] = []
        if "local_products" not in self.local_context:
            self.local_context["local_products"] = []
    
    def get_allowed_exports(self) -> List[str]:
        """يسترجع قائمة الوجهات المسموح بها لهذا الكيان."""
        return self.local_context.get("allowed_exports", [])
    
    def add_allowed_export(self, destination: str):
        """يضيف وجهة جديدة إلى قائمة التصدير المسموح بها."""
        if destination not in self.local_context["allowed_exports"]:
            self.local_context["allowed_exports"].append(destination)