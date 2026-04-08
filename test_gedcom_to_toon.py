"""Unit tests for the GEDCOM-to-TOON conversion pipeline."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from gedcom_parser import GedcomLine, GedcomRecord, parse_gedcom, parse_line
from gedcom_to_toon import convert_file, convert_string
from toon_formatter import gedcom_records_to_toon

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SIMPLE_GEDCOM = """\
0 HEAD
1 GEDC
2 VERS 5.5.1
1 CHAR UTF-8
0 @I1@ INDI
1 NAME John /Smith/
1 SEX M
1 BIRT
2 DATE 15 JAN 1900
2 PLAC New York, NY, USA
1 DEAT
2 DATE 3 MAR 1975
1 OCCU Carpenter
1 FAMS @F1@
0 @I2@ INDI
1 NAME Jane /Doe/
1 SEX F
1 BIRT
2 DATE 22 APR 1905
1 FAMS @F1@
0 @I3@ INDI
1 NAME Robert /Smith/
1 SEX M
1 FAMC @F1@
0 @F1@ FAM
1 HUSB @I1@
1 WIFE @I2@
1 MARR
2 DATE 12 JUN 1927
2 PLAC New York, NY, USA
1 CHIL @I3@
0 TRLR
"""

EMPTY_GEDCOM = "0 HEAD\n0 TRLR\n"


# ---------------------------------------------------------------------------
# parse_line tests
# ---------------------------------------------------------------------------


class TestParseLine(unittest.TestCase):
    def test_basic_tag(self):
        result = parse_line("0 HEAD")
        self.assertIsNotNone(result)
        self.assertEqual(result.level, 0)
        self.assertIsNone(result.xref_id)
        self.assertEqual(result.tag, "HEAD")
        self.assertEqual(result.value, "")

    def test_xref_with_tag(self):
        result = parse_line("0 @I1@ INDI")
        self.assertIsNotNone(result)
        self.assertEqual(result.level, 0)
        self.assertEqual(result.xref_id, "@I1@")
        self.assertEqual(result.tag, "INDI")
        self.assertEqual(result.value, "")

    def test_tag_with_value(self):
        result = parse_line("1 NAME John /Smith/")
        self.assertIsNotNone(result)
        self.assertEqual(result.level, 1)
        self.assertIsNone(result.xref_id)
        self.assertEqual(result.tag, "NAME")
        self.assertEqual(result.value, "John /Smith/")

    def test_level2_with_value(self):
        result = parse_line("2 DATE 15 JAN 1900")
        self.assertIsNotNone(result)
        self.assertEqual(result.level, 2)
        self.assertEqual(result.tag, "DATE")
        self.assertEqual(result.value, "15 JAN 1900")

    def test_empty_line_returns_none(self):
        self.assertIsNone(parse_line(""))
        self.assertIsNone(parse_line("   "))

    def test_xref_value_line(self):
        result = parse_line("1 HUSB @I1@")
        self.assertIsNotNone(result)
        self.assertEqual(result.tag, "HUSB")
        self.assertEqual(result.value, "@I1@")


# ---------------------------------------------------------------------------
# parse_gedcom tests
# ---------------------------------------------------------------------------


class TestParseGedcom(unittest.TestCase):
    def test_parses_top_level_records(self):
        records = parse_gedcom(SIMPLE_GEDCOM)
        tags = [r.tag for r in records]
        self.assertIn("HEAD", tags)
        self.assertIn("INDI", tags)
        self.assertIn("FAM", tags)
        self.assertIn("TRLR", tags)

    def test_individual_has_correct_xref(self):
        records = parse_gedcom(SIMPLE_GEDCOM)
        indis = [r for r in records if r.tag == "INDI"]
        xrefs = {r.xref_id for r in indis}
        self.assertIn("@I1@", xrefs)
        self.assertIn("@I2@", xrefs)

    def test_children_are_nested(self):
        records = parse_gedcom(SIMPLE_GEDCOM)
        i1 = next(r for r in records if r.xref_id == "@I1@")
        name = i1.get_child_value("NAME")
        self.assertEqual(name, "John /Smith/")

    def test_nested_event_children(self):
        records = parse_gedcom(SIMPLE_GEDCOM)
        i1 = next(r for r in records if r.xref_id == "@I1@")
        birt = i1.get_children_by_tag("BIRT")
        self.assertEqual(len(birt), 1)
        self.assertEqual(birt[0].get_child_value("DATE"), "15 JAN 1900")
        self.assertEqual(birt[0].get_child_value("PLAC"), "New York, NY, USA")

    def test_empty_gedcom(self):
        records = parse_gedcom(EMPTY_GEDCOM)
        tags = [r.tag for r in records]
        self.assertIn("HEAD", tags)
        self.assertIn("TRLR", tags)

    def test_no_individuals_in_empty(self):
        records = parse_gedcom(EMPTY_GEDCOM)
        indis = [r for r in records if r.tag == "INDI"]
        self.assertEqual(len(indis), 0)

    def test_cont_merges_with_newline(self):
        gedcom = (
            "0 HEAD\n"
            "0 @I1@ INDI\n"
            "1 NOTE First line\n"
            "2 CONT Second line\n"
            "0 TRLR\n"
        )
        records = parse_gedcom(gedcom)
        i1 = next(r for r in records if r.xref_id == "@I1@")
        note = i1.get_child_value("NOTE")
        self.assertEqual(note, "First line\nSecond line")

    def test_conc_appends_without_newline(self):
        gedcom = (
            "0 HEAD\n"
            "0 @I1@ INDI\n"
            "1 NOTE StartOf\n"
            "2 CONC Value\n"
            "0 TRLR\n"
        )
        records = parse_gedcom(gedcom)
        i1 = next(r for r in records if r.xref_id == "@I1@")
        note = i1.get_child_value("NOTE")
        self.assertEqual(note, "StartOfValue")

    def test_cont_conc_not_stored_as_children(self):
        gedcom = (
            "0 HEAD\n"
            "0 @I1@ INDI\n"
            "1 NOTE Line one\n"
            "2 CONT Line two\n"
            "0 TRLR\n"
        )
        records = parse_gedcom(gedcom)
        i1 = next(r for r in records if r.xref_id == "@I1@")
        note_records = i1.get_children_by_tag("NOTE")
        self.assertEqual(len(note_records), 1)
        cont_records = note_records[0].get_children_by_tag("CONT")
        self.assertEqual(len(cont_records), 0)

    def test_multiple_cont_lines(self):
        gedcom = (
            "0 HEAD\n"
            "0 @I1@ INDI\n"
            "1 NOTE Line A\n"
            "2 CONT Line B\n"
            "2 CONT Line C\n"
            "0 TRLR\n"
        )
        records = parse_gedcom(gedcom)
        i1 = next(r for r in records if r.xref_id == "@I1@")
        note = i1.get_child_value("NOTE")
        self.assertEqual(note, "Line A\nLine B\nLine C")


# ---------------------------------------------------------------------------
# toon_formatter tests
# ---------------------------------------------------------------------------


class TestToonFormatter(unittest.TestCase):
    def setUp(self):
        self.records = parse_gedcom(SIMPLE_GEDCOM)
        self.toon = gedcom_records_to_toon(self.records)

    def test_individuals_section_present(self):
        self.assertIn("=== INDIVIDUALS ===", self.toon)

    def test_families_section_present(self):
        self.assertIn("=== FAMILIES ===", self.toon)

    def test_name_cleaned(self):
        self.assertIn("John Smith", self.toon)
        self.assertNotIn("John /Smith/", self.toon)

    def test_sex_displayed(self):
        self.assertIn("Sex: Male", self.toon)
        self.assertIn("Sex: Female", self.toon)

    def test_birth_event_formatted(self):
        self.assertIn("Birth: 15 JAN 1900, New York, NY, USA", self.toon)

    def test_death_event_formatted(self):
        self.assertIn("Death: 3 MAR 1975", self.toon)

    def test_occupation_formatted(self):
        self.assertIn("Occupation: Carpenter", self.toon)

    def test_marriage_event_formatted(self):
        self.assertIn("Marriage: 12 JUN 1927, New York, NY, USA", self.toon)

    def test_family_husband_wife(self):
        self.assertIn("Husband: John Smith [I1]", self.toon)
        self.assertIn("Wife: Jane Doe [I2]", self.toon)

    def test_family_children(self):
        self.assertIn("Children:", self.toon)
        self.assertIn("Robert Smith [I3]", self.toon)

    def test_family_links_in_individual(self):
        self.assertIn("Husband in Family [F1]", self.toon)
        self.assertIn("Wife in Family [F1]", self.toon)
        self.assertIn("Child in Family [F1]", self.toon)

    def test_empty_gedcom_produces_empty_toon(self):
        records = parse_gedcom(EMPTY_GEDCOM)
        result = gedcom_records_to_toon(records)
        self.assertEqual(result, "")


# ---------------------------------------------------------------------------
# convert_string / convert_file integration tests
# ---------------------------------------------------------------------------


class TestConvertString(unittest.TestCase):
    def test_returns_string(self):
        result = convert_string(SIMPLE_GEDCOM)
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_includes_individual_names(self):
        result = convert_string(SIMPLE_GEDCOM)
        self.assertIn("John Smith", result)
        self.assertIn("Jane Doe", result)


class TestConvertFile(unittest.TestCase):
    def test_converts_to_file(self):
        sample_path = os.path.join(os.path.dirname(__file__), "sample.ged")
        if not os.path.exists(sample_path):
            self.skipTest("sample.ged not found")

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".toon", delete=False
        ) as tmp:
            tmp_path = tmp.name

        try:
            convert_file(sample_path, tmp_path)
            with open(tmp_path, encoding="utf-8") as fh:
                content = fh.read()
            self.assertIn("John Smith", content)
            self.assertIn("=== INDIVIDUALS ===", content)
            self.assertIn("=== FAMILIES ===", content)
        finally:
            os.unlink(tmp_path)

    def test_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            convert_file("/nonexistent/path/file.ged")


if __name__ == "__main__":
    unittest.main()
