from Scripts.datasets import gpu_data
from Scripts.datasets import os_data
from Scripts.datasets import pci_data
from Scripts.datasets import codec_layouts
from Scripts.datasets import nvidia_gsp_data
from Scripts import nullmoth
from Scripts import smbios
from Scripts import utils

import re


class CompatibilityChecker:

    def __init__(self):
        self.utils = utils.Utils()
        self.hardware_report = None
        self.max_native_macos_version = {"OS": []}
        self.min_native_macos_version = {"OS": []}

    def _widest_compatibility(self, compatibilities):
        """Return the widest (max, min) Darwin version pair that fits every entry."""

        max_versions = [maximum for maximum, _ in compatibilities if maximum is not None]
        min_versions = [minimum for _, minimum in compatibilities if minimum is not None]

        if not max_versions or not min_versions:
            return None, None

        return max(max_versions), min(min_versions)

    def _restrict_native_compatibility(self, compatibility):
        """Narrow the supported native macOS range to the given (max, min) pair."""

        max_version, min_version = compatibility

        if max_version is not None and min_version is not None:
            if self.utils.parse_darwin_version(max_version) < self.utils.parse_darwin_version(self.max_native_macos_version["OS"][0] if self.max_native_macos_version["OS"] else "99.99.99"):
                self.max_native_macos_version["OS"] = [max_version]
            if self.utils.parse_darwin_version(min_version) > self.utils.parse_darwin_version(self.min_native_macos_version["OS"][0] if self.min_native_macos_version["OS"] else "0.0.0"):
                self.min_native_macos_version["OS"] = [min_version]

    def show_macos_compatibility(self, device_compatibility):
        """Return a coloured, human-readable compatibility range."""

        if not device_compatibility:
            return "Natively supported"

        max_version, min_version = device_compatibility

        if max_version is None or min_version is None:
            return "\033[1;31mUnsupported\033[0m"

        max_name = os_data.get_macos_name_by_darwin(max_version)
        min_name = os_data.get_macos_name_by_darwin(min_version)

        if max_version == min_version:
            return "macOS {} ({})".format(max_name, max_version)

        return "macOS {} ({}) - {} ({})".format(min_name, min_version, max_name, max_version)

    def is_low_end_intel_cpu(self, processor_name):
        return "Celeron" in processor_name or "Pentium" in processor_name

    def check_cpu_compatibility(self):
        hardware_report = self.hardware_report

        cpu_props = hardware_report.get("CPU", {})
        cpu_codename = cpu_props.get("Codename")
        cpu_name = cpu_props.get("Processor Name") or cpu_props.get("Processor")

        max_version = os_data.get_latest_darwin_version()
        min_version = os_data.get_lowest_darwin_version()

        if "SSE4" not in cpu_props.get("Features", ""):
            self.utils.head("Unsupported CPU")
            print("")
            print("Your CPU does not support SSE4.2 instructions, which are required")
            print("to run macOS on non-Apple hardware.")
            print("")
            self.utils.request_input()
            self.utils.exit_program()

        if cpu_codename in ("Penryn", "Nehalem", "Westmere"):
            max_version = "19.99.99"
        elif cpu_codename in ("Sandy Bridge", "Ivy Bridge"):
            max_version = "20.99.99"
        elif cpu_codename in ("Haswell", "Broadwell"):
            min_version = "20.0.0" if cpu_codename == "Haswell" else min_version
        elif cpu_codename in ("Skylake", "Kaby Lake"):
            pass
        elif cpu_codename in ("Coffee Lake", "Comet Lake"):
            min_version = "18.0.0" if cpu_codename == "Coffee Lake" else min_version

        if cpu_props.get("Manufacturer") == "Intel" and self.is_low_end_intel_cpu(cpu_name):
            min_version = "20.0.0"

        cpu_props["Compatibility"] = (max_version, min_version)

        self._restrict_native_compatibility((max_version, min_version))

    def check_gpu_compatibility(self):
        hardware_report = self.hardware_report

        gpu_props = None

        max_version = os_data.get_latest_darwin_version()
        min_version = os_data.get_lowest_darwin_version()

        ocl_patched_max_version = os_data.get_latest_darwin_version(include_beta=False)
        ocl_patched_min_version = "20.0.0"

        for gpu_name, gpu_props in hardware_report.get("GPU", {}).items():
            gpu_manufacturer = gpu_props.get("Manufacturer")
            gpu_codename = gpu_props.get("Codename")
            device_id = gpu_props.get("Device ID", "")[5:] if "-" in gpu_props.get("Device ID", "") else None

            max_version = os_data.get_latest_darwin_version()
            min_version = os_data.get_lowest_darwin_version()

            ocl_patched_max_version = os_data.get_latest_darwin_version(include_beta=False)
            ocl_patched_min_version = "20.0.0"

            if gpu_manufacturer == "AMD":
                if device_id in gpu_data.AMDCodenames:
                    if gpu_codename in ("Navi 21", "Navi 22", "Navi 23"):
                        min_version = "19.0.0"
                    elif gpu_codename in ("Vega 10", "Vega 20"):
                        min_version = "18.0.0"
                        max_version = "23.99.99"
                    elif gpu_codename in ("Sea Islands", "Southern Islands", "Terascale"):
                        max_version = "21.99.99"
                    else:
                        max_version = min_version = None
                else:
                    if gpu_props.get("Device Type") == "Integrated GPU":
                        min_version = "20.0.0"
                    else:
                        max_version = min_version = None
            elif gpu_manufacturer == "Intel":
                if gpu_props.get("Device Type") == "Integrated GPU":
                    if gpu_codename in ("Iron Lake", "Sandy Bridge", "Ivy Bridge", "Haswell", "Broadwell"):
                        pass
                    elif gpu_codename in ("Skylake", "Kaby Lake"):
                        min_version = "18.0.0"
                    elif gpu_codename in ("Coffee Lake", "Comet Lake"):
                        min_version = "19.0.0"
                    else:
                        min_version = "20.0.0"
                else:
                    max_version = min_version = None
            elif "NVIDIA" in gpu_manufacturer:
                if nullmoth.NullMoth.supported(gpu_props):
                    # The NullMoth driver (nullmoth/nvidia-macos-driver) drives
                    # Turing and newer cards on macOS 15 Sequoia.
                    max_version = nullmoth.NullMoth.SEQUOIA[0]
                    min_version = nullmoth.NullMoth.SEQUOIA[1]
                elif "Kepler" in gpu_codename:
                    max_version = "20.99.99"
                elif gpu_codename in ("Pascal", "Maxwell", "Fermi", "Tesla"):
                    max_version = "17.99.99"
                    min_version = "17.0.0"
                else:
                    max_version = min_version = None

            if gpu_props.get("Device Type") == "Integrated GPU" and gpu_manufacturer == "Intel":
                ocl_patched_max_version = ocl_patched_min_version = None

            gpu_props["Compatibility"] = (max_version, min_version)

            if max_version is not None and min_version is not None:
                gpu_props["OCLP Compatibility"] = (ocl_patched_max_version, ocl_patched_min_version)

        # A GPU whose internal monitor is driven by another GPU cannot be used
        # for graphics output on macOS.
        for gpu_name, gpu_props in hardware_report.get("GPU", {}).items():
            if gpu_props.get("Compatibility") in ((None, None), None):
                continue

            monitors = hardware_report.get("Monitor", {})

            if any(monitor_info.get("Connected GPU", gpu_name) == gpu_name and monitor_info.get("Connector Type") == "Internal"
                   for monitor_name, monitor_info in monitors.items()):
                continue

            if any(monitor_info.get("Connected GPU", gpu_name) != gpu_name for monitor_name, monitor_info in monitors.values() if monitor_info.get("Connector Type") == "Internal"):
                gpu_props["Compatibility"] = (None, None)

        self.max_native_macos_version["OS"] = [os_data.get_latest_darwin_version()]
        self.min_native_macos_version["OS"] = [os_data.get_lowest_darwin_version()]

        gpu_compatibilities = [gpu_props.get("Compatibility") for gpu_name, gpu_props in hardware_report.get("GPU", {}).items()]

        for gpu_props in hardware_report.get("GPU", {}).values():
            oclp_compatibility = gpu_props.pop("OCLP Compatibility", None)
            if oclp_compatibility and gpu_props.get("Compatibility") not in ((None, None), None):
                self.ocl_patched_macos_version = (ocl_patched_max_version, ocl_patched_min_version)

        gpu_compatibility = self._widest_compatibility(gpu_compatibilities)

        if gpu_compatibility == (None, None):
            self.utils.head("Unsupported GPU")
            print("")
            print("You cannot install macOS without a supported GPU.")
            print("")
            self.utils.request_input()
            self.utils.exit_program()

        self._restrict_native_compatibility(gpu_compatibility)

    def check_compatibility(self, hardware_report):
        self.hardware_report = hardware_report

        steps = [
            ("CPU", self.check_cpu_compatibility),
            ("GPU", self.check_gpu_compatibility),
            ("Biometric", self.check_biometric_compatibility),
        ]

        for device_type, step in steps:
            self.utils.head("Checking {} compatibility".format(device_type))
            print("")
            print("Checking for compatible {}...".format(device_type.lower()))
            step()
            print("")

        for device_type in ("Motherboard", "Monitor", "Network", "Sound Controller", "Biometric", "Storage Controller", "Serial Bus Controller"):
            self.utils.head("Checking {} compatibility".format(device_type))
            print("")
            for device_name, device_props in hardware_report.get(device_type, {}).items():
                print("{}- {}: {}".format(" "*3, device_name, self.show_macos_compatibility(device_props.get("Compatibility"))))

        self.utils.request_input()

        return hardware_report, (self.min_native_macos_version, self.max_native_macos_version), self.ocl_patched_macos_version