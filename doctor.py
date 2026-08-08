#!/usr/bin/env python3
"""
iptv-ru-ua doctor — self-healing playlist keeper.

1. probe every channel (playlist + first segment, parallel)
2. dead ones -> slot lookup -> probe curated reservoir -> swap first alive
3. still broken -> runtime discovery: re-pull iptv-org (ru+ua), re-match, re-probe
4. write playlist.m3u (titles & order preserved) + doctor_report.json
5. git commit + push (only when changed)

Run from cron every 6h. Stdlib only; proxy env stripped internally.
"""
import json, os, re, ssl, subprocess, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin

BASE = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE)
for var in ("ALL_PROXY", "HTTPS_PROXY", "HTTP_PROXY", "all_proxy", "https_proxy", "http_proxy"):
    os.environ.pop(var, None)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE
TIMEOUT = 8
IPG_RU = "https://iptv-org.github.io/iptv/countries/ru.m3u"
IPG_UA = "https://iptv-org.github.io/iptv/countries/ua.m3u"

# some CDNs (31.148.48.15 farm, cdn.ntv.ru, vnet.am) gate streams on Referer
REFERERS = {
    "31.148.48.15": "http://31.148.48.15/",
    "cdn.ntv.ru": "https://www.ntv.ru/",
    "vnet.am": "https://www.vnet.am/",
    "bonus-tv.ru": "https://bonus-tv.ru/",
    "macc.com.ua": "http://macc.com.ua/",
}

# his exact playlist titles -> healing slot. None = leave as-is (youtube/udp/rtmp/other)
SLOT_OF = {
    "Первый канал": "Первый канал", "Первый": "Первый канал", "ORT": "Первый канал",
    "Россия 1": "Россия 1", "Россия 1 HD": "Россия 1", "Россия 11": "Россия 1",
    "Russia 24": "Россия 24",
    "НТВ": "НТВ", "НТВ Mir": "НТВ", "НТВ Мир": "НТВ Мир",
    "НТВ Сериал": "НТВ Сериал", "НТВ Стиль": "НТВ Стиль",
    "СТС": "СТС", "СТС Kids": "СТС Kids", "СТС Love": "СТС Love",
    "ТНТ": "ТНТ", "ТНТ4 (480p)": "ТНТ4", "ТНТ MUSIC": "ТНТ MUSIC",
    "ТВ3": "ТВ3", "ТВ Центр": "ТВ Центр",
    "5 канал": "5 канал",
    "Мир 24 (1080p)": "Мир 24", "Мир (1080p)": "Мир",
    "Москва 24": "Москва 24", "360°": "360°",
    "Муз ТВ": "Муз ТВ", "Мульт": "Мульт",
    "RTД": "RTД", "RU TV": "RU TV", "Россия-К": "Россия К",
    "Точка ТВ": "Точка ТВ", "Русский Бестселлер": "Русский Бестселлер",
    "Первый космический": "Первый космический",
    "1+1": "1+1", "1+1 Maraphon": "1+1 Maraphon",
    "Inter+": "Интер+", "К1 (576p)": "К1", "НТН (576p)": "НТН",
    "24 канал": "24 канал", "IHTEP": "Интер",
    "TBN": "TBN",
}

SLOTS = {
    "Первый канал":    [r"первый канал", r"^первый\b", r"\b1tv\b", r"\bORT\b"],
    "Россия 1":        [r"россия 1", r"russia 1", r"rossiya 1"],
    "Россия 24":       [r"россия 24", r"russia 24", r"rossiya 24"],
    "НТВ":             [r"^нтв\b(?! мир)", r"\bntv\b"],
    "НТВ Мир":         [r"нтв мир"],
    "НТВ Сериал":      [r"нтв сериал"],
    "НТВ Стиль":       [r"нтв стиль"],
    "СТС":             [r"^стс\b(?! (kids|love))", r"\bsts\b(?! (kids|love))"],
    "СТС Kids":        [r"стс kids", r"стс кидс"],
    "СТС Love":        [r"стс love", r"стс лав"],
    "ТНТ":             [r"^тнт\b(?!4)", r"\btnt\b(?!4)"],
    "ТНТ4":            [r"тнт4"],
    "ТНТ MUSIC":       [r"тнт music", r"тнт муз"],
    "ТВ3":             [r"^тв3\b", r"\btv3\b"],
    "ТВ Центр":        [r"тв центр"],
    "5 канал":         [r"^5 канал", r"пятый канал"],
    "Мир 24":          [r"мир 24"],
    "Мир":             [r"^мир\b(?!24)"],
    "Москва 24":       [r"москва 24", r"moscow 24"],
    "360°":            [r"^360"],
    "Муз ТВ":          [r"муз тв", r"muz tv", r"муз-тв"],
    "Мульт":           [r"мульт\b"],
    "RTД":             [r"rtд", r"rt doc", r"rtdoc"],
    "Россия К":        [r"россия[ -]?к\b", r"russia k\b", r"культура"],
    "Точка ТВ":        [r"точка тв"],
    "Первый космический": [r"первый космич", r"еврик"],
    "Русский Бестселлер": [r"бестселлер"],
    "1+1":             [r"^1\+1\b", r"1plus1\b"],
    "1+1 Maraphon":    [r"1\+1 марафон", r"maraf"],
    "Интер":           [r"^і?нтер\b", r"^inter\b"],
    "К1":              [r"^к1\b", r"^k1\b"],
    "НТН":             [r"^нтн\b", r"^ntn\b"],
    "24 канал":        [r"^24 канал"],
    "TBN":          [r"\btbn\b"],
}

# verified-winner reservoir (probed ALIVE from the user's IP on 2026-08-08)
RESERVOIR = {
    "Первый канал": [
        "http://31.148.48.15/Pervii_kanal_HD/index.m3u8",
        "https://streaming.televizor-24-tochka.ru/live/210.m3u8",
    ],
    "Россия 1": [
        "http://31.148.48.15/Rossiya_1/index.m3u8",
        "https://live.chechensoft.ru/vainahtv/ngrp:vaynahtv_all/playlist.m3u8",
    ],
    "Россия 24": [
        "http://31.148.48.15/Rossiya_24/index.m3u8",
        "https://vgtrkregion-reg.cdnvideo.ru/vgtrk/habarovsk/russia24-sd/index.m3u8",
    ],
    "НТВ": [
        "http://31.148.48.15/NTV/index.m3u8",
        "https://cdn.ntv.ru/ntv1/playlist.m3u8",
        "https://cdn.ntv.ru/ntv2/playlist.m3u8",
    ],
    "НТВ Мир": ["https://streaming.televizor-24-tochka.ru/live/213.m3u8"],
    "НТВ Сериал": ["https://cdn.ntv.ru/th_serial/playlist.m3u8"],
    "НТВ Стиль": ["https://cdn.ntv.ru/th_hit/playlist.m3u8"],
    "СТС": [
            "https://zabava-htlive.cdn.ngenix.net/hls/CH_STS/variant.m3u8",
            "http://tshift-1.telecoma.tv/sts/index.m3u8",
        ],
    "СТС Love": ["http://31.148.48.15/STS_Love/index.m3u8"],
    "ТНТ": [
        "http://s18209.cdn.ngenix.net/hls/CH_R01_TNT/playlist.m3u8",
        "http://45.153.24.78:80/TNT/index.m3u8",
    ],
    "ТНТ4": ["http://31.148.48.15/TNT4/index.m3u8"],
    "5 канал": ["https://zabava-htlive.cdn.ngenix.net/hls/CH_5TV/variant.m3u8"],
    "Мир 24": ["http://hls.mirtv.cdnvideo.ru/mirtv-parampublish/mir24_2500/playlist.m3u8"],
    "Мир": [
        "http://hls.mirtv.cdnvideo.ru/mirtv-parampublish/mirtv_2500/playlist.m3u8",
        "http://31.148.48.15/Mir/index.m3u8",
    ],
    "360°": ["https://live-vgtrksmotrim.cdnvideo.ru/vgtrksmotrim/smotrim-live-04-srt.smil/playlist.m3u8"],
    "Мульт": ["http://31.148.48.15/Mult_HD/index.m3u8"],
    "RTД": ["https://rt-doc.rttv.com/dvr/rtdru/playlist.m3u8"],
    "Россия К": ["http://31.148.48.15/Kultura/index.m3u8"],
    "RU TV": ["http://31.148.48.15/RU_TV/index.m3u8"],
    "Точка ТВ": ["http://31.148.48.15/Tochka_TV/index.m3u8"],
    "Русский Бестселлер": ["http://31.148.48.15/Russkiy_Bestseller/index.m3u8"],
    "1+1 Maraphon": ["https://dash2.antik.sk/live/1plus1_marathon/playlist.m3u8"],
    "Интер": ["https://cdn15.live-tv.cloud/ua_infinitas_tv/inter-abr/playlist.m3u8"],
    "Интер+": ["https://cdn15.live-tv.cloud/ua_infinitas_tv/inter-abr/playlist.m3u8"],
    "НТН": ["https://cdn15.live-tv.cloud/ua_infinitas_tv/ntn-abr/playlist.m3u8"],
    "24 канал": ["https://cdn15.live-tv.cloud/ua_infinitas_tv/news24-abr/playlist.m3u8"],
}

def fetch_url(url, max_bytes=65536, ua=UA):
    hdrs = {"User-Agent": ua}
    for host, ref in REFERERS.items():
        if host in url:
            hdrs["Referer"] = ref
            break
    req = urllib.request.Request(url, headers=hdrs)
    with urllib.request.urlopen(req, timeout=TIMEOUT, context=CTX) as r:
        return r.status, r.read(max_bytes)

def probe_url(url):
    url = url.strip()
    low = url.lower()
    if low.startswith(("udp://", "rtmp://", "rtmps://")) or "youtube.com" in url or "youtu.be" in url or "ok.ru" in url:
        return False, "unsupported/skip"
    m = re.search(r"[?&]e=(\d+)", url)
    if m and int(m.group(1)) < time.time():
        return False, "expired-token"
    try:
        code, body = fetch_url(url)
        if code != 200 or b"#EXT" not in body:
            return False, f"http{code}"
        seg = next((urljoin(url, l.strip()) for l in body.decode("utf-8", "ignore").splitlines()
                    if l.strip() and not l.strip().startswith("#")), None)
        if seg:
            scode, sbody = fetch_url(seg, 4096)
            if scode != 200 or len(sbody) < 100:
                return False, f"http{code}/seg"
        return True, ""
    except Exception as e:
        return False, type(e).__name__

def parse_m3u(path):
    chans, cur = [], None
    for line in open(path, encoding="utf-8", errors="ignore"):
        line = line.strip()
        if line.startswith("#EXTINF"):
            m = re.search(r'tvg-name="([^"]*)"', line)
            title = m.group(1) if m else line.split(",", 1)[-1]
            cur = {"title": title, "url": None}
        elif line and not line.startswith("#") and cur:
            cur["url"] = line
            chans.append(cur); cur = None
    return chans

def main():
    chans = parse_m3u("playlist.m3u")
    report = []

    # dedupe identical (title, url) — keep first occurrence
    seen, deduped = set(), []
    for c in chans:
        key = (c["title"], c["url"])
        if key in seen:
            report.append(f"DROP dup: {c['title']}")
            continue
        seen.add(key); deduped.append(c)
    chans = deduped

    # parallel probe of current state
    with ThreadPoolExecutor(max_workers=20) as ex:
        futs = {ex.submit(probe_url, c["url"]): c for c in chans}
        results = {id(futs[f]): f.result() for f in as_completed(futs)}
    alive_n = sum(1 for v in results.values() if v[0])
    print(f"[*] baseline: {alive_n}/{len(chans)} alive")

    # phase 2 — curated reservoir swap for dead channels
    still_broken = {}
    for c in chans:
        ok, why = results[id(c)]
        if ok:
            continue
        slot = SLOT_OF.get(c["title"])
        if slot is None:
            report.append(f"LEAVE  : {c['title']} ({why}) — no slot (yt/unsupported)")
            continue
        fixed = False
        for cand in RESERVOIR.get(slot, []):
            if cand == c["url"]:
                continue
            okc, _ = probe_url(cand)
            if okc:
                c["url"] = cand
                report.append(f"SWAP   : {c['title']}  ->  {cand}")
                fixed = True
                break
        if not fixed:
            still_broken[c["title"]] = slot

    # phase 3: runtime discovery via iptv-org (only for still-broken slots)
    if still_broken:
        print(f"[*] runtime discovery for {len(still_broken)} slots...")
        for f, u in (("ru.m3u", IPG_RU), ("ua.m3u", IPG_UA)):
            try:
                req = urllib.request.Request(u, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=TIMEOUT, context=CTX) as r:
                    open(os.path.join("sources", f), "wb").write(r.read())
            except Exception:
                pass
        pool = parse_m3u("sources/ru.m3u") + parse_m3u("sources/ua.m3u")
        for title, slot in still_broken.items():
            pats = SLOTS.get(slot, [])
            cands = list(dict.fromkeys(c["url"] for c in pool
                        if any(re.search(p, c["title"], re.I) for p in pats)))[:10]
            for cand in cands:
                okc, _ = probe_url(cand)
                if okc:
                    for c in chans:
                        if c["title"] == title:
                            c["url"] = cand
                            report.append(f"RUNTIME: {title}  ->  {cand}")
                            break
                    RESERVOIR.setdefault(slot, []).insert(0, cand)
                    break
            else:
                report.append(f"STILL DEAD: {title} ({slot}) — no source found this run")

    # final probe + write
    with ThreadPoolExecutor(max_workers=20) as ex:
        futs = {ex.submit(probe_url, c["url"]): c for c in chans}
        final = {id(futs[f]): f.result() for f in as_completed(futs)}
    alive_fin = sum(1 for v in final.values() if v[0])
    with open("playlist.m3u", "w", encoding="utf-8") as fh:
        fh.write("#EXTM3U\n")
        for c in chans:
            fh.write(f'#EXTINF:-1 tvg-name="{c["title"]}",{c["title"]}\n{c["url"]}\n')

    summary = f"doctor run {time.strftime('%Y-%m-%d %H:%M')} — baseline {alive_n}/{len(chans)} alive -> final {alive_fin}/{len(chans)} alive"
    print(f"[=] {summary}")
    for line in report:
        print("     " + line)
    json.dump({"summary": summary, "report": report}, open("doctor_report.json", "w"),
              ensure_ascii=False, indent=1)

    # git push if changed (rebase first so laptop cron + GH Actions never collide)
    changed = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.strip()
    if changed:
        subprocess.run(["git", "add", "-A"], check=True)
        msg = f"docs: {summary} | swaps: {sum(1 for l in report if l.startswith('SWAP'))}"
        subprocess.run(["git", "commit", "-m", msg], check=True, capture_output=True)
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], capture_output=True, text=True)
        p = subprocess.run(["git", "push"], capture_output=True, text=True)
        print(f"[+] pushed: {msg}" if p.returncode == 0 else f"[!] push failed: {p.stderr[-200:]}")
    else:
        print("[+] nothing changed, no push")

if __name__ == "__main__":
    main()