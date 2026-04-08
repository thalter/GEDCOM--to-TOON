# GEDCOM--to-TOON

Convert GEDCOM formatted files to TOON suitable for loading into LLM

## Overview

This Python application parses a [GEDCOM](https://en.wikipedia.org/wiki/GEDCOM)
genealogy file and converts it to **TOON** (Tree Of Objects Notation), a
plain-text format that is easy for humans and Large Language Models to read.

### TOON format

The output organises individuals and families into clearly labelled sections.
Each individual record includes name, sex, birth/death/burial events, occupation,
residence, and cross-references to spouse and parent families. Each family record
lists the husband, wife, marriage details, and children.

Example output:

```
=== INDIVIDUALS ===

[I1] John Smith
  Sex: Male
  Birth: 15 JAN 1900, New York, NY, USA
  Death: 3 MAR 1975, Los Angeles, CA, USA
  Occupation: Carpenter
  Husband in Family [F1]

[I2] Jane Doe
  Sex: Female
  Birth: 22 APR 1905, Boston, MA, USA
  Wife in Family [F1]

=== FAMILIES ===

[F1] Family
  Husband: John Smith [I1]
  Wife: Jane Doe [I2]
  Marriage: 12 JUN 1927, New York, NY, USA
  Children:
    - Robert Smith [I3]
```

## Requirements

- Python 3.12+
- No external dependencies

## Usage

### Command line

```bash
# Write TOON output to stdout
python gedcom_to_toon.py input.ged

# Write TOON output to a file
python gedcom_to_toon.py input.ged output.toon
```

A sample GEDCOM file (`sample.ged`) is included for testing.

### Python API

```python
from gedcom_to_toon import convert_file, convert_string

# Convert from a file path
convert_file("input.ged", "output.toon")

# Convert from a GEDCOM string
toon_text = convert_string(gedcom_content)
```

## Project structure

| File | Purpose |
|------|---------|
| `gedcom_to_toon.py` | CLI entry point and public API |
| `gedcom_parser.py` | GEDCOM file parser |
| `toon_formatter.py` | TOON output formatter |
| `sample.ged` | Sample GEDCOM file |
| `test_gedcom_to_toon.py` | Unit tests |

## Running the tests

```bash
python -m unittest test_gedcom_to_toon -v
```
