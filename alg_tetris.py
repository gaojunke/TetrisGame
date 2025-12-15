from qgis.core import QgsProcessingAlgorithm, QgsApplication
from .game_tetris import TetrisWindow

class TetrisAlgorithm(QgsProcessingAlgorithm):
    def name(self):
        return "tetris"

    def displayName(self):
        return "Play Tetris Game"

    def group(self):
        return "Tetris Game"

    def groupId(self):
        return "tetrisgame"

    def initAlgorithm(self, config=None):
        pass

    def createInstance(self):
        return TetrisAlgorithm()

    def processAlgorithm(self, parameters, context, feedback):
        win = TetrisWindow()
        provider = QgsApplication.processingRegistry().providerById("tetrisgame")
        if provider:
            provider.hold_window(win)
        win.show()
        return {}
