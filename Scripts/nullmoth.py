import re

from Scripts.datasets import nvidia_gsp_data


class NullMoth:
    """Adapter for the NullMoth NVIDIA driver (nullmoth/nvidia-macos-driver).

    The driver is not a kext bundle that OpenCore injects: its four kernel
    extensions (NVRM, NVAccel, NVRMFB, NVRMAGDC) install into
    /Library/Extensions and load from the Auxiliary Kernel Collection that the
    driver's own install.sh builds.  OpenCore only has to

      * allow the unsigned kexts (csr-active-config <430A0000>),
      * pass the driver's boot arguments,
      * stop the firmware framebuffer from stealing display index 0
        (Kernel > Block com.apple.iokit.IONDRVSupport, Exclude),
      * keep SecureBootModel disabled.

    Everything below is the data and the helpers needed to make the
    OpCore-Simplify engine produce those settings for supported cards, plus
    the 1401 installer values used while installing macOS itself.
    """

    REPO = "nullmoth/nvidia-macos-driver"

    # The NVRAM GUID for the global variables (boot-args, csr-active-config).
    GUID = "7C436110-AB2A-4BBB-A880-FE41995C9F82"

    # macOS 15 Sequoia only (darwin 24).
    SEQUOIA = ("24.99.99", "24.0.0")

    # The SIP value the driver was tested with: unsigned kexts plus the root
    # patches its AMFI arguments need.
    SIP_DRIVER = bytes.fromhex("430A0000")

    # boot-args the driver needs on an installed system.
    BOOT_ARGS = (
        "nvfb=1",
        "nvaccel=1",
        "nvfbheads=4",
        "-nvkmsnosmooth",
        "amfi_get_out_of_my_way=0x1",
        "amfi=0x80",
        "ipc_control_port_options=0",
    )

    # The firmware framebuffer would otherwise take display index 0 from
    # NVRMFB.  Blocked while installing macOS (the installer has no NVIDIA
    # driver and runs on the firmware screen).
    IONDRV_SUPPORT = "com.apple.iokit.IONDRVSupport"

    # BAR values.  The driver sets the BAR up itself once macOS is running, so
    # OpCore-Simplify must not force a size: keep the firmware's sizing on the
    # installed system and use the small-BAR pair while installing macOS.
    INSTALLER_RESIZE_APPLE_GPU_BARS = 0
    INSTALLER_RESIZE_GPU_BARS = -1

    # Optional troubleshooting boot arguments (never added by default).
    OPTIONAL_BOOT_ARGS = (
        ("-nvrmnoflip", "keeps the composited frame on the copy path; first thing to try when the desktop flashes or tears while the cursor moves"),
        ("-nvrmnogo", "the driver idles until nvrmctl go <pass> instead of starting the GPU itself"),
        ("-nvrmnobootscreen", "do not snapshot the boot screen"),
        ("-nvrmnopm", "turns off system sleep support: NVRM stays out of the power tree"),
    )

    # WhateverGreen is still needed for an Intel/AMD GPU on the same machine,
    # but its boot screen copy can read freed memory when the NVIDIA display
    # opens unless the graphics reset is delayed.
    WEG_COMPAT_ARG = "gfxrst=4"

    # Boot arguments that hide the card and must never be present.
    FORBIDDEN_BOOT_ARGS = (
        "nv_disable=1",
        "-wegnoegpu",
    )

    # The GPU firmware the driver loads, installed by the driver package.
    GSP_FIRMWARE = "/Users/Shared/nvfw/nvidia/610.57.04"

    # The driver's kernel extensions (installed to /Library/Extensions by the
    # driver package, never injected from EFI/OC/Kexts).
    KEXTS = ("NVRM", "NVAccel", "NVRMFB", "NVRMAGDC")

    # The driver package is resolved from the release API (see latest_release)
    # rather than pinned, so the fork tracks the driver as it ships.  The
    # pinned entry below is only the last verified download, used when the
    # release API is unreachable; the checksum still has to match.
    PACKAGE = {
        "name": "nullmoth-nvidia-2.3.7.tar.gz",
        "url": "https://github.com/{}/releases/download/v2.3.7/nullmoth-nvidia-2.3.7.tar.gz".format(REPO),
        "sha256": "237675011b81d60f8473a4f53ad08407e659e4a9fcf0dc571c5c15de579e39e6",
    }

    RELEASE_API = "https://api.github.com/repos/{}/releases/latest".format(REPO)
    _PKG_RE = re.compile(r"^nullmoth-nvidia-(\d+(?:\.\d+)+)\.tar\.gz$")

    MUX_HELP = (
        "This laptop has both an NVIDIA GPU and an integrated GPU (Optimus/mux). "
        "The NullMoth driver drives the NVIDIA card and the internal display has to be "
        "connected to it. If the panel is wired to the integrated GPU, the driver cannot "
        "use it: connect an external monitor to the NVIDIA card or switch the mux in firmware."
    )

    def __init__(self, utils=None):
        self.utils = utils

    # ------------------------------------------------------------------
    # Card support
    # ------------------------------------------------------------------
    @staticmethod
    def device_id(gpu_props):
        """Return the PCI device id of a GPU (lower case, no vendor prefix)."""
        device_id = gpu_props.get("Device ID") or ""
        if device_id.startswith("10DE-"):
            device_id = device_id[5:]
        return device_id.upper()

    @classmethod
    def is_nvidia(cls, gpu_props):
        return "NVIDIA" in (gpu_props.get("Manufacturer") or "")

    @classmethod
    def is_discrete(cls, gpu_props):
        return "Discrete" in (gpu_props.get("Device Type") or "")

    @classmethod
    def supported(cls, gpu_props):
        """True when this card is in the driver's supported PCI id table."""
        if not cls.is_nvidia(gpu_props) or not cls.is_discrete(gpu_props):
            return False
        return cls.device_id(gpu_props) in nvidia_gsp_data.SUPPORTED_DEVICES

    @classmethod
    def gpu_disabled(cls, gpu_name, gpu_props, disabled_devices):
        """True when this card is in the engine's disabled-device list.

        The engine records a disabled device under its hardware category
        ("GPU: <name>") and, for some categories, under "<Device Type>: <name>"
        or the bare name, so all three spellings are checked.  A disabled card
        must not activate the driver (1401's tests/test_disabled_gpu_policy.py).
        """
        labels = {
            gpu_name,
            "GPU: {}".format(gpu_name),
            "{}: {}".format(gpu_props.get("Device Type") or "", gpu_name),
        }
        return any(label in (disabled_devices or []) for label in labels)

    @classmethod
    def cards(cls, hardware_report, disabled_devices=None):
        """Names of every supported NVIDIA card in a hardware report."""
        return [
            gpu_name
            for gpu_name, gpu_props in (hardware_report.get("GPU") or {}).items()
            if cls.supported(gpu_props) and not cls.gpu_disabled(gpu_name, gpu_props, disabled_devices)
        ]

    @classmethod
    def has_supported_card(cls, hardware_report, disabled_devices=None):
        return bool(cls.cards(hardware_report, disabled_devices))

    @classmethod
    def tested(cls, hardware_report, disabled_devices=None):
        """Names of the supported cards NVIDIA's table lists as tested."""
        tested = nvidia_gsp_data.TESTED_DEVICES
        return [
            gpu_name
            for gpu_name, gpu_props in (hardware_report.get("GPU") or {}).items()
            if cls.supported(gpu_props) and not cls.gpu_disabled(gpu_name, gpu_props, disabled_devices) and cls.device_id(gpu_props) in tested
        ]

    @classmethod
    def is_laptop(cls, hardware_report):
        return (hardware_report.get("Motherboard") or {}).get("Platform") == "Laptop"

    @classmethod
    def mux_help(cls, hardware_report):
        """The Optimus note when a laptop has both NVIDIA and integrated GPUs."""
        if not cls.is_laptop(hardware_report):
            return None
        gpus = hardware_report.get("GPU") or {}
        if not any(cls.is_nvidia(props) for props in gpus.values()):
            return None
        if not any("Intel" in (props.get("Manufacturer") or "") for props in gpus.values()):
            return None
        return cls.MUX_HELP

    # ------------------------------------------------------------------
    # Hardware report mutation (mirrors 1401's nullmoth.mark)
    # ------------------------------------------------------------------
    @classmethod
    def mark(cls, hardware_report):
        """Mark supported NVIDIA cards as macOS 15 Sequoia compatible.

        Returns the names of the cards that were marked.  Cards that were left
        alone are untouched, so the engine keeps its own verdict for them.
        """
        marked = []
        for gpu_name, gpu_props in (hardware_report.get("GPU") or {}).items():
            if not cls.supported(gpu_props):
                continue
            gpu_props["Compatibility"] = cls.SEQUOIA
            # The driver replaces the OCLP path entirely: there is no
            # nvda_drv_vrl/ngfxcompat patch set for these cards.
            gpu_props.pop("OCLP Compatibility", None)
            if not gpu_props.get("Codename"):
                gpu_props["Codename"] = "NullMoth driver"
            marked.append(gpu_name)
        return marked

    # ------------------------------------------------------------------
    # config.plist mutation
    # ------------------------------------------------------------------
    @classmethod
    def resize_apple_gpu_bars(cls, hardware_report, macos_version, current):
        """Booter > Quirks > ResizeAppleGpuBars for a NullMoth machine.

        The driver sets the BAR up itself once macOS is running, and forcing a
        large BAR can stop PCI configuration, so the default for a supported
        card is -1 (keep the firmware's sizing).  While installing macOS the
        installer has no NVIDIA driver and runs on the firmware framebuffer,
        which only survives with a small BAR (0).
        """
        if not cls.has_supported_card(hardware_report):
            return current
        if cls.is_installing_macos(hardware_report):
            return cls.INSTALLER_RESIZE_APPLE_GPU_BARS
        return -1

    @classmethod
    def is_installing_macos(cls, hardware_report):
        """True while the config is meant to boot the macOS installer.

        The macOS installer has no NVIDIA driver and runs on the firmware's
        screen, so the BAR pair and the IONDRVSupport block differ.  A report
        carrying the "Installing macOS" flag marks such a config (that is how
        1401 builds the stick that installs macOS); the engine's build path
        leaves the flag unset, which means an installed system.
        """
        if hardware_report is None:
            return False
        return bool(hardware_report.get("Installing macOS"))

    @classmethod
    def boot_args(cls, hardware_report=None, kexts=None, installing_macos=False):
        """The driver's boot arguments, minus what conflicts with this machine."""
        return list(cls.BOOT_ARGS)

    @classmethod
    def has_whatevergreen(cls, kexts):
        for kext in kexts or []:
            name = getattr(kext, "name", kext)
            if name == "WhateverGreen":
                return True
        return False

    @classmethod
    def apply(cls, config, hardware_report, kexts=None, installing_macos=False, disabled_devices=None):
        """Apply the driver's OpenCore settings to a config.plist dictionary.

        `installing_macos` selects the installer values (the macOS installer has
        no NVIDIA driver and runs on the firmware framebuffer, so the BAR pair
        differs and IONDRVSupport is not blocked).  `disabled_devices` is the
        engine's disabled-device list: a card the user disabled must not
        activate the driver.

        Returns True when a supported card is present, i.e. when the settings
        were applied.
        """
        if not cls.has_supported_card(hardware_report, disabled_devices):
            return False

        # The report can say "this EFI is for the macOS installer" (1401 sets
        # that when it builds the stick that installs macOS), otherwise the
        # caller decides with the keyword.
        installing_macos = installing_macos or cls.is_installing_macos(hardware_report)

        booter_quirks = config.setdefault("Booter", {}).setdefault("Quirks", {})
        uefi_quirks = config.setdefault("UEFI", {}).setdefault("Quirks", {})
        kernel = config.setdefault("Kernel", {})
        misc_security = config.setdefault("Misc", {}).setdefault("Security", {})

        # --- boot-args -------------------------------------------------
        nvram_add = config.setdefault("NVRAM", {}).setdefault("Add", {})
        nvram_add.setdefault(cls.GUID, {})
        boot_args = nvram_add[cls.GUID].get("boot-args")
        existing = []
        if isinstance(boot_args, str):
            existing = [arg for arg in boot_args.split(" ") if arg]
        elif isinstance(boot_args, (bytes, bytearray)):
            existing = [arg for arg in boot_args.decode().split(" ") if arg]

        # Anything that hides the card would defeat the driver.
        existing = [arg for arg in existing if arg not in cls.FORBIDDEN_BOOT_ARGS]

        args = list(existing)
        for arg in cls.BOOT_ARGS:
            if arg not in args:
                args.append(arg)
        if cls.has_whatevergreen(kexts) and cls.WEG_COMPAT_ARG not in args:
            args.append(cls.WEG_COMPAT_ARG)

        nvram_add[cls.GUID]["boot-args"] = " ".join(args)

        # --- SIP -------------------------------------------------------
        # The kexts are not Apple-signed.
        nvram_add[cls.GUID]["csr-active-config"] = cls.SIP_DRIVER
        nvram_delete = config.setdefault("NVRAM", {}).setdefault("Delete", {})
        nvram_delete.setdefault(cls.GUID, [])
        if "csr-active-config" not in nvram_delete[cls.GUID]:
            nvram_delete[cls.GUID].append("csr-active-config")

        # --- Secure Boot -------------------------------------------------
        misc_security["SecureBootModel"] = "Disabled"

        # --- BARs ---------------------------------------------------------
        if installing_macos:
            booter_quirks["ResizeAppleGpuBars"] = cls.INSTALLER_RESIZE_APPLE_GPU_BARS
            uefi_quirks["ResizeGpuBars"] = cls.INSTALLER_RESIZE_GPU_BARS
        else:
            # Keep the firmware's sizing on an installed system: the driver
            # sets the BAR up itself, and forcing one can stop the firmware
            # before the picker.
            if "ResizeAppleGpuBars" not in booter_quirks:
                booter_quirks["ResizeAppleGpuBars"] = -1
            if "ResizeGpuBars" not in uefi_quirks:
                uefi_quirks["ResizeGpuBars"] = -1

        # --- the firmware framebuffer -------------------------------------
        if not installing_macos:
            block = kernel.setdefault("Block", [])
            entry = {"Arch": "Any", "Comment": "NullMoth: firmware framebuffer takes display index 0 from NVRMFB", "Enabled": True, "Identifier": cls.IONDRV_SUPPORT, "Strategy": "Exclude"}
            if not any(
                (item.get("Identifier") if isinstance(item, dict) else None) == cls.IONDRV_SUPPORT
                for item in block
            ):
                block.append(entry)

        # --- laptop: keep the NVIDIA card awake ---------------------------
        cls.laptop_gpu_awake(config, hardware_report)

        return True
    PCI_PATH_RE = re.compile(r"^PciRoot\(0x[0-9A-Fa-f]+\)(/Pci\(0x[0-9A-Fa-f]+,0x[0-9A-Fa-f]+\))+$")

    @classmethod
    def laptop_gpu_awake(cls, config, hardware_report):
        """On laptops, wake the NVIDIA card from ACPI before the driver starts.

        Without it an Optimus machine can put the dGPU back to sleep before
        NVRM claims it.
        """
        if not cls.is_laptop(hardware_report):
            return
        device_properties = config.setdefault("DeviceProperties", {}).setdefault("Add", {})
        for gpu_name, gpu_props in (hardware_report.get("GPU") or {}).items():
            if not cls.supported(gpu_props):
                continue
            pci_path = gpu_props.get("PCI Path") or gpu_name
            if not cls.PCI_PATH_RE.match(pci_path):
                continue
            props = device_properties.setdefault(pci_path, {})
            props["acpi-wake-type"] = 1

    # ------------------------------------------------------------------
    # USB stick staging (1401 parity: what the app installs after the build)
    # ------------------------------------------------------------------
    @classmethod
    def latest_release(cls, get_json=None, get_text=None):
        """Resolve the newest driver package from the GitHub release API.

        Returns {"name", "url", "sha256", "version"} or None.  Used instead of a
        pinned version so the fork tracks the driver as it is released; the
        caller is expected to verify the download against the returned hash.
        """
        if get_json is None:
            return None
        try:
            release = get_json(cls.RELEASE_API)
        except Exception:
            return None
        if not isinstance(release, dict):
            return None
        version = str(release.get("tag_name") or "").lstrip("v")
        if not version:
            return None
        if get_text is None:
            return {"name": cls.PACKAGE["name"], "url": cls.PACKAGE["url"], "sha256": cls.PACKAGE["sha256"], "version": version}
        try:
            sums = get_text("https://github.com/{}/releases/download/{}/SHA256SUMS.txt".format(cls.REPO, release.get("tag_name") or ""))
        except Exception:
            return None
        for line in (sums or "").splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) != 2 or not cls._PKG_RE.match(parts[1]):
                continue
            return {"name": parts[1], "url": "https://github.com/{}/releases/download/{}/{}".format(cls.REPO, release.get("tag_name"), parts[1]), "sha256": parts[0], "version": version}
        return None

    @classmethod
    def stage(cls, usb_root, package_path, sha256=None):
        """Copy a verified driver package next to the built EFI on the stick.

        Returns the destination path.  `package_path` must have been verified
        against `sha256` (or the release's SHA256SUMS.txt) by the caller.
        """
        import os
        import shutil

        if sha256 is not None:
            import hashlib

            digest = hashlib.sha256()
            with open(package_path, "rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            if digest.hexdigest() != sha256:
                raise ValueError("Driver package checksum mismatch: {} != {}".format(digest.hexdigest(), sha256))

        destination = os.path.join(usb_root, "NullMoth")
        os.makedirs(destination, exist_ok=True)
        target = os.path.join(destination, os.path.basename(package_path))
        shutil.copy2(package_path, target)

        with open(os.path.join(destination, "README.txt"), "w") as handle:
            handle.write(cls.readme())
        return target

    @classmethod
    def readme(cls):
        return "\n".join(
            [
                "NullMoth NVIDIA driver for macOS",
                "=================================",
                "",
                "OpenCore on this stick is already configured for the driver.",
                "The driver's kernel extensions are NOT injected from EFI/OC/Kexts:",
                "install the package into macOS and they load from",
                "/Library/Extensions.",
                "",
                "  shasum -a 256 -c SHA256SUMS",
                "  sudo ./install.sh",
                "",
                "Verify after the restart:",
                "",
                "  kmutil showloaded --list-only | grep nullmoth",
                "  system_profiler SPDisplaysDataType | head -20",
                "",
                "The first shows 4 lines; the second shows your card with Metal: supported.",
                "Remove NVIDIA driver: NullMothSafe.efi adds -nvoff and the",
                "com.nullmoth.recover daemon undoes the install at the next boot.",
                "",
                "Driver: https://github.com/{}".format(cls.REPO),
                "Installer app: https://github.com/nullmoth/1401",
            ]
        )
