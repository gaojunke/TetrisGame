from qgis.core import QgsProcessingProvider
from .alg_tetris import TetrisAlgorithm

class TetrisProvider(QgsProcessingProvider):

    def __init__(self):
        super().__init__()
        self._windows = []

    def hold_window(self, win):
        self._windows.append(win)

    def close_windows(self):
        for window in self._windows:
            window.close()
        self._windows.clear()

    def id(self):
        return "tetrisgame"

    def name(self):
        return "Tetris Game"

    def loadAlgorithms(self):
        self.addAlgorithm(TetrisAlgorithm())
