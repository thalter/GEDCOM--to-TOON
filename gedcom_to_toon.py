#!/usr/bin/env python3
"""Convert a GEDCOM-formatted genealogy file to TOON text format.

Usage:
    python gedcom_to_toon.py <input.ged> [output.toon]

If no output file is specified, the result is written to stdout.
"""

import argparse
import sys

from gedcom_parser import load_gedcom_file, parse_gedcom
from toon_formatter import gedcom_records_to_toon


def convert_file(input_path: str, output_path: str | None = None) -> None:
    """Read a GEDCOM file and write the TOON output.

    Args:
        input_path: Path to the input GEDCOM file.
        output_path: Path to the output TOON file, or None to write to stdout.
    """
    records = load_gedcom_file(input_path)
    toon_text = gedcom_records_to_toon(records)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as fh:
            fh.write(toon_text)
        print(f"Conversion complete: {output_path}", file=sys.stderr)
    else:
        sys.stdout.write(toon_text)


def convert_string(gedcom_text: str) -> str:
    """Convert a GEDCOM string to TOON format and return the result.

    Args:
        gedcom_text: The GEDCOM content as a string.

    Returns:
        The TOON-formatted string.
    """
    records = parse_gedcom(gedcom_text)
    return gedcom_records_to_toon(records)


def main() -> None:
    """Entry point for the command-line interface."""
    parser = argparse.ArgumentParser(
        description="Convert a GEDCOM genealogy file to TOON text format."
    )
    parser.add_argument("input", help="Path to the input GEDCOM file (.ged)")
    parser.add_argument(
        "output",
        nargs="?",
        default=None,
        help="Path to the output TOON file (default: stdout)",
    )
    args = parser.parse_args()

    try:
        convert_file(args.input, args.output)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
