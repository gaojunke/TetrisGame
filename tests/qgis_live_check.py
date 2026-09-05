"""Connect the current QGIS user's anonymous profile; never submit a score."""
import os
import sys
import importlib.util
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qgis.core import QgsApplication
from qgis.PyQt.QtCore import QTimer

QgsApplication.setPrefixPath(os.environ["QGIS_PREFIX_PATH"], True)
app = QgsApplication([], True)
app.initQgis()
project_root = Path(__file__).resolve().parents[1]
if not (project_root / "TetrisGame_updated").is_dir():
    spec = importlib.util.spec_from_file_location(
        "TetrisGame_updated", project_root / "__init__.py",
        submodule_search_locations=[str(project_root)])
    package = importlib.util.module_from_spec(spec)
    sys.modules["TetrisGame_updated"] = package
    spec.loader.exec_module(package)
from TetrisGame_updated.leaderboard import LeaderboardClient

client = LeaderboardClient()
success = False


def check():
    global success
    if client.status.startswith("Online ·"):
        success = True
        print("HTTPS profile and leaderboard: OK", flush=True)
        print("Nickname:", client.player.get("nickname"), "Country:", client.player.get("country"), flush=True)
        print("Public entries:", len(client.players), flush=True)
        app.quit()
    elif "unavailable" in client.status or "Invalid" in client.status:
        print(client.status, flush=True)
        app.quit()


client.changed.connect(check)
QTimer.singleShot(25000, app.quit)
QTimer.singleShot(0, client.refresh)
app.exec()
client.close()
app.exitQgis()
sys.exit(0 if success else 1)
