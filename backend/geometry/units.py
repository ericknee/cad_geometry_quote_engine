"""Name the unit a STEP file was authored in (FR-G7).

Label only: OpenCascade already converts everything to mm when reading, so a wrong or
missing result here never changes a measurement. We reuse what the kernel parsed instead of
re-reading the file.
"""

from OCP.collections import Sequence_TCollection_AsciiString
from OCP.STEPControl import STEPControl_Reader

# The kernel's names for common units -> short labels. Anything else falls back to its own name.
_LABELS = {
    "millimetre": "mm",
    "centimetre": "cm",
    "micrometre": "um",
    "metre": "m",
    "kilometre": "km",
    "inch": "inch",
    "foot": "foot",
}


def detect_source_units(reader: STEPControl_Reader) -> str | None:
    """Return "mm", "inch", "m", etc., or None if it cannot be determined.

    Call after ReadFile.
    """
    try:
        lengths = Sequence_TCollection_AsciiString()
        reader.FileUnits(
            lengths, Sequence_TCollection_AsciiString(), Sequence_TCollection_AsciiString()
        )
        if lengths.Length() == 0:
            return None
        name = lengths.First().ToCString().strip().lower()
    except Exception:  # Label only, so any kernel hiccup just means "unknown".
        return None
    return _LABELS.get(name, name or None)
