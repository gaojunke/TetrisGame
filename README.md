# TetrisGame for QGIS

TetrisGame is a lightweight classic Tetris game for QGIS 4.0 and later. It is a small recreational plugin intended for a short break during GIS work; it does not alter projects, layers, or data.

## Installation

Download the current plugin ZIP from the QGIS Plugins Repository, then use **Plugins > Manage and Install Plugins… > Install from ZIP** in QGIS.

## Launching the game

1. Open **Processing > Toolbox**.
2. Expand **Tetris Game**.
3. Double-click **Play Tetris Game**.

## Controls

| Key | Action |
| --- | --- |
| Left / Right | Move the piece |
| Down | Move down one row |
| Up | Rotate |
| Space | Drop immediately |
| P | Pause or resume |
| R | Restart |

The game window also includes Restart, Pause, GitHub source-code and WeChat public-account buttons.

## Online leaderboard (1.4.1)

- Shared worldwide top five: nickname, personal-best score and country.
- No login or typing: a nickname is generated automatically and retained in the QGIS user's settings. Different installations/settings profiles are different players; this does not identify real people.
- The compact, borderless top five shows abbreviated nicknames, exact scores and two-letter country codes. Hover over a value for its full text; abbreviation does not change the stored nickname.
- Country is estimated by Cloudflare from the connection IP, never selected or submitted by the player. VPNs/proxies affect the estimate. Unknown locations display `—` with an `Unknown` tooltip.
- Each finished game is submitted once. Restarting or closing also saves a played round; unopened/untouched rounds do not count. The best score per player is retained; ties favor the earlier received best.
- Requests are asynchronous. Offline play is always possible. Up to 100 recent unsent results are kept for retry while the game window is open (or next time it opens).
- Right-click **WORLD TOP 5** or the leaderboard to refresh or disable **Online ranking**. Disabling it stops future requests and clears the unsent queue, without removing existing online records. Hover over the title to see connection status and your full nickname/personal best.
- **Privacy** in the leaderboard's right-click menu explains the data sharing. See [PRIVACY.md](PRIVACY.md) for the full notice.

The leaderboard is recreational: basic score validation, idempotency and rate limiting reduce accidental duplicates and simple abuse, but an open-source, account-free client cannot provide cheat-proof scores or one-person-one-account enforcement.

The public service is hosted at https://tetrisgame-leaderboard.gaojunke2020.workers.dev. Source and maintenance instructions are in [leaderboard-service](https://github.com/gaojunke/TetrisGame/tree/main/leaderboard-service). The service is not run by QGIS.

## Compatibility and dependencies

- QGIS 4.0–4.99
- Python bindings provided by QGIS
- No external Python dependencies

## License

This plugin is licensed under [GPL-3.0-or-later](LICENSE).
