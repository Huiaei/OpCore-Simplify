from Scripts.datasets import cpu_data
from Scripts.datasets import kext_data
from Scripts.datasets import os_data
from Scripts.datasets import pci_data
from Scripts.datasets import codec_layouts
from Scripts import nullmoth
from Scripts import utils
import os
import shutil

try:
    long
    unicode
except NameError:
    long = int
    unicode = str

class KextMaestro:
    def __init__(self):
        self.utils = utils.Utils()

    def uncheck_kext(self, kext, kexts, device_properties, macOS_version, config):
        pass
