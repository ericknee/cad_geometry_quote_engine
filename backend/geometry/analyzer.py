"""Public entry point: STEP file in, GeometryResult out."""

from dataclasses import dataclass
from pathlib import Path

from OCP.TopoDS import TopoDS_Shape

from geometry.features import (
    SolidFeatures,
    extract_features,
    material_removal_ratio,
    merge_features,
    sa_to_volume_ratio,
)
from geometry.loader import LoadedStep, load_step
from geometry.measures import (
    DEFAULT_STOCK_ALLOWANCE_MM,
    SolidMeasures,
    box_dimensions,
    measure_solid,
    merge_measures,
    stock_volume_cm3,
)
from geometry.models import BoundingBox, Features, GeometryResult

# Sizes outside this range usually mean the file's unit is wrong, so we warn.
_MIN_PLAUSIBLE_MM = 0.5
_MAX_PLAUSIBLE_MM = 2000.0


@dataclass(frozen=True)
class SolidAnalysis:
    measures: SolidMeasures
    features: SolidFeatures


def analyze_solid(solid: TopoDS_Shape) -> SolidAnalysis:
    """Analyze one solid on its own. Kept separate so solids can later be quoted individually."""
    return SolidAnalysis(measures=measure_solid(solid), features=extract_features(solid))


def analyze_file(
    path: str | Path, stock_allowance_mm: float = DEFAULT_STOCK_ALLOWANCE_MM
) -> GeometryResult:
    return analyze_loaded(load_step(path), stock_allowance_mm)


def analyze_loaded(
    loaded: LoadedStep, stock_allowance_mm: float = DEFAULT_STOCK_ALLOWANCE_MM
) -> GeometryResult:
    """Analyze every solid, then merge into one result (sums, one box around all solids)."""
    if stock_allowance_mm < 0:
        raise ValueError("stock_allowance_mm must be >= 0")

    parts = [analyze_solid(solid) for solid in loaded.solids]
    measures = merge_measures([p.measures for p in parts])
    features = merge_features([p.features for p in parts])

    dimensions = box_dimensions(measures)
    stock = stock_volume_cm3(dimensions, stock_allowance_mm)

    warnings: list[str] = []
    if len(parts) > 1:
        warnings.append(
            f"File contains {len(parts)} solids; results are merged into one part "
            "(one bounding box, volumes and areas added)."
        )
    if dimensions[2] < _MIN_PLAUSIBLE_MM or dimensions[0] > _MAX_PLAUSIBLE_MM:
        warnings.append(
            f"Part size {dimensions[0]:.2f} x {dimensions[1]:.2f} x {dimensions[2]:.2f} mm "
            "looks unusual. Check that the file's units are correct."
        )

    # Rounded only here, at output. Ratios use the unrounded values.
    return GeometryResult(
        file=loaded.file_name,
        source_units=loaded.source_units,
        bounding_box_mm=BoundingBox(
            length=round(dimensions[0], 3),
            width=round(dimensions[1], 3),
            height=round(dimensions[2], 3),
        ),
        stock_volume_cm3=round(stock, 3),
        volume_cm3=round(measures.volume_cm3, 4),
        surface_area_cm2=round(measures.surface_area_cm2, 3),
        features=Features(
            face_count=features.face_count,
            edge_count=features.edge_count,
            cylindrical_faces=features.cylindrical_faces,
            holes_detected=features.holes_detected,
            sa_to_volume_ratio=round(
                sa_to_volume_ratio(measures.surface_area_cm2, measures.volume_cm3), 3
            ),
            material_removal_ratio=round(material_removal_ratio(measures.volume_cm3, stock), 3),
        ),
        solids=len(parts),
        warnings=warnings,
    )
