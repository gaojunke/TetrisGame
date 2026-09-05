from qgis.core import QgsProcessingAlgorithm, QgsApplication, Qgis
from .game_tetris import TetrisWindow

class TetrisAlgorithm(QgsProcessingAlgorithm):
    def name(self):
        return "tetris"

    def displayName(self):
        return "Play Tetris Game"

    def group(self):
        # The provider already supplies the "Tetris Game" top-level entry.
        # An empty group keeps this one-command plugin directly below it.
        return ""

    def groupId(self):
        return ""

    def initAlgorithm(self, config=None):
        pass

    def flags(self):
        # Qt widgets and the async network client must live on the GUI thread.
        return super().flags() | Qgis.ProcessingAlgorithmFlag.NoThreading

    def createInstance(self):
        return TetrisAlgorithm()

    def processAlgorithm(self, parameters, context, feedback):
        win = TetrisWindow()
        provider = QgsApplication.processingRegistry().providerById("tetrisgame")
        if provider:
            provider.hold_window(win)
        win.show()
        return {}
