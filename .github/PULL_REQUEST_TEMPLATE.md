## What does this PR change?

- [ ] Channel added / URL fixed
- [ ] doctor.py logic
- [ ] Workflow / CI
- [ ] Docs

## Channel changes checklist

- [ ] Source is publicly reachable (no credentials, no paid rips)
- [ ] No expiring tokens (`?md5=...&e=...`) in the URL
- [ ] Tested the *segment*, not just an HTTP 200
- [ ] Tested from outside the source country, or geo caveat noted
- [ ] Probe proof pasted below

```
curl -s -o /dev/null -w '%{http_code}' "<url>"          # must be 200
<first-segment check too>
```

## Fixing the doctor / workflow?

- [ ] Stdlib-only (runner has no third-party deps)
- [ ] Timeout ≤ 8s, parallelism ≤ 20
- [ ] Referer hosts added to `REFERERS`, not inlined
- [ ] Ran `python3 doctor.py`; state the kept/removed counts