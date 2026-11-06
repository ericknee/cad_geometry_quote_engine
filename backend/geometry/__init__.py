"""Standalone STEP geometry engine. Pure: no web or database imports."""

from geometry.analyzer import analyze_file
from geometry.errors import GeometryError, GeometryErrorCode
from geometry.materials import ALUMINUM_6061, DEFAULT_MATERIAL, MATERIALS, Material, get_material
from geometry.measures import DEFAULT_STOCK_ALLOWANCE_MM
from geometry.models import BoundingBox, Features, GeometryResult

__all__ = [
    "ALUMINUM_6061",
    "DEFAULT_MATERIAL",
    "DEFAULT_STOCK_ALLOWANCE_MM",
    "MATERIALS",
    "BoundingBox",
    "Features",
    "GeometryError",
    "GeometryErrorCode",
    "GeometryResult",
    "Material",
    "analyze_file",
    "get_material",
]
