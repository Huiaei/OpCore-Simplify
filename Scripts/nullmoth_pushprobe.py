                    print("1. \033[1mlaobamac AirportItlwm\033[0m - Native WiFi on Sequoia 15.2+ and Tahoe without OCLP root patches")
                    print("")
                print("{}. \033[1mAirportItlwm\033[0m - Uses native WiFi settings menu".format(2 if native_fork_available else 1))
                print("   • Provides Handoff, Universal Clipboard, Location Services, Instant Hotspot support")
                print("   • Supports enterprise-level security")
                if darwin_major >= 24:
                    print("   • Requires OCLP root patches on Sequoia and Tahoe but may cause issues")
                print("")
                print("{}. \033[1mitlwm\033[0m - More stable overall".format(len(wifi_options)))