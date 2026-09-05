# Online leaderboard privacy notice

Version 1.4.0 · 2026-09-05

Operator: 高科科 (Gao Keke), contact **996517087@qq.com** / QQ 996517087.

## What is sent and why

When **Online ranking** is enabled (the default), opening the game connects over HTTPS to `tetrisgame-leaderboard.gaojunke2020.workers.dev`, operated on Cloudflare Workers and D1. No account login or real name is requested. A cryptographically random installation token is stored in your QGIS user settings and sent as an HTTPS authorization header. It links your results to a stable, automatically generated nickname. The database stores only its SHA-256 digest, not the token itself. Do not share your QGIS settings/token with others.

After a played round ends, restarts or closes, the plugin submits a random event identifier, score, cleared lines, placed pieces and elapsed time. Lines/pieces/time are used to check the plausibility of scores; the database retains the nickname, token digest, event identifiers, submitted scores, country, timestamps and total accepted rounds. Your highest score determines your rank. No projects, layer data, files, map coordinates, machine name, email address or QGIS account details are sent.

Cloudflare processes the connecting IP as part of providing the HTTPS service and estimates its country. The Worker uses trusted country metadata, not a field provided by the plugin. The application database does **not** retain the IP address. IPs are used transiently by Cloudflare's request limiter; invocation logging is disabled, and the Worker logs only a fixed generic failure message. Cloudflare may process network/security metadata under its own [privacy policy](https://www.cloudflare.com/privacypolicy/). Data may be processed outside your country; no specific residency is guaranteed.

Country is an approximate connection location, **not nationality**. VPNs, proxies and mobile networks can affect it. Unrecognized locations are shown as Unknown. A leaderboard entry uses the country when its best result was received, including when an offline result is uploaded later.

## What is public, and how long it is kept

Only the top five generated nicknames, best scores and countries are returned by the public leaderboard endpoint. Your own profile response also includes your accepted-round count. Neither authentication tokens nor their hashes are included in public ranking responses. Other players' full game histories are not exposed.

Online records remain until the operator removes them or the service is retired; there is no automatic expiry in this version. Request removal by contacting the operator with your generated nickname. Technical users can also delete their own record using the authenticated `DELETE /v1/player` endpoint; do not include tokens in public support messages. Disable ranking and clear pending results before requesting deletion, otherwise a later submitted result can create the record again. Provider backups may temporarily retain removed records according to Cloudflare's retention settings.

## Your choices

Disable **Online ranking** in the game to stop future leaderboard requests and discard unsent results. This does not delete scores already received by the server. The game remains playable offline. A previously downloaded leaderboard may remain visible as cached data, with its status shown. Local settings retain your token, nickname and cached top five; up to 100 recent unsent rounds are queued for retry (older unsent rounds are dropped if that limit is exceeded). Removing the local settings loses that anonymous identity, but does not remove online records.

GitHub and WeChat are contacted only when their buttons are clicked. They open in your system browser and follow their own privacy policies. The plugin has no advertising or analytics SDK and sends no crash reports.

## 中文摘要

默认开启在线排行，无需登录，昵称自动生成并保存在当前 QGIS 用户配置中。国家由 Cloudflare 根据连接 IP 估算，不代表国籍；代理/VPN 会影响结果。游戏成绩及基础局次统计经 HTTPS 发送给作者的 Cloudflare 服务，数据库不保存原始 IP，也不读取或上传 QGIS 项目和图层。

榜单公开前五名的昵称、最高分和国家。同一配置使用同一昵称，不等同于真人身份认证。每次玩过的对局在结束、重开或关闭时记分；断网最多暂存最近 100 局，重新打开游戏后补传。关闭“Online ranking”可停止后续联网并清除待传成绩；已上传的数据需联系作者删除。点“Privacy”可随时查看说明。
