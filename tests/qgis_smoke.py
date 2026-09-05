"""Run with QGIS's Python. Uses isolated settings, never production scores."""
import os
import sys
import tempfile
import unittest
import traceback
from pathlib import Path
from unittest.mock import patch
import importlib.util

os.environ["QT_QPA_PLATFORM"] = "offscreen"
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))
from qgis.core import QgsApplication, Qgis
from qgis.PyQt.QtCore import QSettings, Qt, QPoint
from qgis.PyQt.QtGui import QFontDatabase, QFont
from qgis.PyQt.QtWidgets import QFrame, QLabel

QgsApplication.setPrefixPath(os.environ["QGIS_PREFIX_PATH"], True)
app = QgsApplication([], True)
app.initQgis()
# The headless Qt platform does not discover Windows' system fonts itself.
for font in ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/msyh.ttc"):
    QFontDatabase.addApplicationFont(font)
app.setFont(QFont("Arial", 9))
qt_errors = []


def report_exception(kind, value, tb):
    qt_errors.append(str(value))
    traceback.print_exception(kind, value, tb, file=sys.stdout)


sys.excepthook = report_exception

if not (project_root / "TetrisGame_updated").is_dir():
    spec = importlib.util.spec_from_file_location(
        "TetrisGame_updated", project_root / "__init__.py",
        submodule_search_locations=[str(project_root)])
    package = importlib.util.module_from_spec(spec)
    sys.modules["TetrisGame_updated"] = package
    spec.loader.exec_module(package)

from TetrisGame_updated.leaderboard import LeaderboardClient, PREFIX, valid_player
from TetrisGame_updated.game_tetris import TetrisWindow, WECHAT_URL, REPOSITORY_URL
from TetrisGame_updated.alg_tetris import TetrisAlgorithm
from TetrisGame_updated.leaderboard_panel import LeaderboardPanel, country_name, short_nickname


class PluginTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="tetris-test-")
        self.settings = QSettings(str(Path(self.temp.name) / "test.ini"), QSettings.Format.IniFormat)
        self.client = LeaderboardClient(settings=self.settings, endpoint="")

    def tearDown(self):
        self.client.close()
        self.settings.sync()
        self.temp.cleanup()

    def test_identity_and_offline_queue(self):
        token = self.client._token
        self.client.submit(100, 1, 4, 4000)
        again = LeaderboardClient(settings=self.settings, endpoint="")
        self.assertEqual(token, again._token)
        self.assertEqual(len(again._pending()), 1)
        self.assertEqual(again._pending()[0]["score"], 100)
        self.client.set_enabled(False)
        self.assertEqual(self.client._pending(), [])
        self.client.submit(200, 2, 10, 5000)
        self.assertEqual(self.client._pending(), [])
        again.close()

    def test_queue_limit(self):
        for _ in range(105):
            self.client.submit(0, 0, 1, 2000)
        self.assertEqual(len(self.client._pending()), 100)
        self.assertEqual(len({x["event_id"] for x in self.client._pending()}), 100)

    def test_validation_and_country(self):
        self.assertEqual(country_name("CN"), "China")
        self.assertEqual(country_name("XX"), "Unknown")
        self.assertEqual(short_nickname("GoldenWhale-1234abcd"), "GoldenWhale·1234")
        self.assertFalse(valid_player({"nickname": "<img src=x>", "country": "CN", "score": 10}))
        self.assertFalse(valid_player({"nickname": "JadeFox-1234abcd", "country": "CN", "score": True}))
        self.client._ranking_ready({"players": []})
        self.assertTrue(self.client.status.startswith("Online"))
        self.client._ranking_ready({"players": [None]})
        self.assertTrue(self.client.status.startswith("Invalid"))

    def test_compact_panel_controls_and_unknown_country(self):
        panel = LeaderboardPanel(self.client)
        panel.show()
        app.processEvents()
        self.assertEqual(panel.table.item(0, 0).text(), "—")
        self.assertEqual(panel.table.item(4, 2).text(), "—")
        self.assertEqual(panel.actions(), [panel.refresh_action, panel.sharing_action,
                                           panel.privacy_action])
        self.assertTrue(panel.sharing_action.isChecked())
        panel.sharing_action.trigger()
        self.assertFalse(self.client.enabled)
        panel.sharing_action.trigger()
        self.assertTrue(self.client.enabled)
        with patch("TetrisGame_updated.leaderboard_panel.QMessageBox.information") as privacy:
            panel.privacy_action.trigger()
            privacy.assert_called_once()
        self.client.players = [{"nickname": "GoldenWhale-1234abcd", "score": 10000000,
                                "country": "XX"}]
        self.client.changed.emit()
        app.processEvents()
        self.assertEqual(panel.table.item(0, 1).text(), "10000000")
        self.assertLessEqual(panel.table.fontMetrics().horizontalAdvance("10000000") + 6,
                             panel.table.columnWidth(1))
        self.assertEqual(panel.table.item(0, 2).text(), "—")
        self.assertEqual(panel.table.item(0, 2).toolTip(), "Unknown")
        self.assertFalse(qt_errors)
        panel.close()

    def test_gui_and_scoring_hooks(self):
        win = TetrisWindow(leaderboard_client=self.client)
        win.show()
        app.processEvents()
        self.assertFalse(qt_errors)
        win.timer.stop()
        self.assertTrue(TetrisAlgorithm().flags() & Qgis.ProcessingAlgorithmFlag.NoThreading)
        self.assertEqual(win.credit_label.text(), "河北地质大学\n高科科\nQQ:996517087")
        self.assertFalse(win.github_button.icon().isNull())
        self.assertFalse(win.wechat_button.icon().isNull())
        github_pos = win.github_button.mapTo(win, QPoint(0, 0))
        wechat_pos = win.wechat_button.mapTo(win, QPoint(0, 0))
        self.assertEqual(github_pos.y(), wechat_pos.y())
        self.assertGreater(wechat_pos.x(), github_pos.x())
        with patch("TetrisGame_updated.game_tetris.QDesktopServices.openUrl") as opened:
            win.wechat_button.click()
            self.assertEqual(opened.call_args.args[0].toString(), WECHAT_URL)
            win.github_button.click()
            self.assertEqual(opened.call_args.args[0].toString(), REPOSITORY_URL)
        with patch.object(self.client, "submit") as submitted:
            win.drop_down()
            win.record_score()
            win.record_score()
            self.assertEqual(submitted.call_count, 1)
            self.assertGreaterEqual(submitted.call_args.args[2], 1)
            win.restart()
            win.timer.stop()
            win.pause_toggle()
            win.restart()
            win.timer.stop()
            self.assertEqual(win.btn_pause.text(), "Pause")
        # Fixture-only preview to inspect long nicknames, not an online score.
        self.client.players = [
            {"nickname": "GoldenWhale-1234abcd", "score": 15000, "country": "CN"},
            {"nickname": "ArcticPanda-2234abcd", "score": 12000, "country": "US"},
            {"nickname": "AzureCrane-3234abcd", "score": 9900, "country": "DE"},
            {"nickname": "AmberOtter-4234abcd", "score": 8500, "country": "JP"},
            {"nickname": "BraveFinch-5234abcd", "score": 7200, "country": "BR"},
        ]
        self.client.player = self.client.players[0]
        self.client.status = "UI test fixtures · not live rankings"
        self.client.changed.emit()
        app.processEvents()
        panel = win.leaderboard_panel
        self.assertEqual(panel.table.rowCount(), 5)
        self.assertEqual(panel.table.columnCount(), 3)
        self.assertEqual(panel.width(), 212)
        self.assertEqual(panel.table.width(), 200)
        self.assertLessEqual(win.width(), 650)
        self.assertFalse(panel.table.horizontalHeader().isVisible())
        self.assertFalse(panel.table.verticalHeader().isVisible())
        self.assertEqual(panel.table.frameShape(), QFrame.Shape.NoFrame)
        self.assertFalse(panel.table.showGrid())
        self.assertFalse(panel.table.alternatingRowColors())
        self.assertEqual([label.text() for label in panel.findChildren(QLabel)], ["WORLD TOP 5"])
        self.assertEqual([panel.table.item(0, col).text() for col in range(3)],
                         ["GoldenWhale·1234", "15000", "CN"])
        self.assertEqual(panel.table.item(0, 0).toolTip(), "GoldenWhale-1234abcd")
        self.assertEqual(panel.table.item(0, 2).toolTip(), "China")
        self.assertIn("GoldenWhale-1234abcd", panel.heading.toolTip())
        print("Compact layout:", win.width(), "x", win.height(),
              "leaderboard values:", panel.table.width(), "px")
        self.assertFalse(qt_errors)
        output = Path(__file__).resolve().parents[1] / "qgis4-compact-leaderboard-preview.png"
        self.assertTrue(win.grab().save(str(output)))
        win.close()


if __name__ == "__main__":
    print("QGIS", Qgis.QGIS_VERSION)
    result = unittest.main(exit=False)
    app.exitQgis()
    sys.exit(not result.result.wasSuccessful())
