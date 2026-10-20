"""Self-test for the NullMoth NVIDIA driver adaptation.

Run:  python3 Scripts/nullmoth_selftest.py

Covers the rules the fork must reproduce from 1401 (p1401/nullmoth.py) and the
driver's README, and prints a PASS/FAIL line per rule.  The last check is the
acceptance bar 1401's test suite uses: the produced config.plist must still be
a structurally valid OpenCore config.
"""

import copy
import os
import plistlib
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Scripts import nullmoth
from Scripts.datasets import nvidia_gsp_data

GUID = "7C436110-AB2A-4BBB-A880-FE41995C9F82"
RESULTS = []


def check(name, condition, detail=""):
    RESULTS.append((name, bool(condition), detail))


def base_config():
    return {
        "ACPI": {"Add": [], "Delete": [], "Patch": []},
        "Booter": {"MmioWhitelist": [], "Patch": [], "Quirks": {"ResizeAppleGpuBars": -1}},
        "DeviceProperties": {"Add": {}},
        "Kernel": {"Add": [], "Block": [], "Patch": []},
        "Misc": {"Security": {"SecureBootModel": "Default"}, "Tools": []},
        "NVRAM": {"Add": {GUID: {"boot-args": "-v debug=0x100 keepsyms=1"}}, "Delete": {GUID: []}},
        "UEFI": {"Quirks": {"ResizeGpuBars": -1}},
    }


def desktop_report(device_id="10DE-2D05", platform="Desktop", extra=None):
    gpu = {"Manufacturer": "NVIDIA", "Device Type": "Discrete GPU", "Device ID": device_id, "Codename": ""}
    report = {"Motherboard": {"Platform": platform, "Name": "Test Board", "Chipset": "AMD B650E"}, "GPU": {"NVIDIA GeForce RTX": gpu}}
    if extra:
        report["GPU"].update(extra)
    return report


def kext_names(kexts):
    return [getattr(kext, "name", kext) for kext in kexts or []]


# ---------------------------------------------------------------- card table
check("GSP table loaded", len(nvidia_gsp_data.SUPPORTED_DEVICES) >= 200, "{} ids".format(len(nvidia_gsp_data.SUPPORTED_DEVICES)))
check("GSP tested list", nvidia_gsp_data.TESTED_DEVICES == {"2D05": "NVIDIA GeForce RTX 5060"})
check("RTX 5060 (2D05) supported", nullmoth.NullMoth.supported({"Manufacturer": "NVIDIA", "Device Type": "Discrete GPU", "Device ID": "10DE-2D05"}))
check("bare device id supported", nullmoth.NullMoth.supported({"Manufacturer": "NVIDIA", "Device Type": "Discrete GPU", "Device ID": "2D05"}))
check("RTX 2080 Ti (1E04) supported", nullmoth.NullMoth.supported({"Manufacturer": "NVIDIA", "Device Type": "Discrete GPU", "Device ID": "10DE-1E04"}))
check("Quadro RTX 6000 (1E30) supported", nullmoth.NullMoth.supported({"Manufacturer": "NVIDIA", "Device Type": "Discrete GPU", "Device ID": "10DE-1E30"}))
check("Pascal GTX 1080 (1B80) NOT supported", not nullmoth.NullMoth.supported({"Manufacturer": "NVIDIA", "Device Type": "Discrete GPU", "Device ID": "10DE-1B80"}))
check("Kepler GTX 680 (1180) NOT supported", not nullmoth.NullMoth.supported({"Manufacturer": "NVIDIA", "Device Type": "Discrete GPU", "Device ID": "10DE-1180"}))
check("Maxwell GTX 980 (13C0) NOT supported", not nullmoth.NullMoth.supported({"Manufacturer": "NVIDIA", "Device Type": "Discrete GPU", "Device ID": "10DE-13C0"}))
check("AMD card NOT matched", not nullmoth.NullMoth.supported({"Manufacturer": "AMD", "Device Type": "Discrete GPU", "Device ID": "1002-744C"}))
check("Intel iGPU NOT matched", not nullmoth.NullMoth.supported({"Manufacturer": "Intel", "Device Type": "Integrated GPU", "Device ID": "8086-3E92"}))

# ------------------------------------------------------------- compatibility
report = desktop_report()
check("mark() returns the card", nullmoth.NullMoth.mark(report) == ["NVIDIA GeForce RTX"])
check("mark() sets Sequoia compatibility", report["GPU"]["NVIDIA GeForce RTX"]["Compatibility"] == nullmoth.NullMoth.SEQUOIA)
check("mark() drops OCLP Compatibility", "OCLP Compatibility" not in report["GPU"]["NVIDIA GeForce RTX"])
check("mark() fills the codename", report["GPU"]["NVIDIA GeForce RTX"]["Codename"] == "NullMoth driver")

report = desktop_report("10DE-1B80")
check("Pascal card is left alone", nullmoth.NullMoth.mark(report) == [])
check("Pascal keeps no compatibility", report["GPU"]["NVIDIA GeForce RTX"].get("Compatibility") is None)

# --------------------------------------------------------------- config pass
report = desktop_report()
config = base_config()
check("apply() reports a supported card", nullmoth.NullMoth.apply(config, report, kexts=[]) is True)

boot_args = config["NVRAM"]["Add"][GUID]["boot-args"]
for arg in nullmoth.NullMoth.BOOT_ARGS:
    check("boot-args contains {}".format(arg), arg in boot_args)
check("boot-args keeps the engine's args", "-v debug=0x100 keepsyms=1" in boot_args)
check("csr-active-config is <430A0000>", config["NVRAM"]["Add"][GUID]["csr-active-config"] == nullmoth.NullMoth.SIP_DRIVER)
check("csr-active-config hex is 430A0000", config["NVRAM"]["Add"][GUID]["csr-active-config"].hex() == "430a0000")
check("csr-active-config is rewritten each boot", "csr-active-config" in config["NVRAM"]["Delete"][GUID])
check("boot-args NOT in NVRAM Delete", "boot-args" not in config["NVRAM"]["Delete"][GUID])
check("SecureBootModel Disabled", config["Misc"]["Security"]["SecureBootModel"] == "Disabled")
check("IONDRVSupport blocked", any(item.get("Identifier") == nullmoth.NullMoth.IONDRV_SUPPORT and item.get("Strategy") == "Exclude" for item in config["Kernel"]["Block"]))
check("driver kexts NOT injected", not any(item.get("BundlePath", "").startswith(("NVRM", "NVAccel", "NVRMFB", "NVRMAGDC")) for item in config["Kernel"]["Add"]))
check("installed BARs keep firmware sizing", config["Booter"]["Quirks"]["ResizeAppleGpuBars"] == -1 and config["UEFI"]["Quirks"]["ResizeGpuBars"] == -1)

# idempotency: a second pass must not duplicate anything
before = copy.deepcopy(config)
nullmoth.NullMoth.apply(config, report, kexts=[])
check("apply() is idempotent", config == before)

# WhateverGreen coexistence
report = desktop_report()
config = base_config()
nullmoth.NullMoth.apply(config, report, kexts=["WhateverGreen"])
check("gfxrst=4 added with WhateverGreen", "gfxrst=4" in config["NVRAM"]["Add"][GUID]["boot-args"])
report = desktop_report()
config = base_config()
nullmoth.NullMoth.apply(config, report, kexts=["Lilu", "AMFIPass"])
check("gfxrst=4 absent without WhateverGreen", "gfxrst=4" not in config["NVRAM"]["Add"][GUID]["boot-args"])

# card-hiding boot arguments must not survive
report = desktop_report()
config = base_config()
config["NVRAM"]["Add"][GUID]["boot-args"] = "-v nv_disable=1 -wegnoegpu keepsyms=1"
nullmoth.NullMoth.apply(config, report, kexts=[])
for arg in nullmoth.NullMoth.FORBIDDEN_BOOT_ARGS:
    check("{} removed".format(arg), arg not in config["NVRAM"]["Add"][GUID]["boot-args"])

# installer values
report = desktop_report()
report["Installing macOS"] = True
config = base_config()
nullmoth.NullMoth.apply(config, report, kexts=[])
check("installer ResizeAppleGpuBars = 0", config["Booter"]["Quirks"]["ResizeAppleGpuBars"] == 0)
check("installer ResizeGpuBars = -1", config["UEFI"]["Quirks"]["ResizeGpuBars"] == -1)
check("installer keeps IONDRVSupport unblocked", config["Kernel"]["Block"] == [])
check("installer still sets SIP", config["NVRAM"]["Add"][GUID]["csr-active-config"].hex() == "430a0000")

# laptop: Optimus note + ACPI wake
laptop = desktop_report("10DE-2860", platform="Laptop", extra={"Intel Arc Graphics": {"Manufacturer": "Intel", "Device Type": "Integrated GPU", "Device ID": "8086-7D55"}})
laptop["GPU"]["NVIDIA GeForce RTX"]["PCI Path"] = "PciRoot(0x0)/Pci(0x1,0x0)/Pci(0x0,0x0)"
check("mux note returned on a laptop", nullmoth.NullMoth.mux_help(laptop) is not None)
check("no mux note on a desktop", nullmoth.NullMoth.mux_help(desktop_report()) is None)
config = base_config()
nullmoth.NullMoth.apply(config, laptop, kexts=[])
check("acpi-wake-type set for the NVIDIA card", config["DeviceProperties"]["Add"].get("PciRoot(0x0)/Pci(0x1,0x0)/Pci(0x0,0x0)", {}).get("acpi-wake-type") == 1)

# disabled / unsupported machines are untouched
report = desktop_report("10DE-1B80")
config = base_config()
check("apply() no-ops on an unsupported card", nullmoth.NullMoth.apply(config, report, kexts=[]) is False)
check("config untouched for an unsupported card", config["NVRAM"]["Add"][GUID].get("csr-active-config") is None)

# a card the user disabled must not activate the driver (1401's
# tests/test_disabled_gpu_policy.py)
for label in ("GPU: NVIDIA GeForce RTX", "NVIDIA GeForce RTX", "Discrete GPU: NVIDIA GeForce RTX"):
    check("gpu_disabled() recognises {!r}".format(label), nullmoth.NullMoth.gpu_disabled(
        "NVIDIA GeForce RTX", desktop_report()["GPU"]["NVIDIA GeForce RTX"], [label]) is True)
check("gpu_disabled() ignores unrelated labels", nullmoth.NullMoth.gpu_disabled(
    "NVIDIA GeForce RTX", desktop_report()["GPU"]["NVIDIA GeForce RTX"], ["Audio: Foo"]) is False)
config = base_config()
check("apply() no-ops when the only card is disabled", nullmoth.NullMoth.apply(
    config, desktop_report(), kexts=[], disabled_devices=["GPU: NVIDIA GeForce RTX"]) is False)
check("config untouched for a disabled card", config["NVRAM"]["Add"][GUID].get("csr-active-config") is None)
check("cards() skips disabled cards", nullmoth.NullMoth.cards(
    desktop_report(), disabled_devices=["GPU: NVIDIA GeForce RTX"]) == [])
check("cards() keeps live cards", nullmoth.NullMoth.cards(desktop_report()) == ["NVIDIA GeForce RTX"])

# two cards, one disabled -> the live one still drives the config
two = desktop_report()
two["GPU"]["NVIDIA GeForce RTX 5070"] = {"Manufacturer": "NVIDIA", "Device Type": "Discrete GPU", "Device ID": "10DE-2C02", "Codename": ""}
config = base_config()
check("apply() succeeds when one of two cards is live", nullmoth.NullMoth.apply(
    config, two, kexts=[], disabled_devices=["GPU: NVIDIA GeForce RTX 5070"]) is True)

# ------------------------------------------------------------ structural pass
try:
    plistlib.dumps(config)
    check("config.plist is serialisable", True)
except Exception as e:
    check("config.plist is serialisable", False, str(e))

report = desktop_report()
config = base_config()
nullmoth.NullMoth.apply(config, report, kexts=["Lilu", "AMFIPass"])
try:
    plistlib.loads(plistlib.dumps(config))
    check("config.plist round-trips", True)
except Exception as e:
    check("config.plist round-trips", False, str(e))

# ------------------------------------------------------------------- report
failed = [result for result in RESULTS if not result[1]]
for name, ok, detail in RESULTS:
    print("{} {}{}".format("PASS" if ok else "FAIL", name, " ({})".format(detail) if detail else ""))
print("")
print("{} passed, {} failed, {} total".format(len(RESULTS) - len(failed), len(failed), len(RESULTS)))
sys.exit(1 if failed else 0)
