"""Compact top-five panel, independent of the board and existing controls."""

from qgis.PyQt.QtCore import Qt, QLocale
from qgis.PyQt.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QPushButton, QCheckBox, QMessageBox,
)


def country_name(code):
    if code == "XX":
        return "Unknown"
    territory = QLocale.codeToTerritory(code)
    if territory == QLocale.Country.AnyCountry:
        return code
    return QLocale.territoryToString(territory)


class LeaderboardPanel(QWidget):
    def __init__(self, client, parent=None):
        super().__init__(parent)
        self.client = client
        self.setMinimumWidth(375)
        self.setMaximumWidth(410)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 6, 4, 6)
        layout.setSpacing(12)
        heading = QLabel("WORLD TOP 5")
        heading.setStyleSheet("font-size: 17px; font-weight: 700; color: #283445;")
        subheading = QLabel("One player · one personal best")
        subheading.setStyleSheet("color: #7A8494; font-size: 11px;")
        layout.addWidget(heading)
        layout.addWidget(subheading)
        self.table = QTableWidget(5, 3)
        self.table.setHorizontalHeaderLabels(["Nickname", "Score", "Country"])
        self.table.setVerticalHeaderLabels(["1", "2", "3", "4", "5"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.verticalHeader().setDefaultSectionSize(43)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 66)
        self.table.setFixedHeight(246)
        self.table.setStyleSheet(
            "QTableWidget { border: 1px solid #E0E5EB; border-radius: 6px;"
            "background: #FFFFFF; alternate-background-color: #F6F8FB; color: #283445; font-size: 11px; }"
            "QHeaderView::section { background: #EEF2F6; color: #627084; border: none; padding: 5px; }"
        )
        layout.addWidget(self.table)
        self.identity = QLabel()
        self.identity.setTextFormat(Qt.TextFormat.PlainText)
        self.identity.setWordWrap(True)
        self.identity.setStyleSheet("font-size: 11px; color: #405268;")
        self.status = QLabel()
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        self.status.setWordWrap(True)
        self.status.setMinimumHeight(36)
        self.status.setStyleSheet("font-size: 11px; color: #7A8494;")
        layout.addWidget(self.identity)
        layout.addWidget(self.status)
        actions = QHBoxLayout()
        self.sharing = QCheckBox("Online ranking")
        self.sharing.setChecked(client.enabled)
        self.sharing.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.sharing.setToolTip("Share your generated nickname, best score and IP-based country. No login.")
        self.sharing.toggled.connect(client.set_enabled)
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.refresh_button.clicked.connect(client.refresh)
        actions.addWidget(self.sharing)
        actions.addStretch()
        actions.addWidget(self.refresh_button)
        layout.addLayout(actions)
        notice = QPushButton("Auto nickname · country from IP · Privacy")
        notice.setStyleSheet("text-align: left; border: none; color: #7A8494; font-size: 10px;")
        notice.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        notice.clicked.connect(self.show_privacy)
        layout.addWidget(notice)
        layout.addStretch(1)
        client.changed.connect(self.render)
        self.render()

    def render(self):
        for index in range(5):
            row = self.client.players[index] if index < len(self.client.players) else None
            values = [row["nickname"], f'{row["score"]:,}', country_name(row["country"])] if row else ["—", "—", "—"]
            for column, text in enumerate(values):
                item = QTableWidgetItem(text)
                item.setToolTip(text)
                if column == 1:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(index, column, item)
        player = self.client.player
        self.identity.setText(
            f'You: {player["nickname"]}\n{country_name(player["country"])} · Best: {player["score"]:,}'
            if player else "Your nickname is generated automatically\non the first successful connection."
        )
        self.status.setText(self.client.status)

    def show_privacy(self):
        QMessageBox.information(
            self, "Online leaderboard · Privacy",
            "No account or real name is required. An installation-specific random token "
            "keeps your generated nickname stable. Game results (score, lines, pieces and "
            "duration) are sent over HTTPS to the plugin operator's Cloudflare service.\n\n"
            "Cloudflare estimates your country from your connection IP. VPNs/proxies can "
            "change this result; unknown countries are shown as Unknown. The application "
            "database does not store your IP, and no QGIS projects or layers are sent.\n\n"
            "Top five nicknames, best scores and countries are public. Disable Online "
            "ranking to stop requests and discard unsent results; existing online scores "
            "remain. Up to 100 recent offline results are queued for retry.\n\n"
            "Operator: Gao Keke / 高科科 · 996517087@qq.com. Contact the operator with "
            "your generated nickname to request removal. See PRIVACY.md for details."
        )
