"""Command line: analyze a STEP file and print the result as JSON (FR-G1, FR-G5, FR-G6).

Exit code 0 on success, 1 on any failure (error JSON on stdout), 2 on bad arguments.
"""

import argparse
import json
import math
import sys
from pathlib import Path

from geometry.analyzer import analyze_file
from geometry.errors import GeometryError
from geometry.materials import DEFAULT_MATERIAL, MATERIALS, get_material
from geometry.measures import DEFAULT_STOCK_ALLOWANCE_MM


def _non_negative(text: str) -> float:
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{text}' is not a number") from None
    if not math.isfinite(value) or value < 0:
        raise argparse.ArgumentTypeError("must be a finite number, 0 or greater")
    return value


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="analyze_geometry",
        description="Measure a STEP file; print box, volume, area and features as JSON.",
    )
    parser.add_argument("file", type=Path, help="path to a .step or .stp file")
    parser.add_argument("--pretty", action="store_true", help="indent the JSON")
    parser.add_argument("--out", type=Path, help="also write the JSON to this file")
    parser.add_argument(
        "--stock-allowance",
        type=_non_negative,
        default=DEFAULT_STOCK_ALLOWANCE_MM,
        metavar="MM",
        help=f"extra stock per side in mm (default {DEFAULT_STOCK_ALLOWANCE_MM})",
    )
    parser.add_argument(
        "--material",
        choices=sorted(MATERIALS),
        default=DEFAULT_MATERIAL.name,
        help=f"material for the mass figures (default {DEFAULT_MATERIAL.name})",
    )
    return parser


def _error_json(code: str, message: str, pretty: bool) -> str:
    return json.dumps({"error": {"code": code, "message": message}}, indent=2 if pretty else None)


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        result = analyze_file(args.file, args.stock_allowance, get_material(args.material))
        # ensure_ascii keeps output safe on consoles that cannot print non-ASCII (Windows).
        text = json.dumps(result.model_dump(), indent=2 if args.pretty else None)
    except GeometryError as error:
        print(_error_json(error.code.value, error.message, args.pretty))
        return 1
    except Exception as error:  # Anything unexpected still gets a JSON error, not a traceback.
        print(_error_json("INTERNAL_ERROR", f"{type(error).__name__}: {error}", args.pretty))
        return 1
    if args.out:
        try:
            args.out.write_text(text + "\n", encoding="utf-8")
        except OSError as error:
            print(_error_json("OUTPUT_ERROR", f"Could not write output: {error}", args.pretty))
            return 1
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
