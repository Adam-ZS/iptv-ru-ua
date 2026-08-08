# iptv-ru-ua

Self-healing RU/UA playlist for SS IPTV (LG webOS).

`playlist.m3u` is maintained by a cron-driven health-check doctor (see doctor.py
in the local workspace). Dead channels are re-probed every run and swapped to
fresh verified sources automatically. Titles and order are preserved.

Points SS IPTV -> External Playlists -> this raw URL.