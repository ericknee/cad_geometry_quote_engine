"""Load a STEP file into solids and validate it (FR-G6, FR-G7)."""

from dataclasses import dataclass
from pathlib import Path

from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.IFSelect import IFSelect_ReturnStatus
from OCP.Message import Message, Message_PrinterOStream
from OCP.STEPControl import STEPControl_Reader
from OCP.TopAbs import TopAbs_SOLID
from OCP.TopoDS import TopoDS_Shape

from geometry.errors import GeometryError, GeometryErrorCode
from geometry.topology import unique_subshapes
from geometry.units import detect_source_units

SUPPORTED_EXTENSIONS = (".step", ".stp")

# Silence the kernel's message printer. It writes parse errors to stdout (not stderr), which
# would put a stray line before the CLI's JSON. Tradeoff: we lose the kernel's line-level
# detail; GeometryError still reports the failure.
Message.DefaultMessenger_s().RemovePrinters(Message_PrinterOStream.get_type_descriptor_s())


@dataclass(frozen=True)
class LoadedStep:
    file_name: str
    solids: list[TopoDS_Shape]
    source_units: str | None


def load_step(path: str | Path) -> LoadedStep:
    """Read a STEP file and return its solids, already converted to mm by the kernel."""
    path = Path(path)
    if not path.is_file():
        raise GeometryError(GeometryErrorCode.FILE_NOT_FOUND, f"File not found: {path}")
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise GeometryError(
            GeometryErrorCode.UNSUPPORTED_EXTENSION,
            f"Unsupported file type '{path.suffix}'. Expected one of: "
            f"{', '.join(SUPPORTED_EXTENSIONS)}.",
        )

    shape = _read_shape(path)
    solids = unique_subshapes(shape, TopAbs_SOLID)
    if not solids:
        raise GeometryError(
            GeometryErrorCode.NO_SOLIDS,
            "The file contains no solid bodies (it may hold only surfaces or wires).",
        )
    # OpenCascade's own validity check catches open shells and self-intersections.
    for index, solid in enumerate(solids, start=1):
        if not BRepCheck_Analyzer(solid).IsValid():
            raise GeometryError(
                GeometryErrorCode.INVALID_SOLID,
                f"Solid {index} of {len(solids)} is invalid (open, self-intersecting or "
                "otherwise malformed geometry).",
            )

    return LoadedStep(
        file_name=path.name,
        solids=solids,
        source_units=detect_source_units(path),
    )


def _read_shape(path: Path) -> TopoDS_Shape:
    unreadable = GeometryError(
        GeometryErrorCode.UNREADABLE_STEP, f"Could not read '{path.name}' as a STEP file."
    )
    try:
        reader = STEPControl_Reader()
        if reader.ReadFile(str(path)) != IFSelect_ReturnStatus.IFSelect_RetDone:
            raise unreadable
        if reader.TransferRoots() == 0:
            raise unreadable
        shape = reader.OneShape()
    except GeometryError:
        raise
    except Exception as exc:  # The kernel raises generic errors; callers only see GeometryError.
        raise unreadable from exc
    if shape.IsNull():
        raise unreadable
    return shape
