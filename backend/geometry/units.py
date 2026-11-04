"""Detect the unit a STEP file was authored in (FR-G7).

Label only: OpenCascade already converts everything to mm when reading, so a wrong or
missing result here never changes a measurement.
"""

import re
from pathlib import Path

# The file's geometry context lists its units, e.g. GLOBAL_UNIT_ASSIGNED_CONTEXT((#12, #13, #14)).
_UNIT_CONTEXT = re.compile(r"GLOBAL_UNIT_ASSIGNED_CONTEXT\s*\(\s*\(([^)]*)\)", re.IGNORECASE)
_CONVERSION_NAME = re.compile(r"CONVERSION_BASED_UNIT\s*\(\s*'([^']*)'", re.IGNORECASE)
_SI_METRE = re.compile(r"SI_UNIT\s*\(\s*(\.\w+\.|\$|\*)\s*,\s*\.METRE\.", re.IGNORECASE)

# `$` or `*` means no prefix, i.e. plain metres.
_SI_PREFIXES = {
    ".MILLI.": "mm",
    ".CENTI.": "cm",
    ".MICRO.": "um",
    ".KILO.": "km",
    "$": "m",
    "*": "m",
}


def detect_source_units(path: Path) -> str | None:
    """Return "mm", "inch", "m", etc., or None if it cannot be determined."""
    try:
        text = path.read_text(encoding="latin-1")
    except OSError:
        return None

    context = _UNIT_CONTEXT.search(text)
    if context is None:
        return None

    # Follow the context's own references. Other length-unit entities can exist in the file
    # (the inch is defined from a metre entity), so taking the first match would be wrong.
    for ref in re.findall(r"#(\d+)", context.group(1)):
        entity = re.search(rf"(?m)^\s*#{ref}\s*=\s*(.*?);", text, re.DOTALL)
        if entity is None or "LENGTH_UNIT" not in entity.group(1).upper():
            continue
        return _describe_length_unit(entity.group(1))
    return None


def _describe_length_unit(body: str) -> str | None:
    conversion = _CONVERSION_NAME.search(body)
    if conversion:
        return conversion.group(1).strip().lower() or None
    metre = _SI_METRE.search(body)
    if metre:
        return _SI_PREFIXES.get(metre.group(1).upper())
    return None
