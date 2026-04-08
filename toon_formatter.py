"""Formatter that converts parsed GEDCOM records into TOON text format.

TOON (Tree Of Objects Notation) is a plain-text, human- and LLM-readable
representation of genealogical data extracted from a GEDCOM file.
"""

from typing import Optional
from gedcom_parser import GedcomRecord


def _clean_name(name: str) -> str:
    """Remove GEDCOM surname slash notation, e.g. 'John /Smith/' -> 'John Smith'."""
    return name.replace("/", "").strip()


def _format_event(record: GedcomRecord, label: str) -> Optional[str]:
    """Format a GEDCOM event record (BIRT, DEAT, BURI, MARR, etc.) as a string."""
    date = record.get_child_value("DATE")
    place = record.get_child_value("PLAC")

    parts = []
    if date:
        parts.append(date)
    if place:
        parts.append(place)

    if parts:
        return f"{label}: {', '.join(parts)}"
    return label


def _individual_to_toon(record: GedcomRecord, families: dict[str, GedcomRecord]) -> str:
    """Convert a single INDI record to TOON text."""
    lines: list[str] = []

    xref = record.xref_id or "?"
    short_id = xref.strip("@")

    # Name
    name_record = record.get_child_value("NAME")
    display_name = _clean_name(name_record) if name_record else "Unknown"
    lines.append(f"[{short_id}] {display_name}")

    # Sex
    sex = record.get_child_value("SEX")
    if sex:
        sex_label = {"M": "Male", "F": "Female"}.get(sex.upper(), sex)
        lines.append(f"  Sex: {sex_label}")

    # Birth
    for birt in record.get_children_by_tag("BIRT"):
        event_str = _format_event(birt, "Birth")
        if event_str:
            lines.append(f"  {event_str}")

    # Christening
    for chr_rec in record.get_children_by_tag("CHR"):
        event_str = _format_event(chr_rec, "Christening")
        if event_str:
            lines.append(f"  {event_str}")

    # Death
    for deat in record.get_children_by_tag("DEAT"):
        event_str = _format_event(deat, "Death")
        if event_str:
            lines.append(f"  {event_str}")

    # Burial
    for buri in record.get_children_by_tag("BURI"):
        event_str = _format_event(buri, "Burial")
        if event_str:
            lines.append(f"  {event_str}")

    # Occupation
    for occu in record.get_children_by_tag("OCCU"):
        if occu.value:
            lines.append(f"  Occupation: {occu.value}")

    # Residence
    for resi in record.get_children_by_tag("RESI"):
        event_str = _format_event(resi, "Residence")
        if event_str:
            lines.append(f"  {event_str}")

    # Family links
    for fams in record.get_children_by_tag("FAMS"):
        fam_ref = fams.value.strip()
        fam = families.get(fam_ref)
        if fam:
            husb = fam.get_child_value("HUSB")
            wife = fam.get_child_value("WIFE")
            if husb == xref:
                role = "Husband"
            elif wife == xref:
                role = "Wife"
            else:
                role = "Spouse"
            fam_id = fam_ref.strip("@")
            lines.append(f"  {role} in Family [{fam_id}]")
        else:
            fam_id = fam_ref.strip("@")
            lines.append(f"  Spouse in Family [{fam_id}]")

    for famc in record.get_children_by_tag("FAMC"):
        fam_ref = famc.value.strip()
        fam_id = fam_ref.strip("@")
        lines.append(f"  Child in Family [{fam_id}]")

    # Notes
    for note in record.get_children_by_tag("NOTE"):
        if note.value:
            lines.append(f"  Note: {note.value}")

    return "\n".join(lines)


def _family_to_toon(
    record: GedcomRecord, individuals: dict[str, GedcomRecord]
) -> str:
    """Convert a single FAM record to TOON text."""
    lines: list[str] = []

    xref = record.xref_id or "?"
    short_id = xref.strip("@")
    lines.append(f"[{short_id}] Family")

    def _name_of(ref: str) -> str:
        ind = individuals.get(ref)
        if ind:
            raw = ind.get_child_value("NAME") or "Unknown"
            return f"{_clean_name(raw)} [{ref.strip('@')}]"
        return ref.strip("@")

    husb_ref = record.get_child_value("HUSB")
    if husb_ref:
        lines.append(f"  Husband: {_name_of(husb_ref)}")

    wife_ref = record.get_child_value("WIFE")
    if wife_ref:
        lines.append(f"  Wife: {_name_of(wife_ref)}")

    # Marriage event
    for marr in record.get_children_by_tag("MARR"):
        event_str = _format_event(marr, "Marriage")
        if event_str:
            lines.append(f"  {event_str}")

    # Divorce event
    for div_rec in record.get_children_by_tag("DIV"):
        event_str = _format_event(div_rec, "Divorce")
        if event_str:
            lines.append(f"  {event_str}")

    children = record.get_children_by_tag("CHIL")
    if children:
        lines.append("  Children:")
        for chil in children:
            chil_ref = chil.value.strip()
            lines.append(f"    - {_name_of(chil_ref)}")

    # Notes
    for note in record.get_children_by_tag("NOTE"):
        if note.value:
            lines.append(f"  Note: {note.value}")

    return "\n".join(lines)


def gedcom_records_to_toon(records: list[GedcomRecord]) -> str:
    """Convert a list of parsed GEDCOM top-level records to TOON text format."""
    individuals: dict[str, GedcomRecord] = {}
    families: dict[str, GedcomRecord] = {}

    for record in records:
        if record.tag == "INDI" and record.xref_id:
            individuals[record.xref_id] = record
        elif record.tag == "FAM" and record.xref_id:
            families[record.xref_id] = record

    sections: list[str] = []

    # Individuals section
    if individuals:
        ind_blocks = [
            _individual_to_toon(ind, families) for ind in individuals.values()
        ]
        sections.append("=== INDIVIDUALS ===\n\n" + "\n\n".join(ind_blocks))

    # Families section
    if families:
        fam_blocks = [
            _family_to_toon(fam, individuals) for fam in families.values()
        ]
        sections.append("=== FAMILIES ===\n\n" + "\n\n".join(fam_blocks))

    return "\n\n".join(sections) + "\n" if sections else ""
