"""Parser for GEDCOM-formatted genealogy files."""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GedcomLine:
    """Represents a single parsed line from a GEDCOM file."""

    level: int
    xref_id: Optional[str]
    tag: str
    value: str


@dataclass
class GedcomRecord:
    """Represents a GEDCOM record (a top-level entry and its sub-records)."""

    level: int
    xref_id: Optional[str]
    tag: str
    value: str
    children: list["GedcomRecord"] = field(default_factory=list)

    def get_child_value(self, tag: str) -> Optional[str]:
        """Return the value of the first child record with the given tag."""
        for child in self.children:
            if child.tag == tag:
                return child.value
        return None

    def get_children_by_tag(self, tag: str) -> list["GedcomRecord"]:
        """Return all child records with the given tag."""
        return [child for child in self.children if child.tag == tag]


_LINE_PATTERN = re.compile(r"^(\d+)\s+(@[^@]+@|\S+)\s*(@[^@]+@|\S+)?\s*(.*)$")


def parse_line(raw: str) -> Optional[GedcomLine]:
    """Parse a single GEDCOM line into a GedcomLine object.

    GEDCOM line format: LEVEL [XREF_ID] TAG [VALUE]
    """
    raw = raw.strip()
    if not raw:
        return None

    parts = raw.split(None, 3)
    if len(parts) < 2:
        return None

    try:
        level = int(parts[0])
    except ValueError:
        return None

    if len(parts) == 2:
        tag = parts[1]
        xref_id = None
        value = ""
    elif parts[1].startswith("@") and parts[1].endswith("@"):
        xref_id = parts[1]
        tag = parts[2] if len(parts) > 2 else ""
        value = parts[3] if len(parts) > 3 else ""
    else:
        xref_id = None
        tag = parts[1]
        value = " ".join(parts[2:]) if len(parts) > 2 else ""

    return GedcomLine(level=level, xref_id=xref_id, tag=tag, value=value)


def parse_gedcom(text: str) -> list[GedcomRecord]:
    """Parse a GEDCOM text into a list of top-level GedcomRecord objects.

    Builds a tree of records where sub-records (level > 0) are children of
    the nearest preceding record at level - 1.

    ``CONT`` and ``CONC`` continuation lines are merged into the value of
    their parent record rather than stored as child records.  ``CONT`` adds
    a newline before the continued text; ``CONC`` appends without a newline.
    """
    lines = [parse_line(line) for line in text.splitlines()]
    lines = [line for line in lines if line is not None]

    if not lines:
        return []

    records: list[GedcomRecord] = []
    stack: list[GedcomRecord] = []

    for line in lines:
        # CONT/CONC are continuations of the nearest parent's value.
        if line.tag in ("CONT", "CONC") and stack:
            parent = None
            for candidate in reversed(stack):
                if candidate.level == line.level - 1:
                    parent = candidate
                    break
            if parent is not None:
                if line.tag == "CONT":
                    parent.value = parent.value + "\n" + line.value
                else:  # CONC
                    parent.value = parent.value + line.value
                continue  # Do not add CONT/CONC as child records.

        record = GedcomRecord(
            level=line.level,
            xref_id=line.xref_id,
            tag=line.tag,
            value=line.value,
        )

        if line.level == 0:
            records.append(record)
            stack = [record]
        else:
            # Pop stack until the parent level is found
            while len(stack) > 1 and stack[-1].level >= line.level:
                stack.pop()
            if stack:
                stack[-1].children.append(record)
            stack.append(record)

    return records


def load_gedcom_file(path: str) -> list[GedcomRecord]:
    """Read and parse a GEDCOM file from disk.

    Tries UTF-8 (with optional BOM) first, then falls back to Latin-1 so
    that older GEDCOM files using ANSEL or Windows-1252 encodings can still
    be read without crashing.
    """
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            with open(path, encoding=encoding) as fh:
                return parse_gedcom(fh.read())
        except UnicodeDecodeError:
            continue
    # Last-resort: read with replacement for any remaining undecodable bytes.
    with open(path, encoding="utf-8", errors="replace") as fh:
        return parse_gedcom(fh.read())
