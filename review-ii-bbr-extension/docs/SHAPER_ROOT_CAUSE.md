# Shaper / nginx root cause (Oct 2026 validation)

## Symptoms

- Review I CMAB @ CUBIC: ~3.2 s latency, ~848 `arms.json` samples, mixed ladder.
- Validation CMAB @ CUBIC (patched stack): ~16.6 s, 28 arms, all arm 7, ~86% rebuffer.
- Dynamic @ CUBIC on same validation: ~4.3 s, low rebuffer (stack path OK at low bitrate).

## Root causes (ranked)

### 1. `docker restart` + broken `tc_init` (fixed)

`batch_runner` calls `restart_nginx()` before **every** 300 s run. Docker **restart** keeps the **network namespace** and existing `tc` rules.

Old `tc-trace.py`:

- Never added root `htb` qdisc (`tc qdisc add dev eth0 root handle 1: htb`).
- `tc_init()` used `tc class add` only; on restart, **class already exists** → Python crash → supervisord restart loop → trace **stops updating** or shaper ends up stuck (often during trace `rtt=0` → **100% loss**).

**Fix:** `tc_del()` then full HTB + class + netem in `runner/tc-trace.py`; recover with `tc_init()` if `tc change` fails.

### 2. Local nginx image rebuild vs Review I pull

Compose sets `image: clarkzjw/dashjs-nginx:emulation` **and** `build:`. After BBR work you **rebuilt** nginx with `entrypoint.sh` + `set-tcp-cc.sh`. Review I may have used the **pulled** Hub image (older layer, possibly different supervisord / tc behavior).

Always record: `docker inspect dashjs-nginx --format '{{.Id}} {{.Created}}'`.

### 3. CMAB vs Dynamic under trace shaper

`tc-trace` applies **~180 ms** netem delay from `isl-trace.csv` and **100% loss** on trace zeros (handover). **abrCMAB** at **6000 kbps** is far more sensitive than **abrDynamic** at ~400 kbps. That explains “Dynamic OK, CMAB dead” even when CC is `cubic`.

Review I numbers are still valid **for the Sept stack snapshot**; Oct validation is **not** a replacement CUBIC baseline until the shaper fix is deployed and a CMAB rerun matches ~800+ arms.

## What to rerun after fix

1. Rebuild nginx on VM (see below).
2. `./review-ii-bbr-extension/scripts/verify_nginx_shaper.sh`
3. One CMAB @ CUBIC, 300 s — expect **>200** arm logs and mean latency **~3–4 s** class.
4. Optional: full 4-run validation (CUBIC/BBR × CMAB/Dynamic).

## BBR 160-run matrix

Runs used the same `restart_nginx` + old `tc-trace`. After fix, **BBR vs Dynamic comparisons on the same commit** remain interpretable; **absolute** latency vs Review I CUBIC still needs a rerun or explicit limitation (RC7).

## CMAB still bad after tc-trace restart fix (Oct 17 0438 run)

If CMAB still shows ~30 arm logs, all arm 7, ~15 s latency while Dynamic ~4 s, the shaper **mode** is wrong for Review I parity:

| Mode | Process | Baseline delay | Review I (848 arms) |
|------|---------|----------------|---------------------|
| `SHAPER=trace` | `tc-trace.py` | ~180 ms from CSV + 100% loss on trace zeros | Unlikely Sept baseline |
| `SHAPER=clock` | `tc.py` | ~40 ms + handover at 12/27/42/57 s | **Match this first** |

Set on nginx: `SHAPER=clock`, rebuild nginx, rerun one CMAB @ CUBIC 300 s.

## Optional: softer handover loss

Upstream uses **100%** loss for trace `rtt=0`. Clock-based `tc.py` uses **~1%** at seconds 12/27/42/57. To experiment (may shift BBR numbers):

```yaml
environment:
  - HANDOVER_LOSS_PERCENT=1
```

Default remains `100` for upstream parity.
