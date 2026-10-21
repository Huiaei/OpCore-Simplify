import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Scripts import dsdt


def make_table(signature, body=b""):
    """Build a minimal ACPI table: 4 byte signature, 4 byte length, 28 more."""
    length = 36 + len(body)
    return signature + length.to_bytes(4, "little") + bytes(28) + body


class SplitAcpiTableBlobTests(unittest.TestCase):
    def setUp(self):
        # Instantiating DSDT downloads/validates iasl, so bypass __init__.
        self.dsdt = dsdt.DSDT.__new__(dsdt.DSDT)

    def test_splits_concatenated_tables(self):
        first = make_table(b"FACP", b"facp")
        second = make_table(b"SSDT", b"one")
        third = make_table(b"SSDT", b"two")
        tables = self.dsdt._split_acpi_table_blob(first + second + third)
        self.assertEqual(tables, [first, second, third])

    def test_single_table_is_returned_as_is(self):
        table = make_table(b"DSDT", b"dsdt-body")
        self.assertEqual(self.dsdt._split_acpi_table_blob(table), [table])

    def test_trailing_partial_table_is_ignored(self):
        table = make_table(b"SSDT", b"payload")
        self.assertEqual(self.dsdt._split_acpi_table_blob(table + table[:20]), [table])

    def test_zero_length_header_stops_parsing(self):
        broken = b"SSDT" + (0).to_bytes(4, "little") + bytes(28)
        self.assertEqual(self.dsdt._split_acpi_table_blob(broken), [])

    def test_length_beyond_blob_stops_parsing(self):
        good = make_table(b"FACP")
        broken = b"SSDT" + (4096).to_bytes(4, "little") + bytes(28)
        self.assertEqual(self.dsdt._split_acpi_table_blob(good + broken), [good])

    def test_empty_blob(self):
        self.assertEqual(self.dsdt._split_acpi_table_blob(b""), [])


class WindowsApiDumpTests(unittest.TestCase):
    def setUp(self):
        self.dsdt = dsdt.DSDT.__new__(dsdt.DSDT)

    def test_returns_none_off_windows(self):
        if os.name == "nt":
            self.skipTest("only meaningful on non-Windows hosts")
        self.assertIsNone(self.dsdt.dump_tables_via_windows_api("SysReport/ACPI"))

    def test_acpi_guru_skips_automatic_dump_off_windows(self):
        from Scripts import acpi_guru

        guru = acpi_guru.ACPIGuru.__new__(acpi_guru.ACPIGuru)
        if os.name == "nt":
            self.skipTest("only meaningful on non-Windows hosts")
        self.assertFalse(guru._dump_tables_automatically())


if __name__ == "__main__":
    unittest.main()
