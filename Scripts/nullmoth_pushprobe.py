        for personality_name, properties in plist_data.get("IOKitPersonalities", {}).items():
            matching_keys = [key for key in self.matching_keys if key in properties]
            
            if not matching_keys:
                continue
            
            match_key = matching_keys[0]

            if match_key in ["IOPCIMatch", "IOPCIPrimaryMatch"]:
                pci_list = properties[match_key].split(" ")
                for pci_id in pci_list:
                    vendor_id = pci_id[-4:]
                    device_id = pci_id[2:6]
                    pci_ids.append("{}-{}".format(vendor_id, device_id).upper())
            elif match_key == "IONameMatch":
                for pci_id in properties[match_key]:
                    vendor_id = pci_id[3:7]
                    device_id = pci_id.split(",")[1].zfill(4)
                    pci_ids.append("{}-{}".format(vendor_id, device_id).upper())
            elif match_key == "idProduct":
                vendor_id = self.utils.int_to_hex(properties["idVendor"]).zfill(4)
                device_id = self.utils.int_to_hex(properties["idProduct"]).zfill(4)
                pci_ids.append("{}-{}".format(vendor_id, device_id).upper())
            elif match_key == "HDAConfigDefault":
                for codec_layout in properties[match_key]:
                    codec_id = self.utils.int_to_hex(codec_layout.get("CodecID")).zfill(8)
                    pci_ids.append("{}-{}".format(codec_id[:4], codec_id[-4:]))
                pci_ids = sorted(list(set(pci_ids)))

        return pci_ids

    def is_intel_hedt_cpu(self, processor_name, cpu_codename):
        if cpu_codename in cpu_data.IntelCPUGenerations[45:66]:
            return cpu_codename.endswith(("-X", "-P", "-W", "-E", "-EP", "-EX"))
        