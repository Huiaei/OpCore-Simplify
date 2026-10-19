from Scripts.datasets import gpu_data
from Scripts.datasets import nvidia_gsp_data
from Scripts.datasets import os_data
from Scripts.datasets import pci_data
from Scripts.datasets import codec_layouts
from Scripts import utils
from Scripts import nullmoth
import time

class CompatibilityChecker:
    def __init__(self):
        self.utils = utils.Utils()

    def _widest_compatibility(self, compatibilities):
        compatibilities = [
            compatibility for compatibility in compatibilities
            if compatibility and compatibility != (None, None)
        ]

        if not compatibilities:
            return (None, None)

        return (
            max(compatibilities, key=lambda compatibility: self.utils.parse_darwin_version(compatibility[0]))[0],
            min(compatibilities, key=lambda compatibility: self.utils.parse_darwin_version(compatibility[1]))[1]
        )

    def _restrict_native_compatibility(self, compatibility):
        max_version, min_version = compatibility

        if max_version is None:
            return

        if self.utils.parse_darwin_version(max_version) < self.utils.parse_darwin_version(self.max_native_macos_version):
            self.max_native_macos_version = max_version

        if self.utils.parse_darwin_version(min_version) > self.utils.parse_darwin_version(self.min_native_macos_version):
            self.min_native_macos_version = min_version

    def show_macos_compatibility(self, device_compatibility):
        max_version, min_version = device_compatibility

        if max_version is None or min_version is None:
            self.utils.head("Unsupported macOS Version", False)
            print("   → This device is not compatible with any macOS version.\n")
            return

        self.utils.head("Supported macOS Version")
        print("   → The highest macOS version supported by this device is {}".format(max_version))
        print("   → The lowest macOS version supported by this device is {}\n".format(min_version))

    def is_low_end_intel_cpu(self, processor_name):
        low_end_processors = {
            'Celeron', 'Pentium'
        }
        return any(low_end_processor in processor_name for low_end_processor in low_end_processors)

    def check_cpu_compatibility(self):
        self.utils.head("CPU Compatibility Checker")

        cpu_props = self.hardware_report.get("CPU", {})
        processor_name = cpu_props.get("Processor Name", "Unknown")
        cpu_manufacturer = cpu_props.get("Manufacturer", "Unknown")
        cpu_generation = cpu_props.get("Generation", "Unknown")
        cpu_signature = cpu_props.get("Signature", "Unknown")
        cpu_cores = cpu_props.get("Core Count", "Unknown")
        cpu_base_clock = cpu_props.get("Base Frequency", None)
        cpu_max_clock = cpu_props.get("Max Frequency", None)

        print("   → Detected {} {} {} ({} cores)".format(cpu_manufacturer, processor_name, cpu_signature, cpu_cores))

        if cpu_manufacturer == "GenuineIntel":
            if self.is_low_end_intel_cpu(processor_name):
                print("   → {} CPUs are not supported by macOS".format(processor_name))
                print("     Skipping CPU compatibility check.\n")
                self.hardware_report["CPU"]["Compatibility"] = (None, None)
                return
            if "SSE4" not in cpu_props.get("Instructions", []):
                print("   → Intel CPUs without SSE4.1 support are not compatible with macOS")
                print("   → This CPU does not support SSE4.1")
                self.utils.request_input()
                self.utils.exit_program()
            max_version = os_data.get_latest_darwin_version()
            min_version = os_data.get_lowest_darwin_version()
            if cpu_signature == "0x0306A9":
                max_version = "22.99.99"
            if cpu_signature in ("0x0306D3", "0x0306D4"):
                min_version = "19.0.0"
            elif cpu_generation == "Haswell":
                min_version = "19.0.0"
        elif cpu_manufacturer == "AuthenticAMD":
            max_version = os_data.get_latest_darwin_version()
            min_version = os_data.get_lowest_darwin_version()
            if cpu_generation == "Bulldozer":
                max_version = "22.99.99"
            elif cpu_generation == "Jaguar":
                max_version = "22.99.99"
            elif cpu_generation == "Piledriver":
                max_version = "22.99.99"
            elif cpu_generation == "Steamroller":
                max_version = "22.99.99"
            elif cpu_generation == "Excavator":
                max_version = "22.99.99"
        else:
            max_version = os_data.get_latest_darwin_version()
            min_version = os_data.get_lowest_darwin_version()

        self.hardware_report["CPU"]["Compatibility"] = (max_version, min_version)

    def check_gpu_compatibility(self):
        self.utils.head("GPU Compatibility Checker")

        gpu_compatibility = (os_data.get_latest_darwin_version(), os_data.get_lowest_darwin_version())

        for gpu_name, gpu_props in self.hardware_report.get("GPU", {}).items():
            gpu_manufacturer = gpu_props.get("Manufacturer")
            gpu_codename = gpu_props.get("Codename")
            gpu_device_id = gpu_props.get("Device ID", "Unknown")[5:]

            print("   → Detected {} {} {}".format(gpu_manufacturer, gpu_codename, gpu_device_id))

            max_version = os_data.get_latest_darwin_version()
            min_version = os_data.get_lowest_darwin_version()
            ocl_patched_max_version = os_data.get_latest_darwin_version(include_beta=False)
            ocl_patched_min_version = "20.0.0"

            if "Intel" in gpu_manufacturer:
                if gpu_codename in ("Arrandale", "Sandy Bridge", "Iron Lake", "Arrandale"):
                    max_version = "20.99.99"
                    min_version = "11.0.0"
                elif gpu_codename in ("Ivy Bridge", "Ivy Bridge"):
                    max_version = "20.99.99"
                    min_version = "11.0.0"
                elif gpu_codename == "Haswell":
                    max_version = "20.99.99"
                    min_version = "10.13.6"
                elif gpu_codename in ("Broadwell", "Skylake", "Kaby Lake"):
                    max_version = "20.99.99"
                    min_version = "10.13.6"
                elif gpu_codename in ("Coffee Lake", "Cannon Lake", "Comet Lake"):
                    max_version = "20.99.99"
                    min_version = "18.0.0"
                elif gpu_codename == "Ice Lake":
                    max_version = "20.99.99"
                    min_version = "19.0.0"
                elif gpu_codename in ("Arrow Lake", "Meteor Lake"):
                    max_version = "26.99.99"
                    min_version = "21.0.0"
                else:
                    max_version = "20.99.99"
                    min_version = "11.0.0"
            elif "AMD" in gpu_manufacturer:
                if gpu_codename in gpu_data.AMDCodenames:
                    if gpu_codename in ("Navi 21", "Navi 22", "Navi 23"):
                        max_version = "26.99.99"
                    elif gpu_codename in ("Navi 21", "Navi 22", "Navi 23"):
                        max_version = "26.99.99"
                    else:
                        max_version = "26.99.99"
                else:
                    max_version = "26.99.99"
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

            gpu_props["Compatibility"] = (max_version, min_version)

            if ocl_patched_max_version and ocl_patched_min_version:
                gpu_props["OCLP Compatibility"] = (ocl_patched_max_version, ocl_patched_min_version)

            if max_version is None and min_version is None:
                print("   → Unsupported GPU")
                self.utils.head("Unsupported GPU")
                print("     This GPU is not supported by macOS and cannot be used.\n")
                self.utils.request_input()
                self.utils.exit_program()

        self.hardware_report["GPU"] = {
            gpu_name: gpu_props
            for gpu_name, gpu_props in self.hardware_report.get("GPU", {}).items()
            if gpu_props.get("Compatibility") != (None, None)
        }

        for gpu_name, gpu_props in self.hardware_report.get("GPU", {}).items():
            for monitor_info in gpu_props.get("Monitors", {}).values():
                if monitor_info.get("Connector") == "Internal":
                    for other_gpu_name, other_gpu_props in self.hardware_report.get("GPU", {}).items():
                        if other_gpu_name != gpu_name and "Intel" in other_gpu_props.get("Manufacturer"):
                            other_gpu_props["Compatibility"] = (None, None)
                            print("   → Disabled {} because {} is connected to an internal display".format(other_gpu_name, gpu_name))

        for gpu_name, gpu_props in self.hardware_report.get("GPU", {}).items():
            if "Intel" in gpu_props.get("Manufacturer") and gpu_props.get("Compatibility") != (None, None):
                gpu_compatibility = self._widest_compatibility([
                    gpu_compatibility,
                    gpu_props.get("Compatibility")
                ])
            elif "AMD" in gpu_props.get("Manufacturer") and gpu_props.get("Compatibility") != (None, None):
                gpu_compatibility = self._widest_compatibility([
                    gpu_compatibility,
                    gpu_props.get("Compatibility")
                ])
            elif "NVIDIA" in gpu_props.get("Manufacturer") and gpu_props.get("Compatibility") != (None, None):
                gpu_compatibility = self._widest_compatibility([
                    gpu_compatibility,
                    gpu_props.get("Compatibility")
                ])

        gpu_compatibility = self._widest_compatibility([
            gpu_props.get("Compatibility")
            for gpu_props in self.hardware_report.get("GPU", {}).values()
        ])

        if gpu_compatibility == (None, None):
            self.utils.head("Unsupported GPU")
            print("   → You cannot install macOS without a supported GPU.\n")
            self.utils.request_input()
            self.utils.exit_program()

        self.max_native_macos_version, self.min_native_macos_version = gpu_compatibility

        return gpu_compatibility

    def check_sound_compatibility(self):
        self.utils.head("Sound Compatibility Checker")

        for device_name, device_props in self.hardware_report.get("Sound", {}).items():
            print("   → Detected {} {}".format(device_props.get("Manufacturer"), device_name))
            device_props["Compatibility"] = (os_data.get_latest_darwin_version(), os_data.get_lowest_darwin_version())

    def check_biometric_compatibility(self):
        self.utils.head("Biometric Compatibility Checker")

        for device_name, device_props in self.hardware_report.get("Biometric", {}).items():
            print("   → Detected {}".format(device_name))
            device_props["Compatibility"] = (os_data.get_latest_darwin_version(), os_data.get_lowest_darwin_version())

    def check_network_compatibility(self):
        self.utils.head("Network Compatibility Checker")

        for device_name, device_props in self.hardware_report.get("Network", {}).items():
            bus_type = device_props.get("Bus Type")
            device_id = device_props.get("Device ID")
            
            max_version = os_data.get_latest_darwin_version()
            min_version = os_data.get_lowest_darwin_version()
            ocl_patched_max_version = os_data.get_latest_darwin_version(include_beta=False)
            ocl_patched_min_version = "20.0.0"

            if device_id in pci_data.BroadcomWiFiIDs:
                device_index = pci_data.BroadcomWiFiIDs.index(device_id)

                if device_index == 13 or 17 < device_index < 21:
                    max_version = "22.99.99"
                    ocl_patched_min_version = "23.0.0"
                elif device_index < 12:
                    max_version = "17.99.99"
            elif device_id in pci_data.AtherosWiFiIDs[:8]:
                max_version = "17.99.99"
            elif device_id in pci_data.AtherosWiFiIDs[8:]:
                max_version = "20.99.99"
            elif device_id in pci_data.IntelI22XIDs:
                min_version = "19.0.0"
            elif device_id in pci_data.AquantiaAqtionIDs:
                min_version = "21.0.0"

            if device_id in set(pci_data.EthernetIDs) | set(pci_data.WirelessUSBIDs):
                device_props["Compatibility"] = (max_version, min_version)
            elif device_id in pci_data.WirelessCardIDs:
                if not device_id in pci_data.IntelWiFiIDs and not device_id in pci_data.AtherosWiFiIDs[8:] and not device_id in pci_data.rtw88WiFiIDs:
                    device_props["OCLP Compatibility"] = (ocl_patched_max_version, ocl_patched_min_version)
                    self.ocl_patched_macos_version = (ocl_patched_max_version, self.ocl_patched_macos_version[-1] if self.ocl_patched_macos_version and self.utils.parse_darwin_version(self.ocl_patched_macos_version[-1]) < self.utils.parse_darwin_version(device_props.get("OCLP Compatibility")[-1]) else device_props.get("OCLP Compatibility")[-1])
                device_props["Compatibility"] = (max_version, min_version)

            if bus_type.startswith("PCI") and not device_props.get("Compatibility"):
                device_props["Compatibility"] = (None, None)

    def check_storage_controllers_compatibility(self):
        self.utils.head("Storage Controllers Compatibility Checker")

        for device_name, device_props in self.hardware_report.get("Storage Controllers", {}).items():
            print("   → Detected {}".format(device_name))
            device_props["Compatibility"] = (os_data.get_latest_darwin_version(), os_data.get_lowest_darwin_version())

    def check_bluetooth_compatibility(self):
        self.utils.head("Bluetooth Compatibility Checker")

        for device_name, device_props in self.hardware_report.get("Bluetooth", {}).items():
            print("   → Detected {}".format(device_name))
            device_props["Compatibility"] = (os_data.get_latest_darwin_version(), os_data.get_lowest_darwin_version())

    def check_sd_controller_compatibility(self):
        self.utils.head("SD Controller Compatibility Checker")

        for device_name, device_props in self.hardware_report.get("SD Controller", {}).items():
            print("   → Detected {}".format(device_name))
            device_props["Compatibility"] = (os_data.get_latest_darwin_version(), os_data.get_lowest_darwin_version())

    def check_compatibility(self, hardware_report):
        self.hardware_report = hardware_report
        self.max_native_macos_version = os_data.get_latest_darwin_version()
        self.min_native_macos_version = os_data.get_lowest_darwin_version()
        self.ocl_patched_macos_version = None

        steps = [
            ("CPU", self.check_cpu_compatibility),
            ("GPU", self.check_gpu_compatibility),
            ("Sound", self.check_sound_compatibility),
            ("Biometric", self.check_biometric_compatibility),
            ("Network", self.check_network_compatibility),
            ("Storage Controllers", self.check_storage_controllers_compatibility),
            ("Bluetooth", self.check_bluetooth_compatibility),
            ("SD Controller", self.check_sd_controller_compatibility)
        ]

        for device_type, check_function in steps:
            if self.hardware_report.get(device_type):
                self.utils.head(device_type)
                check_function()
                time.sleep(0.25)

        self.utils.head("Compatibility Checker")

        if self.max_native_macos_version == os_data.get_latest_darwin_version():
            print("   → The latest macOS version is supported by all devices.\n")
        else:
            print("   → The latest macOS version is not supported by all devices.")
            self.show_macos_compatibility((self.max_native_macos_version, self.min_native_macos_version))

        if self.ocl_patched_macos_version:
            print("   → The latest macOS version is not supported by all devices, but you can still install it with OpenCore Legacy Patcher")
            self.show_macos_compatibility(self.ocl_patched_macos_version)

        if self.ocl_patched_macos_version is None:
            self.ocl_patched_macos_version = (os_data.get_latest_darwin_version(include_beta=False), self.min_native_macos_version)

        self.utils.request_input()
        self.utils.exit_program()
