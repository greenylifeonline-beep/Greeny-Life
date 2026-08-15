# greenlines_brain/repository/interface.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class KnowledgeRepository(ABC):
    @abstractmethod
    def get_entity(self, entity_type: str, entity_id: str) -> Optional[Dict]:
        """يسترجع كياناً معيناً من نوع محدد."""
        pass
    
    @abstractmethod
    def find_entities(self, entity_type: str, filters: Dict = None) -> List[Dict]:
        """يبحث عن كيانات من نوع محدد بشروط اختيارية."""
        pass
    
    @abstractmethod
    def get_relationships(self, source_type: str, source_id: str) -> List[Dict]:
        """يسترجع العلاقات المرتبطة بكيان معين."""
        pass
    
    @abstractmethod
    def get_rules(self, domain: Optional[str] = None) -> List[Dict]:
        """يسترجع القواعد التجارية، ويمكن تصفيتها حسب المجال."""
        pass
    
    @abstractmethod
    def get_evidence(self, entity_id: str) -> List[Dict]:
        """يسترجع الأدلة المرتبطة بكيان أو قاعدة معينة."""
        pass
    
    @abstractmethod
    def search(self, query: str) -> List[Dict]:
        """يبحث في المعرفة باستخدام استعلام نصي."""
        pass