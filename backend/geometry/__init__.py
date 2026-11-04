"""Standalone STEP geometry engine. Pure: no web or database imports."""

from geometry.analyzer import analyze_file
from geometry.errors import GeometryError, GeometryErrorCode
from geometry.measures import DEFAULT_STOCK_ALLOWANCE_MM
from geometry.models import BoundingBox, Features, GeometryResult

__all__ = [
    "DEFAULT_STOCK_ALLOWANCE_MM",
    "BoundingBox",
    "Features",
    "GeometryError",
    "GeometryErrorCode",
    "GeometryResult",
    "analyze_file",
]
