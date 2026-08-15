# greenlines_brain/ontology.py
from dataclasses import dataclass, field
from typing import List, Optional, Dict

@dataclass
class Product:
    id: str
    name: str
    category: str
    description: str
    hs_code: str
    ean: str
    country_of_origin: str
    certifications: List[str] = field(default_factory=list)
    markets: Dict[str, bool] = field(default_factory=dict)  # {"gcc": True, "eu": False}

@dataclass
class Supplier:
    id: str
    name: str
    categories: List[str]
    country: str
    city: str
    certifications: List[str]
    status: str  # active, candidate, inactive

@dataclass
class Certificate:
    id: str
    name: str
    category: str
    description: str
    applicable_to: List[str]

@dataclass
class EntityContext:
    """
    يمثل سياق كيان محلي (مصر، النرويج، الخليج).
    كل كيان له قوانينه ومورديه وعملائه الخاصة.
    """
    name: str  # "egypt", "norway", "gulf"
    country: str
    currency: str
    legal_entity: str
    local_products: List[Product] = field(default_factory=list)
    local_suppliers: List[Supplier] = field(default_factory=list)
    local_regulations: List[str] = field(default_factory=list)