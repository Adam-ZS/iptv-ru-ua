# Contributing to iptv-ru-ua

Thanks for wanting to make this playlist better and more resilient. Every
channel added here has to survive the same doctor probe that watches it,
or it becomes noise for the people watching TV.

## Ground rules

1. **Playlists are public data.** Only submit sources that are already
   publicly reachable (free HLS streams, official or open mirrors). No
   paid-subscription rips, no credentials anywhere.
2. **No expiring tokens.** Streams with `?md5=...&e=<epoch>` die on a
   schedule — they are the reason this project exists. Don't add them.
3. **No geo-only sources.** A URL that only plays inside one country is a
   bug the next user discovers. When in doubt, prefer mirrors tested
   outside the source country.
4. **Segment-prove it.** A 200 HTTP response means nothing — include the
   result of a segment fetch (the doctor does `playlist + first segment`).

## How to contribute a channel

1. **Probe** the candidate exactly like the doctor does:

   ```bash
   # playlist must return #EXTM3U
   curl -s -m 8 -o /dev/null -w '%{http_code}\n' -A 'Mozilla/5.0' "$URL"

   # first segment must be fetchable and >100 bytes
   curl -s -m 8 "$URL" | grep -oE '^[^#].*' | head -1 | \
     xargs -I{} curl -s -m 8 -o /dev/null -w '%{http_code}\n' "$(dirname "$URL")/{}"
   # both must be 200
   ```

2. **Open an issue** using the *Dead channel / suggestion* template:
   - channel name
   - working URL (with proof: the two 200s)
   - region you tested from
   - referer/user-agent required, if any

3. A maintainer adds it to the **reservoir** (the strictly-verified list the
   doctor prefers before runtime discovery) or adds a slot + regex so the
   doctor can discover it automatically.

## Editing the playlist directly (pull requests welcome)

- Keep `#EXTINF` titles verbatim from the existing style — titles are the
  stable contract for viewers.
- `tvg-name` must match the visible title.
- One channel, one URL, no duplicates — the doctor de-dupes but please don't
  make it work for a fish.
- Order matters: keep the grouping (RU first, then UA, then other) and don't
  shuffle existing entries; changing the ordering breaks people's muscle memory
  on remote for nothing.

## Reporting broken channels

The doctor self-heals every 6 hours. Before opening an issue, check the
[latest doctor run](https://github.com/Adam-ZS/iptv-ru-ua/actions) — the
channel you're about to report may already be flagged and scheduled.

If it's been dead for a while and it matters to you: open the
[Dead channel issue](.github/ISSUE_TEMPLATE/02_dead_channel.yml) with a
replacement URL if you have one.

## Coding the doctor

- **Stdlib only** (repo runs on GitHub Actions runners; no third-party deps
  by design).
- Probe timeouts: 8s. Parallelism: 20 workers. Stay within that budget.
- The reservoir is **UAE-verified**: new entries must include evidence of a
  successful probe from a UAE IP (or note the geo so it's checked by others).
- Referer-gated hosts belong in the `REFERERS` map, not as a one-off flag.

## Conventions

- Commit style: `docs: doctor run <date> — baseline N/M -> final N/M` for
  automated runs; descriptive subjects for manual changes.
- Rebases pull before push — the doctor and GitHub Actions both commit; keep
  history linear.
- Never commit large binaries; the repo is a text/data home.