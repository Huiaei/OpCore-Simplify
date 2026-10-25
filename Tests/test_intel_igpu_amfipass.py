"""Regression tests for lzhoang2801/OpCore-Simplify#717.

Skylake and Kaby Lake integrated GPUs have no driver of their own from macOS 13
onwards, so the generator drives them through the Kaby Lake device-id spoof.
macOS 14 tightened AMFI library validation, and without AMFIPass the system
panics in endpointsecurityd while mapping IOSurface.  These tests pin the
selection logic and the display-connector hint that ships with it.
"""

import copy
import io
import os
import sys
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Scripts import kext_maestro
from Scripts.datasets import cpu_data
from Scripts.datasets import kext_data
from Scripts.kext_maestro import KextMaestro


def igpu(device_id, device_type="Integrated GPU", manufacturer="Intel"):
    return {
        "Device ID": device_id,
        "Device Type": device_type,
        "Manufacturer": manufacturer,
        "Codename": "",
    }


def hardware_report(gpu_props=None, platform="Desktop"):
    """A report shaped like the one issue #717 was filed with."""
    gpu_props = gpu_props or igpu("8086-191D")
    gpu_props.setdefault("Codename", "")

    return {
        "CPU": {
            "Manufacturer": "Intel",
            "Processor Name": "Xeon E3-1235L v5",
            "Codename": "Skylake",
            "Core Count": "4",
            "CPU Count": "1",
            "SIMD Features": ["SSE", "AVX2"],
        },
        "Motherboard": {
            "Platform": platform,
            "Name": "MAXSUN MS-H110ZL",
            "Chipset": "H110",
        },
        "BIOS": {"Version": "1.0", "Release Date": "2016-01-01", "Mode": "UEFI"},
        "GPU": {"Intel HD Graphics P530": gpu_props},
        "Monitor": {},
        "Network": {},
        "Sound": {},
        "Bluetooth": {},
        "Storage": {},
        "USB Controllers": {},
    }


def maestro():
    """A fresh KextMaestro whose kext table is untouched by other tests."""
    instance = KextMaestro()
    instance.kexts = copy.deepcopy(kext_data.kexts)
    for kext in instance.kexts:
        kext.checked = False
    return instance


class TestKabyLakeSpoofDetection(unittest.TestCase):
    def test_skylake_and_kaby_lake_ids_take_the_spoof(self):
        for device_id in ("8086-1912", "8086-191D", "8086-5916", "8086-5912", "8086-87C0"):
            with self.subTest(device_id=device_id):
                self.assertTrue(kext_maestro.intel_igpu_takes_kaby_lake_spoof(igpu(device_id)))

    def test_newer_intel_igpus_keep_their_own_driver(self):
        # Coffee Lake and Ice Lake are still native, so they need no AMFIPass.
        for device_id in ("8086-3E92", "8086-9B3E", "8086-8A52", "8086-9A49"):
            with self.subTest(device_id=device_id):
                self.assertFalse(kext_maestro.intel_igpu_takes_kaby_lake_spoof(igpu(device_id)))

    def test_discrete_and_amd_gpus_are_ignored(self):
        self.assertFalse(kext_maestro.intel_igpu_takes_kaby_lake_spoof(igpu("8086-1912", "Discrete GPU")))
        self.assertFalse(kext_maestro.intel_igpu_takes_kaby_lake_spoof(igpu("1002-15D8", manufacturer="AMD")))
        self.assertFalse(kext_maestro.intel_igpu_takes_kaby_lake_spoof({}))
        self.assertFalse(kext_maestro.intel_igpu_takes_kaby_lake_spoof(None))


class TestAmfiPassSelection(unittest.TestCase):
    def test_macos_14_and_newer_need_amfipass(self):
        instance = maestro()
        for macos_version in ("23.0.0", "24.0.0", "25.0.0"):
            with self.subTest(macos_version=macos_version):
                self.assertTrue(instance.intel_igpu_needs_amfipass("Intel HD Graphics P530", igpu("8086-191D"), macos_version))

    def test_macos_13_and_older_do_not(self):
        instance = maestro()
        for macos_version in ("21.0.0", "22.0.0", "22.99.99"):
            with self.subTest(macos_version=macos_version):
                self.assertFalse(instance.intel_igpu_needs_amfipass("Intel HD Graphics P530", igpu("8086-191D"), macos_version))

    def test_disabled_igpu_does_not_pull_amfipass(self):
        instance = maestro()
        for label in ("Intel HD Graphics P530", "GPU: Intel HD Graphics P530", "Integrated GPU: Intel HD Graphics P530"):
            with self.subTest(label=label):
                self.assertFalse(
                    instance.intel_igpu_needs_amfipass("Intel HD Graphics P530", igpu("8086-191D"), "24.0.0", [label])
                )

    def test_enabled_intel_igpus_reports_only_enabled_cards(self):
        instance = maestro()
        report = hardware_report()
        self.assertEqual(instance.enabled_intel_igpus(report), ["Intel HD Graphics P530"])
        self.assertEqual(instance.enabled_intel_igpus(report, ["Integrated GPU: Intel HD Graphics P530"]), [])

    def test_select_required_kexts_adds_amfipass_without_root_patches(self):
        instance = maestro()
        output = io.StringIO()

        with redirect_stdout(output):
            needs_oclp = instance.select_required_kexts(hardware_report(), "24.0.0", False, [])

        selected = [kext.name for kext in instance.kexts if kext.checked]
        self.assertIn("AMFIPass", selected)
        self.assertIn("RestrictEvents", selected)
        self.assertIn("Lilu", selected)
        self.assertFalse(needs_oclp, "the device-id spoof must not enable the OCLP root-patch flow")
        self.assertIn("no native graphics driver in this macOS version", output.getvalue())

    def test_select_required_kexts_skips_amfipass_on_vintage_macos(self):
        instance = maestro()

        with redirect_stdout(io.StringIO()):
            instance.select_required_kexts(hardware_report(), "20.0.0", False, [])

        self.assertNotIn("AMFIPass", [kext.name for kext in instance.kexts if kext.checked])

    def test_amfipass_metadata_matches_the_driver_the_issue_used(self):
        kext = kext_data.kexts[kext_data.kext_index_by_name["AMFIPass"]]
        self.assertEqual(kext.name, "AMFIPass")
        self.assertIn("Lilu", kext.requires_kexts)


class TestDisplayOutputHint(unittest.TestCase):
    def test_hint_is_silent_without_an_intel_igpu(self):
        self.assertEqual(kext_maestro.intel_igpu_display_hint([]), [])

    def test_hint_names_the_gpu_and_the_connector_guide(self):
        lines = kext_maestro.intel_igpu_display_hint(["Intel HD Graphics P530"])
        joined = "\n".join(lines)

        self.assertTrue(joined.startswith("* Display Output (Intel HD Graphics P530):"))
        self.assertIn("dortania.github.io/OpenCore-Post-Install/gpu-patching/intel-patching/connector.html", joined)
        self.assertIn("framebuffer-conX-*", joined)

    def test_hint_explains_igfxvesa_when_the_generator_added_it(self):
        lines = kext_maestro.intel_igpu_display_hint(["Intel HD Graphics P530"], ["-v", "debug=0x100", "-igfxvesa"])
        joined = "\n".join(lines)

        self.assertIn("-igfxvesa", joined)
        self.assertIn("disables graphics acceleration", joined)

    def test_hint_does_not_mention_igfxvesa_without_it(self):
        lines = kext_maestro.intel_igpu_display_hint(["Intel HD Graphics P530"], ["-v", "debug=0x100"])
        joined = "\n".join(lines)

        self.assertNotIn("-igfxvesa", joined)
        self.assertNotIn("disables graphics acceleration", joined)


if __name__ == "__main__":
    unittest.main()
