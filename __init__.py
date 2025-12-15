from .main import TetrisPlugin

def classFactory(iface):
    return TetrisPlugin(iface)
