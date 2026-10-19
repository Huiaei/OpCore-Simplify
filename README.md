<br/>
<div align="center">
  <h3 align="center">OpCore Simplify</h3>

  <p align="center">
    A specialized tool that streamlines <a href="https://github.com/acidanthera/OpenCorePkg">OpenCore</a> EFI creation by automating the essential setup process and providing standardized configurations. Designed to reduce manual effort while ensuring accuracy in your Hackintosh journey.
    <br />
    <br />
    <a href="#-features">Features</a> •
    <a href="#-how-to-use">How To Use</a> •
    <a href="#-contributing">Contributing</a> •
    <a href="#-license">License</a> •
    <a href="#-credits">Credits</a> •
    <a href="#-contact">Contact</a>
  </p>
  
  <p align="center">
    <a href="https://trendshift.io/repositories/15410" target="_blank"><img src="https://trendshift.io/api/badge/repositories/15410" alt="lzhoang2801%2FOpCore-Simplify | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>
  </p>
</div>

> [!WARNING]
> While OpCore Simplify significantly reduces setup time, the Hackintosh journey still requires:
> - Understanding basic concepts from the [Dortania Guide](https://dortania.github.io/OpenCore-Install-Guide/)
> - Testing and troubleshooting during the installation process
> - Patience and persistence in resolving any issues that arise
>
> Our tool does not guarantee a successful installation in the first attempt, but it should help you get started.

## ✨ **Features**

1. **Comprehensive Hardware and macOS Support**  
   Fully supports modern hardware. Use `Compatibility Checker` to check supported/unsupported devices and macOS version supported.

   | **Component**  | **Supported**                                                                                       |
   |----------------|-----------------------------------------------------------------------------------------------------|
   | **CPU**        | Intel: Nehalem and Westmere (1st Gen) → Arrow Lake (15th Gen/Core Ultra Series 2) <br> AMD: Ryzen and Threadripper with [AMD Vanilla](https://github.com/AMD-OSX/AMD_Vanilla) |
   | **GPU**        | Intel iGPU: Iron Lake (1st Gen) → Ice Lake (10th Gen) <br> AMD APU: The entire Vega Raven ASIC family (Ryzen 1xxx → 5xxx, 7x30 series) <br> AMD dGPU: Navi 23, Navi 22, Navi 21 generations, and older series <br> NVIDIA: Kepler, Pascal, Maxwell, Fermi, Tesla generations <br> NVIDIA Turing and newer (GTX 16, RTX 20/30/40/50, TITAN RTX, Quadro RTX, Quadro T-series) on macOS 15 Sequoia via the [NullMoth NVIDIA driver](https://github.com/nullmoth/nvidia-macos-driver) |
   | **macOS**      | macOS High Sierra → macOS Tahoe |

2. **ACPI Patches and Kexts**  
   Automatically detects and adds ACPI patches and kexts based on hardware configuration.
   
   - Integrated with [SSDTTime](https://github.com/corpnewt/SSDTTime) for common patches (e.g., FakeEC, FixHPET, PLUG, RTCAWAC).
   - Includes custom patches:
      - Prevent kernel panics by directing the first CPU entry to an active CPU, disabling the UNC0 device, and creating a new RTC device for HEDT systems.
      - Disable unsupported or unused PCI devices, such as the GPU (using Optimus and Bumblebee methods or adding the disable-gpu property), Wi-Fi card, and NVMe storage controller.
      - Fix sleep state values in _PRW methods (GPRW, UPRW, HP special) to prevent immediate wake.
      - Add devices including ALS0, BUS0, MCHC, PMCR, PNLF, RMNE, IMEI, USBX, XOSI, along with a Surface Patch.
      - Enable ALSD and GPI0 devices.

3. **Automatic Updates**  
    Automatically checks for and updates OpenCorePkg and kexts from [Dortania Builds](https://dortania.github.io/builds/) and GitHub releases before each EFI build.
            
4. **EFI Configuration**  
   Apply additional customization based on both widely used sources and personal experience.

   - Spoof GPU IDs for certain AMD GPUs not recognized in macOS.
   - Use CpuTopologyRebuild kext for Intel CPUs with P-cores and E-cores to enhance performance.
   - Disable System Integrity Protection (SIP).
   - Spoof CPU IDs for Intel Pentium, Celeron, Xeon, and Core processors.
   - Add custom CPU names for AMD CPUs, as well as Intel Pentium, Celeron, Xeon, and Core lines from the Rocket Lake (11th) generation and newer.
   - Add a patch to allow booting macOS with unsupported SMBIOS.
   - Add NVRAM entries to bypass checking the internal Bluetooth controller.
   - Properly configure ResizeAppleGpuBars based on specific Resizable BAR information.
   - Allow flexible iGPU configuration between headless and driving a display when a supported discrete GPU is present.
   - Force Intel GPUs into VESA mode with HDMI and DVI connectors to simplify installation process.
   - Provide configuration required for using OpenCore Legacy Patcher.
   - Add built-in device property for network devices (fix 'Could not communicate with the server' when using iServices) and storage controllers (fix internal drives shown as external).
   - Prioritize SMBIOS optimized for both power management and performance.
   - Re-enable CPU power management on legacy Intel CPUs in macOS Ventura 13 and newer.
   - Apply WiFi profiles for itlwm kext to enable auto WiFi connections at boot time.

   and more...

5. **Easy Customization**  
   In addition to the default settings applied, users can easily make further customizations if desired.

   - Custom ACPI patches, and SMBIOS adjustments (**not recommended**).
   - Force load kexts on unsupported macOS versions.

## 🚀 **How To Use**

1. **Download OpCore Simplify**:
   - Click **Code** → **Download ZIP**, or download directly via this [link](https://github.com/lzhoang2801/OpCore-Simplify/archive/refs/heads/main.zip).  
   - Extract the downloaded ZIP file to your desired location.

   ![Download OpCore Simplify](https://i.imgur.com/mcE7OSX.png)

2. **Running OpCore Simplify**:
   - On **Windows**, run `OpCore-Simplify.bat`.
   - On **macOS**, run `OpCore-Simplify.command`.
   - On **Linux**, run `OpCore-Simplify.py` with existing Python interpreter.

   ![OpCore Simplify Menu](https://i.imgur.com/vTr1V9D.png)

3. **Selecting hardware report**:
   - On Windows, there will be an option for `E. Export hardware report`. It's recommended to use this for the best results with your hardware configuration and BIOS at the time of building.
   - Alternatively, use [**Hardware Sniffer**](https://github.com/lzhoang2801/Hardware-Sniffer) to create a `Report.json` and ACPI dump for configuration manully.

   ![Selecting hardware report](https://i.imgur.com/MbRmIGJ.png)

   ![Loading ACPI Tables](https://i.imgur.com/SbL6N6v.png)

   ![Compatibility Checker](https://i.imgur.com/kuDGMmp.png)

4. **Selecting macOS Version and Customizing OpenCore EFI**:
   - By default, the latest compatible macOS version will be selected for your hardware.
   - OpCore Simplify will automatically apply essential ACPI patches and kexts. 
   - You can manually review and customize these settings as needed.

   ![OpCore Simplify Menu](https://i.imgur.com/TSk9ejy.png)

5. **Building OpenCore EFI**:
   - Once you've customized all options, select **Build OpenCore EFI** to generate your EFI.
   - The tool will automatically download the necessary bootloader and kexts, which may take a few minutes.

   ![WiFi Profile Extractor](https://i.imgur.com/71TkJkD.png)

   ![Choosing Codec Layout ID](https://i.imgur.com/Mcm20EQ.png)

   ![Building OpenCore EFI](https://i.imgur.com/deyj5de.png)

6. **USB Mapping**:
   - After building your EFI, follow the steps for mapping USB ports.

   ![Results](https://i.imgur.com/MIPigPF.png)

7. **Create USB and Install macOS**: 
   - Use [**UnPlugged**](https://github.com/corpnewt/UnPlugged) on Windows to create a USB macOS installer, or follow [this guide](https://dortania.github.io/OpenCore-Install-Guide/installer-guide/mac-install.html) for macOS.
   - For troubleshooting, refer to the [OpenCore Troubleshooting Guide](https://dortania.github.io/OpenCore-Install-Guide/troubleshooting/troubleshooting.html).

> [!NOTE]
> 1. After a successful installation, if OpenCore Legacy Patcher is required, simply apply root patches to activate the missing features (such as modern Broadcom Wi-Fi card and graphics acceleration).
> 
> 2. For AMD GPUs, after applying root patches from OpenCore Legacy Patcher, you need to remove the boot argument `-radvesa`/`-amd_no_dgpu_accel` for graphics acceleration to work.
> 
> 3. For an NVIDIA Turing-or-newer card, see [NullMoth NVIDIA driver](#-nullmoth-nvidia-driver) below.

## 🟫 **NullMoth NVIDIA driver**

This fork adds support for NVIDIA Turing and newer cards (GTX 16, RTX 20/30/40/50, TITAN RTX, Quadro RTX and the Quadro T-series) on
**macOS 15 Sequoia** through the [NullMoth NVIDIA driver](https://github.com/nullmoth/nvidia-macos-driver) — NVIDIA's own open GPU kernel
modules (r610) with a Metal plugin, a framebuffer, an accelerator and an AGDC shim on top.

The supported card list comes from NVIDIA's `open-gpu-kernel-modules` 610.57.04 table, stored in
[`Scripts/datasets/nvidia_gsp_data.py`](Scripts/datasets/nvidia_gsp_data.py). Kepler, Maxwell and Pascal are **not** supported by the
driver and keep their original (OCLP) path.

When a supported card is found, OpCore Simplify writes the settings the driver needs into `config.plist`:

| Setting | Value | Why |
|---|---|---|
| `NVRAM → Add → 7C436110-… → boot-args` | `nvfb=1 nvaccel=1 nvfbheads=4 -nvkmsnosmooth amfi_get_out_of_my_way=0x1 amfi=0x80 ipc_control_port_options=0` | framebuffer + accelerator, 4 display heads; the AMFI arguments let WindowServer load the driver bundle |
| `NVRAM → Add → … → csr-active-config` | `<430A0000>` | the SIP value the driver was tested with (its kexts are not Apple-signed) |
| `Misc → Security → SecureBootModel` | `Disabled` | Apple Secure Boot refuses kexts Apple did not sign |
| `Kernel → Block` | `com.apple.iokit.IONDRVSupport`, `Exclude` | otherwise the firmware framebuffer takes display index 0 from NVRMFB |
| `Kernel → Add` | `Lilu.kext`, `AMFIPass.kext` | the driver's dependencies |
| `Booter → Quirks → ResizeAppleGpuBars` | `-1` | keep the firmware's BAR sizing; the driver sets the BAR up itself once macOS runs |
| `UEFI → Quirks → ResizeGpuBars` | `-1` | forced resizing can stop the firmware before the picker |

`nv_disable=1`, `-wegnoegpu` and `agdpmod=pikera` are removed for the card, and `gfxrst=4` is added when WhateverGreen is also present
(for an Intel or AMD GPU on the same machine). While the config is used to boot the **macOS installer** — which has no NVIDIA driver and
runs on the firmware framebuffer — the installer values are used instead: `ResizeAppleGpuBars = 0`, `ResizeGpuBars = -1`, and
`IONDRVSupport` is left unblocked.

On a laptop with both an NVIDIA and an Intel GPU, the NVIDIA card is woken from ACPI (`acpi-wake-type = 1`) so an Optimus machine does not
put it back to sleep before the driver claims it, and the *Before Using EFI* screen prints the mux note.

The driver's four kernel extensions (`NVRM`, `NVAccel`, `NVRMFB`, `NVRMAGDC`) are **not** injected from `EFI/OC/Kexts`: they install to
`/Library/Extensions` and load from the Auxiliary Kernel Collection. OpenCore only has to set SIP and the boot arguments.

After installing macOS with the built EFI, install the driver on the installed system:

```bash
tar -xzf nullmoth-nvidia-*.tar.gz && cd pkgroot
shasum -a 256 -c SHA256SUMS
sudo ./install.sh
```

BIOS requirements: **Above 4G Decoding ON**, **CSM OFF**. Verify after the restart:

```bash
kmutil showloaded --list-only | grep nullmoth   # 4 lines
system_profiler SPDisplaysDataType | head -20   # your card, Metal: supported
```

The [1401](https://github.com/nullmoth/1401) app (Windows and macOS) automates the driver install and its boot-picker entry
(*1401: Remove NVIDIA driver*); this fork's job is only to produce the OpenCore side of that setup.

## 🤝 **Contributing**

Contributions are **highly appreciated**! If you have ideas to improve this project, feel free to fork the repo and create a pull request, or open an issue with the "enhancement" tag.

Don't forget to ⭐ star the project! Thank you for your support! 🌟

## 📜 **License**

Distributed under the BSD 3-Clause License. See `LICENSE` for more information.

## 🙌 **Credits**

- [OpenCorePkg](https://github.com/acidanthera/OpenCorePkg) and [kexts](https://github.com/lzhoang2801/OpCore-Simplify/blob/main/Scripts/datasets/kext_data.py) – The backbone of this project.
- [SSDTTime](https://github.com/corpnewt/SSDTTime) – SSDT patching utilities.

## 📞 **Contact**

**Hoang Hong Quan**
> Facebook [@macforce2601](https://facebook.com/macforce2601) &nbsp;&middot;&nbsp;
> Telegram [@lzhoang2601](https://t.me/lzhoang2601) &nbsp;&middot;&nbsp;
> Email: lzhoang2601@gmail.com

## 🌟 **Star History**

[![Star History Chart](https://star-history.dera.page/svg?repos=lzhoang2801/OpCore-Simplify&type=Date)](https://star-history.dera.page/#lzhoang2801/OpCore-Simplify&Date)
