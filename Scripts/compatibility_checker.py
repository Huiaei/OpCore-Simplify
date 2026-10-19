from Scripts.datasets import gpu_data
from Scripts.datasets import nvidia_gsp_data
from Scripts.datasets import os_data
from Scripts import utils
import platform
import datetime
import time


class CompatibilityChecker:
    def __init__(self):
        self.utils = utils.Utils()

    def _widest_compatibility(self, compatibilities):
        """
        Return the widest compatibility of the given list.

        Parameters
        ----------
        compatibilities : list
            List of compatibility tuples.

        Returns
        -------
        tuple
            (Max, Min) of the given compatibility list.
        """
        compatibility = (None, None)

        for max_version, min_version in compatibilities:
            if max_version is None or min_version is None:
                continue

            if compatibility[0] is None:
                compatibility = (max_version, min_version)
            else:
                compatibility = (max(max_version, compatibility[0], key=self.utils.parse_darwin_version),
                                 min(min_version, compatibility[1], key=self.utils.parse_darwin_version))

        return compatibility

    def _restrict_native_compatibility(self, compatibility):
        """
        Restrict the compatibility of the tool.

        Parameters
        ----------
        compatibility : tuple
            (Max, Min) of the compatibility.

        Returns
        -------
        tuple
            (Max, Min) of the compatibility.
        """
        if compatibility[0] is not None and compatibility[1] is not None:
            self.max_native_macos_version = min(self.max_native_macos_version, compatibility[0], key=self.utils.parse_darwin_version)
            self.min_native_macos_version = max(self.min_native_macos_version, compatibility[1], key=self.utils.parse_darwin_version)

    def show_macos_compatibility(self, device_compatibility):
        if isinstance(device_compatibility, tuple):
            max_version, min_version = device_compatibility

            if max_version == min_version:
                if max_version == self.max_native_macos_version:
                    return "\033[1;32m  " + min_version + "\033[0m"
                else:
                    return "\033[1;36m  " + min_version + "\033[0m"

            if max_version == self.max_native_macos_version:
                if min_version == self.min_native_macos_version:
                    return "\033[1;32m  " + min_version + " - " + max_version + "\033[0m"
                else:
                    return "\033[1;32m  " + self.min_native_macos_version + " - " + max_version + "\033[0m"

            if min_version == self.min_native_macos_version:
                return "\033[1;36m  " + min_version + " - " + self.max_native_macos_version + "\033[0m"

            return "\033[1;36m  " + min_version + " - " + max_version + "\033[0m"
        else:
            return "\033[1;31m  None\033[0m"

    def check_compatibility(self, hardware_report):
        """
        Perform the compatibility checks.

        Parameters
        ----------
        hardware_report : dict
            The dictionary containing the hardware report.
        """
        if "CPU" in hardware_report:
            self.check_cpu_compatibility()

        if "GPU" in hardware_report:
            self.check_gpu_compatibility(hardware_report)

        if "Sound" in hardware_report:
            self.check_sound_compatibility(hardware_report)

        if "Biometric" in hardware_report:
            self.check_biometric_compatibility(hardware_report)

        if "Network" in hardware_report:
            self.check_network_compatibility(hardware_report)

        if "Storage Controllers" in hardware_report:
            self.check_storage_controller_compatibility(hardware_report)

        if "Bluetooth" in hardware_report:
            self.check_bluetooth_compatibility(hardware_report)

        if "SD Controller" in hardware_report:
            self.check_sd_controller_compatibility(hardware_report)

        time.sleep(0.25)

    def check_cpu_compatibility(self):
        """
        Check the compatibility of the CPU.

        Returns
        -------
        bool
            True if the CPU is compatible.
        """
        if "SSE4" in self.hardware_report["CPU"]["Features"]:
            self.utils.head("CPU Compatibility")
            print("\033[1;32mYour CPU supports SSE4, which is required for macOS.\033[0m")
            return True

        self.utils.head("CPU Compatibility")
        print("\033[1;31mYour CPU does not support SSE4, which is required for macOS.\033[0m")
        print("")
        print("You cannot install macOS without a supported CPU.")
        self.utils.request_input()
        self.utils.exit_program()

    def check_gpu_compatibility(self):
        """
        Check the compatibility of the GPUs.

        Returns
        -------
        tuple
            (Max, Min) of the GPU compatibility.
        """
        self.utils.head("GPU Compatibility")

        print("Checking compatibility of GPUs:")

        for gpu_name, gpu_props in self.hardware_report["GPU"].items():
            gpu_compatibility = None

            device_id = gpu_props.get("Device ID", "").split("-")[-1]

            if device_id.startswith("0x"):
                device_id = device_id[2:]

            if gpu_props.get("Manufacturer") == "AMD" or gpu_props.get("Device Type") == "Integrated GPU":
                if gpu_props.get("Device Type") == "Integrated GPU":
                    gpu_compatibility = (self.max_native_macos_version, self.min_native_macos_version)
                elif "Navi 22" in gpu_props.get("Codename", ""):
                    gpu_compatibility = ("24.99.99", "24.0.0")
                elif gpu_props.get("Codename") in gpu_data.AMDCodenames:
                    gpu_compatibility = ("20.99.99", "17.0.0")
                else:
                    gpu_compatibility = (None, None)

            elif gpu_props.get("Manufacturer") == "NVIDIA":
                if nvidia_gsp_data.NullMoth.supported(gpu_props):
                    gpu_compatibility = nvidia_gsp_data.NullMoth.SEQUOIA
                elif "Kepler" in gpu_props.get("Codename", ""):
                    gpu_compatibility = ("20.99.99", "17.0.0")
                elif gpu_props.get("Codename") in ("Pascal", "Maxwell", "Fermi", "Tesla"):
                    gpu_compatibility = ("17.99.99", "17.0.0")
                else:
                    gpu_compatibility = (None, None)

            if gpu_props.get("Device Type") == "Integrated GPU" and gpu_props.get("Manufacturer") == "Intel":
                if gpu_props.get("Codename") in ("Iron Lake", "Sandy Bridge", "Ivy Bridge", "Haswell", "Broadwell", "Skylake"):
                    gpu_compatibility = ("20.99.99", "17.0.0")

            gpu_props["Compatibility"] = gpu_compatibility

            if gpu_props.get("Device Type") == "Integrated GPU" and gpu_compatibility == (None, None):
                gpu_props["Compatibility"] = (self.max_native_macos_version, self.min_native_macos_version)

            print("  - \033[1;33m{}\033[0m:".format(gpu_name))
            print("    Compatibility: {}".format(self.show_macos_compatibility(gpu_props["Compatibility"])))

            if gpu_props["Compatibility"] == (None, None):
                self.utils.head("GPU Compatibility")
                print("\033[1;31mYour GPU ({}) is not supported by macOS.\033[0m".format(gpu_name))
                print("")
                print("You cannot install macOS without a supported GPU.")
                self.utils.request_input()
                self.utils.exit_program()

            time.sleep(0.25)

        gpu_compatibility = self._widest_compatibility([gpu_props["Compatibility"] for gpu_props in self.hardware_report["GPU"].values()])

        for gpu_name, gpu_props in self.hardware_report["GPU"].items():
            for monitor_name, monitor_info in gpu_props.get("Monitor", {}).items():
                if monitor_info.get("Connector") == "Internal" and not monitor_info.get("Connected", True):
                    if gpu_props["Compatibility"] != (None, None):
                        print("  - \033[1;33m{}\033[0m: Internal monitor not connected, removing compatibility.".format(gpu_name))
                        gpu_props["Compatibility"] = (None, None)

        self._restrict_native_compatibility(gpu_compatibility)

        return gpu_compatibility

    def check_sound_compatibility(self, hardware_report):
        """
        Check the compatibility of the sound card.

        Parameters
        ----------
        hardware_report : dict
            The dictionary containing the hardware report.

        Returns
        -------
        bool
            True if the sound card is compatible.
        """
        self.utils.head("Sound Compatibility")

        audio_device = hardware_report.get("Sound", {})
        audio_codec = audio_device.get("Codec ID", "")

        if audio_codec:
            print("  - \033[1;33m{}\033[0m: \033[1;32mCompatible\033[0m".format(audio_device.get("Detected Audio Codec", "Unknown")))
            return True

        print("  - \033[1;33m{}\033[0m: \033[1;31mNo audio codec detected\033[0m".format(audio_device.get("Detected Audio Codec", "Unknown")))

        return False

    def check_biometric_compatibility(self, hardware_report):
        """
        Check the compatibility of the biometric devices.

        Parameters
        ----------
        hardware_report : dict
            The dictionary containing the hardware report.

        Returns
        -------
        bool
            True if the biometric devices are compatible.
        """
        self.utils.head("Biometric Compatibility")

        biometric_device = hardware_report.get("Biometric", {})
        fingerprint_reader = biometric_device.get("Reader", {})
        fingerprint_reader_id = fingerprint_reader.get("Device ID", "")

        if fingerprint_reader_id:
            print("  - \033[1;33m{}\033[0m: \033[1;32mCompatible\033[0m".format(fingerprint_reader.get("Detected Controller", "Unknown")))
            return True

        print("  - \033[1;33m{}\033[0m: \033[1;31mNo biometric reader detected\033[0m".format(fingerprint_reader.get("Detected Controller", "Unknown")))

        return False

    def check_network_compatibility(self, hardware_report):
        """
        Check the compatibility of the network devices.

        Parameters
        ----------
        hardware_report : dict
            The dictionary containing the hardware report.

        Returns
        -------
        bool
            True if the network device is compatible.
        """
        self.utils.head("Network Compatibility")

        max_native_macos_version = self.max_native_macos_version
        min_native_macos_version = self.min_native_macos_version

        for device_name, device_props in hardware_report.get("Network", {}).items():
            device_compatibility = (max_native_macos_version, min_native_macos_version)
            ocl_patched_max_version = os_data.get_latest_darwin_version(include_beta=False)
            ocl_patched_min_version = "20.0.0"

            device_id = device_props.get("Device ID", "").split("-")[-1]

            if device_id.startswith("0x"):
                device_id = device_id[2:]

            if device_props.get("Manufacturer") == "Broadcom":
                if device_id in self.BroadcomWiFiIDs:
                    print("  - \033[1;33m{}\033[0m: \033[1;32mCompatible\033[0m".format(device_name))

                    if device_id in self.BroadcomWiFiIDs:
                        print("    OCLP Compatibility: {}".format(self.show_macos_compatibility((ocl_patched_max_version, ocl_patched_min_version))))

                    device_props["Compatibility"] = (ocl_patched_max_version, ocl_patched_min_version)
                else:
                    print("  - \033[1;33m{}\033[0m: \033[1;33mUnverified\033[0m".format(device_name))
                    device_props["Compatibility"] = device_compatibility

            elif device_props.get("Manufacturer") == "Intel":
                if device_id in self.IntelWiFiIDs:
                    print("  - \033[1;33m{}\033[0m: \033[1;32mCompatible\033[0m".format(device_name))
                    device_props["Compatibility"] = device_compatibility
                else:
                    print("  - \033[1;33m{}\033[0m: \033[1;33mUnverified\033[0m".format(device_name))
                    device_props["Compatibility"] = device_compatibility

            elif device_props.get("Manufacturer") == "Atheros":
                if device_id in self.AtherosWiFiIDs:
                    print("  - \033[1;33m{}\033[0m: \033[1;32mCompatible\033[0m".format(device_name))
                    device_props["Compatibility"] = device_compatibility
                else:
                    print("  - \033[1;33m{}\033[0m: \033[1;33mUnverified\033[0m".format(device_name))
                    device_props["Compatibility"] = device_compatibility

            else:
                print("  - \033[1;33m{}\033[0m: \033[1;31mUnsupported\033[0m".format(device_name))
                device_props["Compatibility"] = (None, None)

            if device_props.get("Compatibility") == (None, None):
                self.utils.head("Network Compatibility")
                print("\033[1;31mYour network device ({}) is not supported by macOS.\033[0m".format(device_name))
                print("")
                print("You cannot install macOS without a supported network device.")
                self.utils.request_input()
                self.utils.exit_program()

            time.sleep(0.25)

    def check_storage_controller_compatibility(self, hardware_report):
        """
        Check the compatibility of the storage controllers.

        Parameters
        ----------
        hardware_report : dict
            The dictionary containing the hardware report.

        Returns
        -------
        bool
            True if the storage controllers are compatible.
        """
        self.utils.head("Storage Controller Compatibility")

        max_native_macos_version = self.max_native_macos_version
        min_native_macos_version = self.min_native_macos_version

        for device_name, device_props in hardware_report.get("Storage Controllers", {}).items():
            device_compatibility = (max_native_macos_version, min_native_macos_version)

            if device_props.get("Manufacturer") in ("AMD", "Intel"):
                print("  - \033[1;33m{}\033[0m: \033[1;32mCompatible\033[0m".format(device_name))
            else:
                print("  - \033[1;33m{}\033[0m: \033[1;33mUnverified\033[0m".format(device_name))

            device_props["Compatibility"] = device_compatibility

            time.sleep(0.25)

    def check_bluetooth_compatibility(self, hardware_report):
        """
        Check the compatibility of the Bluetooth devices.

        Parameters
        ----------
        hardware_report : dict
            The dictionary containing the hardware report.

        Returns
        -------
        bool
            True if the Bluetooth device is compatible.
        """
        self.utils.head("Bluetooth Compatibility")

        max_native_macos_version = self.max_native_macos_version
        min_native_macos_version = self.min_native_macos_version

        for device_name, device_props in hardware_report.get("Bluetooth", {}).items():
            device_compatibility = (max_native_macos_version, min_native_macos_version)

            if device_props.get("Manufacturer") == "Broadcom" or device_props.get("Manufacturer") == "Intel":
                print("  - \033[1;33m{}\033[0m: \033[1;32mCompatible\033[0m".format(device_name))
            else:
                print("  - \033[1;33m{}\033[0m: \033[1;33mUnverified\033[0m".format(device_name))

            device_props["Compatibility"] = device_compatibility

            time.sleep(0.25)

    def check_sd_controller_compatibility(self, hardware_report):
        """
        Check the compatibility of the SD controllers.

        Parameters
        ----------
        hardware_report : dict
            The dictionary containing the hardware report.

        Returns
        -------
        bool
            True if the SD controller is compatible.
        """
        self.utils.head("SD Controller Compatibility")

        max_native_macos_version = self.max_native_macos_version
        min_native_macos_version = self.min_native_macos_version

        for device_name, device_props in hardware_report.get("SD Controller", {}).items():
            device_compatibility = (max_native_macos_version, min_native_macos_version)

            if device_props.get("Manufacturer") in ("AMD", "Intel"):
                print("  - \033[1;33m{}\033[0m: \033[1;32mCompatible\033[0m".format(device_name))
            else:
                print("  - \033[1;33m{}\033[0m: \033[1;33mUnverified\033[0m".format(device_name))

            device_props["Compatibility"] = device_compatibility

            time.sleep(0.25)
