# iptv-ru-ua

**Self-healing Russian & Ukrainian IPTV playlist** — live M3U for SS IPTV (LG webOS) and any HLS player, kept alive automatically, no maintenance, no laptop required.

[![Playlist Doctor](https://github.com/Adam-ZS/iptv-ru-ua/actions/workflows/doctor.yml/badge.svg)](https://github.com/Adam-ZS/iptv-ru-ua/actions/workflows/doctor.yml)
![Last commit](https://img.shields.io/github/last-commit/Adam-ZS/iptv-ru-ua)
![Repo size](https://img.shields.io/github/repo-size/Adam-ZS/iptv-ru-ua)
![License](https://img.shields.io/github/license/Adam-ZS/iptv-ru-ua)

---

## The problem

Free RU/UA playlists rot. Links die by the dozen every month:

- official CDN streams ship **expiring `md5` tokens** (`?md5=...&e=UNIX_EPOCH`) — the link is a corpse the moment the token lapses
- pirate mirrors drop, geo-block, or rate-limit
- you hand-fix the list, it dies again, repeat forever

## The solution — a playlist that heals itself

`playlist.m3u` in this repo is **not a static file**. A headless doctor bots it:

1. **Probes every channel** every run (playlist + a real video segment, parallel)
2. **Swaps dead channels** to verified replacements from a curated reservoir
3. **Discovers fresh sources** — re-pulls [iptv-org](https://github.com/iptv-org/iptv) country lists each run and re-tests
4. **Pushes the fix** automatically

It runs on **GitHub Actions 4× a day** (03:17 / 09:17 / 15:17 / 21:17 UTC) — always on, free, no server of yours involved.

Channel titles are **stable**: the naming and order never shuffle; only the URL behind each name is replaced when needed.

## Quick start

Point any IPTV player that accepts an external M3U at:

```
https://raw.githubusercontent.com/Adam-ZS/iptv-ru-ua/main/playlist.m3u
```

### SS IPTV (LG webOS)

1. Open SS IPTV → Settings → **External playlists**
2. **Add** & paste the raw URL above
3. Open the new playlist. Done.

The app re-fetches at every launch, so repairs arrive on their own.

### Any other player

VLC, Kodi, Jellyfin, TiviMate, etc. — same URL, load it as a playlist/remote M3U.

**Mirror (cache-friendly):** `https://cdn.jsdelivr.net/gh/Adam-ZS/iptv-ru-ua@main/playlist.m3u`

---

## What's inside

- **RU majors**: Первый канал / ОРТ, Россия 1, Россия 24, НТВ, СТС, ТНТ, ТВ3, ТВ Центр, 5 канал, Мир / Мир 24, 360°, Мульт, RTД, RU TV, Точка ТВ, Москва 24*
- **UA**: 1+1, Марафон, Интер (Inter), НТН, 24 канал, Freedom (plus YouTube-based live feeds)
- *indicates channels with **no working public source** at the moment — the doctor rehunts them every run, and they re-join automatically the moment a source appears.

Channel names and order are preserved across repairs — your TV list doesn't reshuffle.

---

## How it works

```
cron (GH Actions, 4×daily)
        │
        ▼
┌─────────────────────┐
│  doctor.py          │
│  ┌───────────────┐  │
│  │ probe ALL     │  │  parallel, 8s timeout, playlist+segment
│  │ channels      │  │
│  └──────┬────────┘  │
│         │ dead?     │
│         ▼           │
│  ┌───────────────┐  │
│  │ curated       │  │  reservoir of verified mirrors
│  │ reservoir     │  │  (geo-tested from UAE: 31.148.48.15 farm,
│  └──────┬────────┘  │   cdn.ntv.ru, live-tv.cloud — Referer-aware)
│         │ still?    │
│         ▼           │
│  ┌───────────────┐  │
│  │ runtime       │  │  re-pull iptv-org ru/ua, match by name,
│  │ discovery     │  │  probe, swap the first alive
│  └──────┬────────┘  │
│         ▼           │
│  write playlist.m3u │  titles/order preserved
│  git commit + push  │  rebase-safe (multi-scheduler)
└─────────────────────┘
        │
        ▼
playlist.m3u → raw.githubusercontent → your TV / player
```

**Referer-gated CDNs** (31.148.48.15, cdn.ntv.ru, vnet.am, macc.com.ua) are probed with the correct `Referer` header — many "dead" mirrors are just picky.

---

## Development & contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) — new channel sources, caveats, and the do's/don'ts (no tokens with `?e=` expiries, no geo-only sources, always a segment-probe proof).

- [Issue templates](.github/ISSUE_TEMPLATE/) — report a dead channel, a bug, or a feature
- [Security policy](SECURITY.md) — responsible disclosure
- [Code of conduct](CODE_OF_CONDUCT.md) — the rules of the road

---

## License

[MIT](LICENSE) © 2026 iptv-ru-ua contributors. Channel links remain the property of their respective broadcasters/aggregators; this project only aggregates publicly reachable streams.