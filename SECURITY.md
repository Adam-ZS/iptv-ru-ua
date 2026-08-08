# Security Policy

## Supported versions

| Version | Supported |
| ------- | --------- |
| `main`  | ✅        |

The playlist is live-maintained; only the `main` branch is meaningful.

## Chipsets at risk — what we take seriously

- **Credential material** (tokens, keys, `?e=` expiries, URLs with embedded
  credentials) — never expected here; if you find one, it's a bug.
- **Playlist poisoning** — a submitted source that is actually malformed,
  malicious, or payload-serving (e.g. an HLS playlist pointing at non-media
  content, or a redirect harvesting IP addresses).
- **Doctor failures** — a broken probe loop or an infinite swap that floods
  the repo with bad commits.

## Reporting a vulnerability

**Do not open a public issue for security findings.**

Report privately instead:

1. Open a **private security advisory**:
   https://github.com/Adam-ZS/iptv-ru-ua/security/advisories/new
2. Or email the maintainers (address found via the repo's About page →
   "Manage email").

Please include:
- the affected file / URL
- a minimal reproduction
- impact assessment

We aim to acknowledge reports within **5 days** and release a fix on `main`
promptly; then the doctor picks it up automatically and the playlist is clean.

## Disclosure policy

We practice **coordinated disclosure** — no public info until a fix is on
`main`. Credit goes to reporters in the fix commit unless they opt out.