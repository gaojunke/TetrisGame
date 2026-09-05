"""Compact top-five panel, independent of the board and existing controls."""

from qgis.PyQt.QtCore import Qt, QLocale
from qgis.PyQt.QtGui import QAction, QColor
from qgis.PyQt.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QFrame, QMessageBox,
)


def country_name(code):
    if code == "XX":
        return "Unknown"
    territory = QLocale.codeToTerritory(code)
    if territory == QLocale.Country.AnyCountry:
        return code
    return QLocale.territoryToString(territory)


def short_nickname(nickname):
    """Abbreviate only the display; the stored online identity is unchanged."""
    name, separator, suffix = nickname.rpartition("-")
    return f"{name}·{suffix[:4]}" if separator else nickname


class LeaderboardPanel(QWidget):
    def __init__(self, client, parent=None):
        super().__init__(parent)
        self.client = client
        # The values occupy 200 px, matching the width of the game board.
        self.setFixedWidth(212)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 0, 0)
        layout.setSpacing(10)
        self.heading = QLabel("WORLD TOP 5")
        self.heading.setStyleSheet("font-size: 14px; font-weight: 600; color: #283445;")
        layout.addWidget(self.heading)
        self.table = QTableWidget(5, 3)
        self.table.horizontalHeader().hide()
        self.table.verticalHeader().hide()
        self.table.setFrameShape(QFrame.Shape.NoFrame)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(False)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.verticalHeader().setDefaultSectionSize(28)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 54)
        self.table.setColumnWidth(2, 28)
        self.table.setFixedHeight(140)
        self.table.setStyleSheet(
            "QTableWidget { border: none; background: transparent; color: #405268; font-size: 11px; }"
            "QTableWidget::item { border: none; padding: 0; }"
        )
        layout.addWidget(self.table)
        layout.addStretch(1)

        # Keep the main view values-only without removing existing controls.
        self.refresh_action = QAction("Refresh", self)
        self.refresh_action.triggered.connect(client.refresh)
        self.sharing_action = QAction("Online ranking", self)
        self.sharing_action.setCheckable(True)
        self.sharing_action.toggled.connect(client.set_enabled)
        self.privacy_action = QAction("Privacy…", self)
        self.privacy_action.triggered.connect(self.show_privacy)
        for widget in (self, self.heading, self.table):
            widget.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)
            widget.addActions([self.refresh_action, self.sharing_action, self.privacy_action])
        client.changed.connect(self.render)
        self.render()

    def render(self):
        for index in range(5):
            row = self.client.players[index] if index < len(self.client.players) else None
            if row:
                values = [short_nickname(row["nickname"]), str(row["score"]),
                          row["country"] if row["country"] != "XX" else "—"]
                full_values = [row["nickname"], f'{row["score"]:,}', country_name(row["country"])]
            else:
                values = full_values = ["—", "—", "—"]
            for column, text in enumerate(values):
                item = QTableWidgetItem(text)
                item.setToolTip(full_values[column])
                item.setData(Qt.ItemDataRole.AccessibleTextRole, full_values[column])
                if column == 1:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                elif column == 2:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    item.setForeground(QColor("#7A8494"))
                if row is None:
                    item.setForeground(QColor("#A6AFBA"))
                self.table.setItem(index, column, item)
        player = self.client.player
        identity = (
            f'You: {player["nickname"]}\n{country_name(player["country"])} · Best: {player["score"]:,}'
            if player else ""
        )
        details = "\n".join(part for part in (self.client.status, identity,
                            "Right-click for refresh, online ranking and privacy.") if part)
        self.heading.setToolTip(details)
        self.setAccessibleDescription(details)
        blocked = self.sharing_action.blockSignals(True)
        self.sharing_action.setChecked(self.client.enabled)
        self.sharing_action.blockSignals(blocked)

    def show_privacy(self):
        QMessageBox.information(
            self, "Online leaderboard · Privacy",
            "No account or real name is required. An installation-specific random token "
            "keeps your generated nickname stable. Game results (score, lines, pieces and "
            "duration) are sent over HTTPS to the plugin operator's Cloudflare service.\n\n"
            "Cloudflare estimates your country from your connection IP. VPNs/proxies can "
            "change this result; unknown countries use a dash with an Unknown tooltip. The application "
            "database does not store your IP, and no QGIS projects or layers are sent.\n\n"
            "Top five nicknames, best scores and countries are public. Disable Online "
            "ranking to stop requests and discard unsent results; existing online scores "
            "remain. Up to 100 recent offline results are queued for retry.\n\n"
            "Operator: Gao Keke / 高科科 · 996517087@qq.com. Contact the operator with "
            "your generated nickname to request removal. See PRIVACY.md for details."
        )
