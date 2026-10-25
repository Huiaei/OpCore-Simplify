<br/>
<div align="center">
  <h3 align="center">OpCore Simplify</h3>

  <p align="center">
    一个专用工具：通过自动化关键配置流程、提供标准化配置，简化 <a href="https://github.com/acidanthera/OpenCorePkg">OpenCore</a> EFI 的创建过程。目标是减少手工操作，同时保证黑苹果（Hackintosh）配置的准确性。
    <br />
    <br />
    <a href="#ai-notice">AI 生成声明</a> •
    <b>简体中文</b> • <a href="README.md">English</a>
    <br />
    <br />
    <a href="#this-branch">本分支说明</a> •
    <a href="#features">功能特性</a> •
    <a href="#how-to-use">使用方法</a> •
    <a href="#nullmoth">NullMoth 驱动</a> •
    <a href="#intel-igpu">Intel 核显</a> •
    <a href="#contributing">参与贡献</a> •
    <a href="#license">许可</a> •
    <a href="#credits">致谢</a> •
    <a href="#contact">联系</a>
  </p>
</div>

<a id="ai-notice"></a>

> [!CAUTION]
> **本文档与 `fork-local-fixes` 分支上的改动由 AI 生成，请先读完再使用。**
>
> 该分支的提交与本文档中描述该分支的章节，均由 AI 代理（DSH）在人工指示下编写；上游项目本身与 `main` 镜像仍是人工编写的代码。
>
> AI 侧的验证范围：`unittest` 测试套件、`config.plist` 端到端生成、以及在虚拟机里跑通一次完整的 EFI 构建。**没有在真实硬件上开机验证过**。因此请把这里的一切当作“待评审的提案”：
>
> - 用 `git diff main..fork-local-fixes` 逐行看清改了什么；
> - 不认识的项目先查 [Dortania 指南](https://dortania.github.io/OpenCore-Install-Guide/)；
> - 动自己的机器之前，先留一份能开机的 EFI 或备份。
>
> 不提供任何担保，详见下方许可条款。

> [!WARNING]
> OpCore Simplify 能显著缩短配置时间，但黑苹果依然需要：
> - 理解 [Dortania 指南](https://dortania.github.io/OpenCore-Install-Guide/) 中的基本概念
> - 在安装过程中不断测试与排查
> - 解决突发问题时的耐心与坚持
>
> 本工具不保证一次安装成功，它的作用是让你有一个正确的起点。

<a id="this-branch"></a>

## 🌿 **本分支说明**

这是 `fork-local-fixes` 分支：它等于 `main` 加上一组本地改动，下文所有内容都只存在于这个分支上。`main` 保持为上游项目的镜像，因此两者不会悄悄分叉：`git diff main..fork-local-fixes` 就是全部差异。

工具的使用流程没有任何变化——同样的交互提示、同样的 EFI 目录结构、同样的 OpenCore 约定。变化在于：它认识的硬件更多、在 GitHub 很慢或不可达的网络下能活下来、以及一批原本会让构建以报错收场的问题被修掉了。

> 英文版见 [README.md](README.md)，其中 [This branch](README.md#-this-branch) 一节与本篇一一对应。

### 本分支增加了什么

**1. 通过 NullMoth 驱动支持 NVIDIA 显卡（Turing 及更新）**

macOS 15 删掉了最后一批 NVIDIA 驱动，NullMoth 的社区驱动把 Turing、Ampere、Ada、Blackwell 重新带了回来。该驱动**不是** EFI kext——它安装到 `/Library/Extensions`、由 Auxiliary Kernel Collection 加载——所以一份“标准”的 OpenCore 配置反而会挡它的路。本分支把驱动的规则教给了工具：

- 按 PCI device id（采用 open-gpu-kernel-modules 公布的列表）识别受支持的卡，并且只向它提供 macOS 15 Sequoia。
- 写入驱动所需的启动参数、SIP 值、`SecureBootModel`、内存映射相关 quirk 以及 `IONDRVSupport` 排除规则；**绝不**把驱动 kext 塞进 `EFI/OC/Kexts`。
- 当显卡位于 Optimus 路径之后时补上笔记本唤醒属性；发现不止一张受支持的卡时给出警告（驱动只能接管一张）。
- 驱动包从最新 release 动态解析，同时保留一个固定版本的兜底，离线跑也能用。
- 构建结束时输出一段“使用此 EFI 之前”的说明，讲清驱动怎么装；并附带 `Scripts/nullmoth_selftest.py`，无硬件也能复查这些规则。
- 这类卡被报告为“支持”，但**不**显示 `OCLP Compatibility` 行——对这些显卡驱动是**替代** OCLP，而不是让 OCLP 去打补丁。

**2. Realtek 无线网卡（AirPort Family、RTW88 与老 HS80211 栈）**

RTL8852BE 这类卡现在可以选了，按 macOS 版本给出正确的 kext 组合，并处理了 Monterey 的例外。这部分来自上游的 PR，这里修掉了它的三个缺陷：它依赖了一个并不存在的 kext、它的资源文件名与后来发布的 release 不再匹配、以及同一个 bundle 被塞进 `EFI/OC/Kexts` 两次。

**3. 在糟糕的网络下活下来**

每个下载现在都有第二、第三、第四个来源，断掉的传输会续传而不是从头再来：

- github.com、`raw.githubusercontent.com`、`api.github.com` 都会回落到公共镜像，GitHub 被墙或被限速不再等于构建失败。
- 传输从磁盘上已有的字节续传，读超时 30 秒，读阻塞时重试而不是直接中止。
- 解压前先校验下载到的是真正的 zip，不是就重新下载——过去 14.4 MB 里的 12.1 MB 半截文件会被当成成功（该 release 不发布校验和），直到后面才以 “File is not a zip file” 报错。

**4. 控制台、日志与无界面运行**

- 在非 UTF-8 控制台（中文 Windows、cp437 终端）上，项目符号、对勾与进度条会降级为纯 ASCII，而不是抛 `UnicodeEncodeError` 然后只留一个空错误框结束。
- 崩溃处理器在打印 traceback 时不会再二次崩溃——正是这一点让那些运行只留下 “An Error Occurred”。
- 每次运行都在仓库旁写日志：`logs/OpCore-Simplify-<时间戳>.log`（去掉 ANSI 颜色），退出时另存 `logs/latest.log`。不需要再用 shell 重定向——PowerShell 的 `| tee` 写的是 UTF-16，而且丢 stderr。
- 管道输入或无界面会话会干净退出，不再出现 `EOFError` traceback；没有桌面会话时也不会去打开结果目录。
- Linux 下直接复制 ACPI 表，不再经过 `sudo`。
- 如果 Windows 硬件嗅探器无法导出 ACPI 表（退出码 5，开启 Secure Boot 或内存完整性时常见），改由 Windows 固件表 API 读取，构建继续。

**5. 正确性修复**

- 编译失败的 SSDT 不再把它留下的 `.dsl` 丢在结果里，配置里也不会再引用它，OpenCore 因此不会报找不到文件。
- Comet Lake 平台（NUC10 之类）在 macOS 15 上会得到 `Cpuid1Data`/`Cpuid1Mask`，此前会卡在 `EXITBS:START`。
- Intel Skylake / Kaby Lake 核显在 macOS 14 及以上会自动加入 `AMFIPass` 与 `RestrictEvents`（缺了它们系统会在 `endpointsecurityd` 崩溃），同时仍走纯 device-id 伪装，而不进入 OCLP 打补丁流程；并提示什么情况下还需要自定义显示接口映射。
- Intel PRO/1000 PT（`8086:105E`）被报告为支持到 macOS 12 为止，与 Apple 自带驱动真正覆盖的范围一致。
- 不以 `_SB` 为根的 ACPI 路径（`_TZ_` 下的温度/风扇设备等）重新可以通过校验。

**6. 合并进来的上游 PR**

合入了六个 PR 和第七个的一部分（它们修的确实是真问题，且与上面的工作不冲突）：Windows SSL 需要的 `certifi` 依赖、commits 载荷嵌套的兼容（此前自更新读不到最新提交）、接受非 `_SB` 根路径的 ACPI 校验、在老 Python 上也能用的目录合并助手、ASCII 进度条、以及 Realtek 无线支持。补丁与分支上下文不匹配时按原意手工改写而非丢弃；两个 PR 改同一行时保留覆盖面更广的那个。

**7. 测试**

`Tests/` 与 `tests/` 下是不依赖网络与硬件的 `unittest` 套件，覆盖驱动规则、下载与镜像逻辑、控制台降级、ACPI 兜底以及合入的 PR。`Scripts/nullmoth_selftest.py` 直接校验驱动规则。GitHub Actions 工作流会在 Windows 与 Linux 上跑这些套件。

### 分支备注

- 分支：`fork-local-fixes`，基于 `main` 中镜像的上游版本。
- 本仓库的 `main` 保持为干净的镜像，因此 `git diff main..fork-local-fixes` 精确等于这一组改动。
- 上游仍是原作者的项目——本分支是本地集成，不是替代品。

<a id="features"></a>

## ✨ **功能特性**

1. **广泛的硬件与 macOS 支持**
   完整支持现代硬件。用 `Compatibility Checker` 检查哪些设备受支持/不受支持，以及支持哪些 macOS 版本。

   | **部件** | **支持范围** |
   |----------|--------------|
   | **CPU** | Intel：Nehalem 与 Westmere（第 1 代）→ Arrow Lake（第 15 代 / Core Ultra 系列 2）<br>AMD：Ryzen 与 Threadripper，配合 [AMD Vanilla](https://github.com/AMD-OSX/AMD_Vanilla) |
   | **GPU** | Intel 核显：Iron Lake（第 1 代）→ Ice Lake（第 10 代）<br>AMD APU：Vega Raven 全系（Ryzen 1xxx → 5xxx、7x30 系列）<br>AMD 独显：Navi 23、Navi 22、Navi 21 各代及更早系列<br>NVIDIA：Kepler、Pascal、Maxwell、Fermi、Tesla 各代<br>NVIDIA Turing 及更新（GTX 16、RTX 20/30/40/50、TITAN RTX、Quadro RTX、Quadro T 系列）在 macOS 15 Sequoia 上通过 [NullMoth NVIDIA 驱动](https://github.com/nullmoth/nvidia-macos-driver) 支持 |
   | **macOS** | macOS High Sierra → macOS Tahoe |

2. **ACPI 补丁与 kext**
   根据硬件配置自动检测并添加 ACPI 补丁与 kext。

   - 集成了 [SSDTTime](https://github.com/corpnewt/SSDTTime)，用于常见补丁（如 FakeEC、FixHPET、PLUG、RTCAWAC）。
   - 内置自定义补丁：
     - 把第一个 CPU 条目指向活跃 CPU、禁用 UNC0 设备、为 HEDT 平台创建新的 RTC 设备，以避免内核崩溃。
     - 禁用不受支持或未使用的 PCI 设备，例如显卡（Optimus/Bumblebee 方式或添加 disable-gpu 属性）、无线网卡、NVMe 控制器。
     - 修正 `_PRW` 方法中的休眠状态值（GPRW、UPRW、HP 专用），避免立即被唤醒。
     - 添加 ALS0、BUS0、MCHC、PMCR、PNLF、RMNE、IMEI、USBX、XOSI 等设备，以及 Surface Patch。
     - 启用 ALSD 与 GPI0 设备。

3. **自动更新**
   每次构建 EFI 之前，自动从 [Dortania Builds](https://dortania.github.io/builds/) 与 GitHub releases 检查并更新 OpenCorePkg 与 kext。

4. **EFI 配置**
   基于广泛使用的资料与个人经验做进一步定制。

   - 为某些在 macOS 中不被识别的 AMD 显卡伪装 GPU ID。
   - 对带 P-core / E-core 的 Intel CPU 使用 CpuTopologyRebuild kext 提升性能。
   - 关闭系统完整性保护（SIP）。
   - 为 Intel Pentium、Celeron、Core、Xeon 处理器伪装 CPU ID。
   - 为 AMD CPU 以及 Rocket Lake（第 11 代）及更新的 Intel Pentium、Celeron、Xeon、Core 添加自定义 CPU 名称。
   - 添加补丁，使不受支持的 SMBIOS 也能启动 macOS。
   - 添加 NVRAM 条目以跳过内置蓝牙控制器检查。
   - 依据实际的 Resizable BAR 信息正确配置 ResizeAppleGpuBars。
   - 在存在受支持独显时，让核显可在“无头”（headless）与“驱动显示器”之间灵活配置。
   - 对 HDMI 与 DVI 接口上的 Intel 显卡强制 VESA 模式，简化安装过程。
   - 提供使用 OpenCore Legacy Patcher 所需的配置。
   - 为网络设备（修复使用 iServices 时的 “Could not communicate with the server”）与存储控制器（修复内置硬盘被显示为外置）添加内置设备属性。
   - 优先选择在电源管理与性能上都更优的 SMBIOS。
   - 在 macOS Ventura 13 及更新版本上为老 Intel CPU 重新启用电源管理。
   - 应用 itlwm kext 的 WiFi 配置，使开机时能自动连接 WiFi。

   以及更多……

5. **易于定制**
   在默认设置之外，用户可以自行做进一步调整。

   - 自定义 ACPI 补丁、kext 与 SMBIOS 调整（**不推荐**）。
   - 在不受支持的 macOS 版本上强制加载 kext。

<a id="how-to-use"></a>

## 🚀 **使用方法**

1. **下载 OpCore Simplify**：
   - 点击 **Code** → **Download ZIP**，或直接用这个[链接](https://github.com/lzhoang2801/OpCore-Simplify/archive/refs/heads/main.zip)。
   - 把下载的 ZIP 解压到你想要的位置。

   ![下载 OpCore Simplify](https://i.imgur.com/mcE7OSX.png)

2. **运行 OpCore Simplify**：
   - **Windows**：运行 `OpCore-Simplify.bat`。
   - **macOS**：运行 `OpCore-Simplify.command`。
   - **Linux**：用现成的 Python 解释器运行 `OpCore-Simplify.py`。
   - 如果出现 `Failed to create SSL context: No module named 'certifi'`，先安装依赖：`python -m pip install -r requirements.txt`（原生 Windows Python 在 `C:\Program Files\Common Files\SSL\cert.pem` 没有 CA 证书包，因此 `Scripts/resource_fetcher.py` 需要 `certifi` 才能校验 GitHub 下载）。

   ![OpCore Simplify 菜单](https://i.imgur.com/vTr1V9D.png)

3. **选择硬件报告**：
   - Windows 下会提供 `E. Export hardware report`，推荐用它，这样能拿到构建当刻最真实的硬件与 BIOS 信息。
   - 也可以手动用 [**Hardware Sniffer**](https://github.com/lzhoang2801/Hardware-Sniffer) 生成 `Report.json` 与 ACPI 转储。

   ![选择硬件报告](https://i.imgur.com/MbRmIGJ.png)

   ![加载 ACPI 表](https://i.imgur.com/SbL6N6v.png)

   ![兼容性检查](https://i.imgur.com/kuDGMmp.png)

4. **选择 macOS 版本并定制 OpenCore EFI**：
   - 默认会为你的硬件挑选最新的兼容版本。
   - OpCore Simplify 会自动应用必要的 ACPI 补丁与 kext。
   - 你可以按需逐项复核与调整。

   ![OpCore Simplify 菜单](https://i.imgur.com/TSk9ejy.png)

5. **构建 OpenCore EFI**：
   - 调整完所有选项后，选择 **Build OpenCore EFI** 生成 EFI。
   - 工具会自动下载所需的引导器与 kext，可能需要几分钟。

   ![WiFi Profile 提取](https://i.imgur.com/71TkJkD.png)

   ![选择 Codec Layout ID](https://i.imgur.com/Mcm20EQ.png)

   ![构建 OpenCore EFI](https://i.imgur.com/deyj5de.png)

6. **USB 定制**：
   - 构建完成后，按提示完成 USB 端口映射。

   ![结果](https://i.imgur.com/MIPigPF.png)

7. **制作 U 盘并安装 macOS**：
   - Windows 下用 [**UnPlugged**](https://github.com/corpnewt/UnPlugged) 制作安装 U 盘，或在 macOS 下参考[这份指南](https://dortania.github.io/OpenCore-Install-Guide/installer-guide/mac-install.html)。
   - 排错请参考 [OpenCore 排错指南](https://dortania.github.io/OpenCore-Install-Guide/troubleshooting/troubleshooting.html)。

> [!NOTE]
> 1. 安装成功后若需要 OpenCore Legacy Patcher，直接应用 root patch 即可启用缺失的功能（例如较新的 Broadcom 无线网卡与显卡加速）。
>
> 2. 对 AMD 显卡，应用 OpenCore Legacy Patcher 的 root patch 后，需要移除启动参数 `-radvesa`/`-amd_no_dgpu_accel`，显卡加速才会生效。
>
> 3. 若使用 NVIDIA Turing 或更新的显卡，请看下面的 [NullMoth NVIDIA 驱动](#nullmoth)。

<a id="nullmoth"></a>

## 🟫 **NullMoth NVIDIA 驱动**

本分支通过 [NullMoth NVIDIA 驱动](https://github.com/nullmoth/nvidia-macos-driver)，为 **macOS 15 Sequoia** 增加了对 NVIDIA Turing 及更新显卡（GTX 16、RTX 20/30/40/50、TITAN RTX、Quadro RTX 与 Quadro T 系列）的支持——它基于 NVIDIA 自家的开源 GPU 内核模块（r610），并在其上叠加了 Metal 插件、framebuffer、accelerator 与 AGDC shim。

受支持的显卡列表取自 NVIDIA `open-gpu-kernel-modules` 610.57.04 的表格，存放在
[`Scripts/datasets/nvidia_gsp_data.py`](Scripts/datasets/nvidia_gsp_data.py)。Kepler、Maxwell、Pascal **不**受该驱动支持，仍走原来的（OCLP）路径。

发现受支持的显卡时，OpCore Simplify 会把驱动需要的设置写进 `config.plist`：

| 设置项 | 取值 | 原因 |
|---|---|---|
| `NVRAM → Add → 7C436110-… → boot-args` | `nvfb=1 nvaccel=1 nvfbheads=4 -nvkmsnosmooth amfi_get_out_of_my_way=0x1 amfi=0x80 ipc_control_port_options=0` | framebuffer + accelerator，4 个显示头；AMFI 相关参数让 WindowServer 能加载驱动 bundle |
| `NVRAM → Add → … → csr-active-config` | `<430A0000>` | 驱动测试时所用的 SIP 值（它的 kext 没有 Apple 签名） |
| `Misc → Security → SecureBootModel` | `Disabled` | Apple Secure Boot 会拒绝非 Apple 签名的 kext |
| `Kernel → Block` | `com.apple.iokit.IONDRVSupport`、`Exclude` | 否则固件 framebuffer 会从 NVRMFB 手里抢走 display index 0 |
| `Kernel → Add` | `Lilu.kext`、`AMFIPass.kext` | 驱动的依赖 |
| `Booter → Quirks → ResizeAppleGpuBars` | `-1` | 保持固件给定的 BAR 尺寸；进入 macOS 后由驱动自己设置 BAR |
| `UEFI → Quirks → ResizeGpuBars` | `-1` | 强制改尺寸可能在选择器出现前就让固件卡住 |

对这张卡会移除 `nv_disable=1`、`-wegnoegpu` 与 `agdpmod=pikera`；若同一台机器上还有 Intel 或 AMD 显卡、也就是存在 WhateverGreen 时，会追加 `gfxrst=4`。

当这份配置用于启动 **macOS 安装器**时（安装器没有 NVIDIA 驱动、跑在固件 framebuffer 上），会改用安装器取值：`ResizeAppleGpuBars = 0`、`ResizeGpuBars = -1`，并且不屏蔽 `IONDRVSupport`。

同时装 NVIDIA 与 Intel 显卡的笔记本上，NVIDIA 卡会通过 ACPI 唤醒（`acpi-wake-type = 1`），避免 Optimus 机器在驱动接管前又把它睡过去；*Before Using EFI* 画面还会打印 mux 相关的提示。

驱动的四个内核扩展（`NVRM`、`NVAccel`、`NVRMFB`、`NVRMAGDC`）**不**从 `EFI/OC/Kexts` 注入：它们安装到 `/Library/Extensions`，由 Auxiliary Kernel Collection 加载。OpenCore 只需要负责 SIP 与启动参数。

用生成的 EFI 装好 macOS 之后，再在已安装的系统上装驱动：

```bash
tar -xzf nullmoth-nvidia-*.tar.gz && cd pkgroot
shasum -a 256 -c SHA256SUMS
sudo ./install.sh
```

BIOS 要求：**Above 4G Decoding 开启**、**CSM 关闭**。重启后验证：

```bash
kmutil showloaded --list-only | grep nullmoth   # 应有 4 行
system_profiler SPDisplaysDataType | head -20   # 应显示你的显卡，Metal: supported
```

[1401](https://github.com/nullmoth/1401) 应用（Windows 与 macOS）会自动完成驱动安装与它的引导项（*1401: Remove NVIDIA driver*）；本分支只负责生成这套方案在 OpenCore 侧的部分。

<a id="intel-igpu"></a>

## 🟦 **Intel Skylake/Kaby Lake 核显（macOS 14+）**

Apple 在 macOS 13 移除了 Skylake 图形驱动，因此 OpCore Simplify 通过 **Kaby Lake device-id 伪装** 来驱动 Skylake（`0x09`/`0x19`）与 Kaby Lake（`0x59`、`0x87C0`）核显——这套驱动在 macOS 14 与 15 上仍是原生的。这是纯粹的 device-id 伪装，不涉及 OCLP 的 root patch。

macOS 14 收紧了 AMFI 的库校验，因此缺少 `AMFIPass` 时，系统会在 `endpointsecurityd` 映射 `IOSurface` 时崩溃（“mapping process is a platform binary, but mapped file is not”）。所以对这些核显，在 macOS 14 及以上，生成器会自动加入 `AMFIPass` 与 `RestrictEvents`，并在屏幕上说明。

framebuffer 的接口表是**按主板定制的**，因此即使其他接口正常，某一个物理接口（台式主板上的 HDMI 尤其常见）也可能黑屏。遇到这种情况，请为该主板打接口映射补丁（[Dortania 指南](https://dortania.github.io/OpenCore-Post-Install/gpu-patching/intel-patching/connector.html)，或 Hackintool 的 *Framebuffer* 标签页）——*Before Using EFI* 画面会提醒你。如果配置里带了 `-igfxvesa`（DVI/HDMI 显示器接在核显上时会加上，用于保持固件显示模式并禁用加速），在打好映射补丁后请把它删掉。

<a id="contributing"></a>

## 🤝 **参与贡献**

贡献**非常欢迎**！如果你有改进想法，欢迎 fork 本仓库并提交 pull request，或开一个带 “enhancement” 标签的 issue。

也别忘了给项目点个 ⭐ star！谢谢支持！🌟

<a id="license"></a>

## 📜 **许可**

以 BSD 3-Clause 许可分发，详见 `LICENSE`。

<a id="credits"></a>

## 🙌 **致谢**

- [OpenCorePkg](https://github.com/acidanthera/OpenCorePkg) 与 [kexts](https://github.com/lzhoang2801/OpCore-Simplify/blob/main/Scripts/datasets/kext_data.py) —— 本项目的骨架。
- [SSDTTime](https://github.com/corpnewt/SSDTTime) —— SSDT 补丁工具。

<a id="contact"></a>

## 📞 **联系**

**Hoang Hong Quan**
> Facebook [@macforce2601](https://facebook.com/macforce2601) &nbsp;&middot;&nbsp;
> Telegram [@lzhoang2601](https://t.me/lzhoang2601) &nbsp;&middot;&nbsp;
> Email: lzhoang2601@gmail.com

<a id="star-history"></a>

## 🌟 **Star 历史**

[![Star History Chart](https://star-history.dera.page/svg?repos=lzhoang2801/OpCore-Simplify&type=Date)](https://star-history.dera.page/#lzhoang2801/OpCore-Simplify&Date)
