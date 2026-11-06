"""Result types (the FR-G5 output). Lengths in mm, volumes in cm³, areas in cm²."""

from pydantic import BaseModel, ConfigDict, Field


class _Frozen(BaseModel):
    # Frozen: a result cannot be changed after it is built.
    model_config = ConfigDict(frozen=True)


class BoundingBox(_Frozen):
    """Axis-aligned box, sorted so length >= width >= height."""

    length: float = Field(gt=0)
    width: float = Field(gt=0)
    height: float = Field(gt=0)


class Features(_Frozen):
    face_count: int = Field(ge=0)
    edge_count: int = Field(ge=0)
    cylindrical_faces: int = Field(ge=0)
    holes_detected: int = Field(ge=0)
    # Estimated clamping count on a 3-axis machine (see geometry/setups.py).
    setups: int = Field(ge=1)
    # Walls thinner than 3 mm (see geometry/walls.py).
    thin_wall_count: int = Field(ge=0)
    sa_to_volume_ratio: float = Field(ge=0)
    material_removal_ratio: float = Field(ge=0, le=1)
    # Not computed yet: to be added once CNC machining costs are known.
    complexity_score: float | None = Field(default=None, ge=1.0, le=3.0)


class GeometryResult(_Frozen):
    file: str
    units: str = "mm"
    # Unit the file was authored in. Label only: numbers are already converted.
    source_units: str | None = None
    # Name of the material used for the masses below (see geometry/materials.py).
    material: str
    bounding_box_mm: BoundingBox
    stock_volume_cm3: float = Field(gt=0)
    volume_cm3: float = Field(gt=0)
    # Volume x the material's density.
    stock_mass_kg: float = Field(gt=0)
    part_mass_kg: float = Field(gt=0)
    surface_area_cm2: float = Field(gt=0)
    features: Features
    # More than 1 means results are merged and `warnings` says so.
    solids: int = Field(default=1, ge=1)
    warnings: list[str] = Field(default_factory=list)
