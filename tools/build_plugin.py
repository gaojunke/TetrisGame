"""Create and reopen a clean QGIS ZIP; no service code or credentials included."""
import ast
import configparser
import hashlib
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED, ZipInfo

root = Path(__file__).resolve().parents[1]
source = root / "TetrisGame_updated"
if not source.is_dir():
    source = root
metadata = configparser.ConfigParser()
metadata.read(source / "metadata.txt", encoding="utf-8")
version = metadata["general"]["version"]
names = ["__init__.py", "main.py", "provider.py", "alg_tetris.py", "game_tetris.py",
         "leaderboard.py", "leaderboard_panel.py", "leaderboard_config.py", "metadata.txt",
         "README.md", "LICENSE", "PRIVACY.md", "icons/plugin-icon.svg",
         "icons/github-mark.svg", "icons/wechat.svg"]
for name in names:
    if name.endswith(".py"):
        ast.parse((source / name).read_text(encoding="utf-8"), filename=name)
target = root / f"TetrisGame_updated-{version}-qgis4.zip"
with ZipFile(target, "w", ZIP_DEFLATED) as archive:
    for name in names:
        info = ZipInfo("TetrisGame_updated/" + name)
        info.create_system = 3
        info.external_attr = 0o100644 << 16
        info.compress_type = ZIP_DEFLATED
        archive.writestr(info, (source / name).read_bytes())
with ZipFile(target) as archive:
    assert archive.testzip() is None
    assert len(archive.infolist()) == len(names)
    for name in names:
        assert archive.read("TetrisGame_updated/" + name) == (source / name).read_bytes()
print(target)
print("Files:", len(names), "Bytes:", target.stat().st_size)
print("SHA256:", hashlib.sha256(target.read_bytes()).hexdigest())
