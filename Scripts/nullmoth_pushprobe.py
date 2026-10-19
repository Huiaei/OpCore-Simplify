        config["Kernel"]["Emulate"]["DummyPowerManagement"] = "AMD" in hardware_report.get("CPU").get("Manufacturer") or \
            self.is_low_end_intel_cpu(hardware_report.get("CPU").get("Processor Name"))
        config["Kernel"]["Force"] = []
        config["Kernel"]["Quirks"]["AppleCpuPmCfgLock"] = hardware_report.get("CPU").get("Codename") in cpu_data.IntelCPUGenerations[62:]
