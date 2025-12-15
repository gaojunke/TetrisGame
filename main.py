from qgis.core import QgsApplication
from .provider import TetrisProvider

class TetrisPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.provider = TetrisProvider()

    def initGui(self):
        QgsApplication.processingRegistry().addProvider(self.provider)

    def unload(self):
        QgsApplication.processingRegistry().removeProvider(self.provider)
