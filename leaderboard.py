"""Anonymous, asynchronous leaderboard; gameplay never waits for the network."""

import json
import re
import secrets

from qgis.core import QgsNetworkAccessManager, QgsSettings
from qgis.PyQt.QtCore import QObject, QTimer, QUrl, pyqtSignal
from qgis.PyQt.QtNetwork import QNetworkReply, QNetworkRequest

from .leaderboard_config import API_BASE_URL

PREFIX = "TetrisGame/leaderboard/"
MAX_PENDING = 100
MAX_RESPONSE = 65536


def valid_player(value):
    """Treat server/cached content as data, never rich text or executable code."""
    return (
        isinstance(value, dict)
        and isinstance(value.get("nickname"), str)
        and re.fullmatch(r"[A-Za-z]+-[0-9a-f]{8}", value["nickname"]) is not None
        and isinstance(value.get("country"), str)
        and re.fullmatch(r"[A-Z]{2}", value["country"]) is not None
        and type(value.get("score")) is int
        and 0 <= value["score"] <= 10000000
    )


class LeaderboardClient(QObject):
    changed = pyqtSignal()

    def __init__(self, parent=None, settings=None, endpoint=API_BASE_URL):
        super().__init__(parent)
        self.settings = settings if settings is not None else QgsSettings()
        self.endpoint = endpoint.rstrip("/")
        self.enabled = self.settings.value(PREFIX + "enabled", True, type=bool)
        token = self.settings.value(PREFIX + "installation_token", "", type=str)
        if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
            token = secrets.token_urlsafe(32)
            self.settings.setValue(PREFIX + "installation_token", token)
        self._token = token
        cached = self._read_json("profile", {})
        self.player = cached if valid_player(cached) else {}
        cached = self._read_json("top5", [])
        self.players = [row for row in cached if valid_player(row)][:5] if isinstance(cached, list) else []
        self.status = "Not connected"
        self._busy = False
        self._closed = False
        self._reply = None
        self._registered = False
        self._generation = 0
        self._timer = QTimer(self)
        self._timer.setInterval(60000)
        self._timer.timeout.connect(self.refresh)

    def _read_json(self, name, default):
        raw = self.settings.value(PREFIX + name, "", type=str)
        if len(raw) > 131072:
            return default
        try:
            return json.loads(raw) if raw else default
        except (TypeError, ValueError):
            return default

    def _save_json(self, name, value):
        self.settings.setValue(PREFIX + name, json.dumps(value, separators=(",", ":")))

    def _pending(self):
        value = self._read_json("pending", [])
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, dict) and
                isinstance(item.get("event_id"), str) and
                re.fullmatch(r"[0-9a-f]{32}", item["event_id"])][:MAX_PENDING]

    def set_enabled(self, enabled):
        self.enabled = bool(enabled)
        self.settings.setValue(PREFIX + "enabled", self.enabled)
        if not self.enabled:
            self._generation += 1
            self._timer.stop()
            self._save_json("pending", [])
            if self._reply is not None:
                self._reply.abort()
            self._busy = False
            self.status = "Offline play · sharing disabled"
            self.changed.emit()
        else:
            self.refresh()

    def refresh(self):
        self.enabled = self.settings.value(PREFIX + "enabled", True, type=bool)
        if self._closed or self._busy:
            return
        if not self.enabled:
            self.status = "Offline play · sharing disabled"
            self.changed.emit()
            return
        self._timer.start()
        url = QUrl(self.endpoint)
        if (not url.isValid() or url.scheme() != "https" or not url.host()
                or url.userInfo() or url.hasQuery() or url.hasFragment()):
            self.status = "Leaderboard service not configured"
            self.changed.emit()
            return
        self._busy = True
        self.status = "Connecting…"
        self.changed.emit()
        if not self._registered:
            self._request("/v1/player", {}, self._profile_ready)
        else:
            self._flush()

    def submit(self, score, lines, pieces, duration_ms):
        self.enabled = self.settings.value(PREFIX + "enabled", True, type=bool)
        if not self.enabled or pieces < 1:
            return
        pending = self._pending()
        pending.append({"event_id": secrets.token_hex(16), "score": int(score),
                        "lines": int(lines), "pieces": int(pieces),
                        "duration_ms": max(1, int(duration_ms))})
        self._save_json("pending", pending[-MAX_PENDING:])
        self.refresh()

    def _set_player(self, data):
        player = data.get("player") if isinstance(data, dict) else None
        if not valid_player(player):
            self._fail("Invalid leaderboard response")
            return False
        self.player = player
        self._save_json("profile", player)
        self.changed.emit()
        return True

    def _profile_ready(self, data):
        if self._set_player(data):
            self._registered = True
            self._flush()

    def _flush(self):
        pending = self._pending()
        if pending:
            item = pending[0]
            self.status = "Syncing scores…"
            self.changed.emit()
            self._request("/v1/scores", item, lambda data: self._submitted(item, data),
                          rejected=lambda: self._reject(item))
        else:
            self._request("/v1/leaderboard", None, self._ranking_ready)

    def _remove_pending(self, item):
        # Reload before writing: two open game windows can share this queue.
        self._save_json("pending", [row for row in self._pending()
                                    if row["event_id"] != item["event_id"]])

    def _submitted(self, item, data):
        if self._set_player(data):
            self._remove_pending(item)
            # Space requests out so an offline backlog does not exhaust limits.
            QTimer.singleShot(2500, self._continue_flush)

    def _continue_flush(self):
        if not self._closed and self.enabled and self._busy:
            self._flush()

    def _reject(self, item):
        self._remove_pending(item)
        self._fail("One score was rejected; other scores will retry")

    def _ranking_ready(self, data):
        rows = data.get("players") if isinstance(data, dict) else None
        if not isinstance(rows, list) or len(rows) > 5 or not all(valid_player(row) for row in rows):
            self._fail("Invalid leaderboard response")
            return
        self.players = rows
        self._save_json("top5", rows)
        self._busy = False
        self.status = "Online · personal best scores"
        self.changed.emit()

    def _fail(self, message):
        self._busy = False
        count = len(self._pending())
        self.status = message + (f" · {count} score(s) saved for retry" if count else " · cached results")
        self.changed.emit()

    def _request(self, path, payload, callback, rejected=None):
        self.enabled = self.settings.value(PREFIX + "enabled", True, type=bool)
        if self._closed or not self.enabled:
            self._busy = False
            return
        generation = self._generation
        request = QNetworkRequest(QUrl(self.endpoint + path))
        request.setRawHeader(b"Accept", b"application/json")
        # Never follow a redirect with the installation's bearer credential.
        request.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute,
                             QNetworkRequest.RedirectPolicy.ManualRedirectPolicy)
        manager = QgsNetworkAccessManager.instance()
        if payload is None:
            reply = manager.get(request)
        else:
            request.setRawHeader(b"Authorization", ("Bearer " + self._token).encode("ascii"))
            request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
            reply = manager.post(request, json.dumps(payload).encode("utf-8"))
        self._reply = reply
        reply.setReadBufferSize(MAX_RESPONSE + 1)
        buffer = bytearray()
        timeout = QTimer(reply)
        timeout.setSingleShot(True)
        timeout.timeout.connect(reply.abort)
        timeout.start(10000)

        def drain():
            buffer.extend(bytes(reply.readAll()))
            if len(buffer) > MAX_RESPONSE:
                reply.abort()

        def finished():
            timeout.stop()
            drain()
            status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
            failed = reply.error() != QNetworkReply.NetworkError.NoError
            if self._reply is reply:
                self._reply = None
            reply.deleteLater()
            if self._closed or generation != self._generation:
                return
            if status in (400, 413, 415) and rejected is not None:
                rejected()
                return
            if failed or status != 200 or len(buffer) > MAX_RESPONSE:
                self._fail("Leaderboard unavailable; game is offline")
                return
            try:
                data = json.loads(buffer.decode("utf-8"))
            except (ValueError, UnicodeError):
                self._fail("Invalid leaderboard response")
                return
            callback(data)

        reply.readyRead.connect(drain)
        reply.finished.connect(finished)

    def close(self):
        self._closed = True
        self._timer.stop()
        if self._reply is not None:
            self._reply.abort()
