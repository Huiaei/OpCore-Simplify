import os
import tempfile
import types
import unittest

from Scripts.acpi_guru import ACPIGuru


def make_guru(acpi_directory, run_impl):
    """Build an ACPIGuru without touching the network or the local DSDT."""
    guru = object.__new__(ACPIGuru)
    guru.acpi_directory = acpi_directory
    guru.acpi = types.SimpleNamespace(iasl="/bin/false")
    guru.run = run_impl
    return guru


class TestWriteSSDTCleanup(unittest.TestCase):
    """A failed compilation must not leave its source in the finished EFI."""

    def test_failed_compile_removes_the_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            guru = make_guru(tmp, lambda args: ("Compilation failed.", 1))
            result = guru.write_ssdt("SSDT-PLUG-ALT", "DefinitionBlock (\"\", \"SSDT\", 2, \"ZPSS\", \"CpuPlugA\", 0x00003000)\n{\n}\n")
            self.assertFalse(result)
            self.assertEqual(os.listdir(tmp), [])

    def test_failed_compile_keeps_no_aml(self):
        with tempfile.TemporaryDirectory() as tmp:
            guru = make_guru(tmp, lambda args: ("Compilation failed.", 1))
            guru.write_ssdt("SSDT-TEST", "// nothing\n")
            self.assertFalse(os.path.exists(os.path.join(tmp, "SSDT-TEST.aml")))

    def test_successful_compile_keeps_the_aml_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            def run(args):
                # iasl writes <name>.aml next to the source
                aml = os.path.splitext(args["args"][1])[0] + ".aml"
                with open(aml, "wb") as f:
                    f.write(b"\x53\x53\x44\x54")
                return ("", 0)

            guru = make_guru(tmp, run)
            result = guru.write_ssdt("SSDT-USBX", "// usbx\n")
            self.assertTrue(result)
            self.assertEqual(os.listdir(tmp), ["SSDT-USBX.aml"])

    def test_compile_disabled_keeps_the_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            guru = make_guru(tmp, lambda args: ("", 0))
            result = guru.write_ssdt("SSDT-SKIP", "// skip\n", compile=False)
            self.assertFalse(result)
            self.assertEqual(os.listdir(tmp), ["SSDT-SKIP.dsl"])


if __name__ == "__main__":
    unittest.main()
