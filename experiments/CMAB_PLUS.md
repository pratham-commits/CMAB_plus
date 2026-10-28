# CMAB+ (hardened abrCMAB)

Same LinTS CMAB. Three extra guards, off unless `cmabHardened=true`:

1. After each 15 s handover slot, the probe target is the highest rung at or below safe throughput, not the top of the ladder.
2. After that window, LinTS still cannot exceed safe throughput (`getSafeAverageThroughput`, already × 0.9).
3. Switch priority is DEFAULT (not STRONG) when the arm was clamped or buffer &lt; 0.5 s.

`CMAB_HARDENED=1` on the runner adds the URL flag only for `abrCMAB` jobs. L2A, LoLP, and Dynamic are unchanged.

Old Hub images do **not** contain this code. The 160-run script builds `Dockerfile-dashjs-local` and `Dockerfile-runner`.

## Desktop check (no Docker)

```bash
node experiments/test_cmab_plus_policy.mjs
```

## GCP — two full matrices, both SHAPER=clock

Sync this repo to `~/mmsys24-starlink-livestreaming`, then in tmux:

```bash
cd ~/mmsys24-starlink-livestreaming
chmod +x experiments/run-cmab-plus-160-clock.sh

# ~13 h each. Do not run both at once (one nginx, one chrome).
./experiments/run-cmab-plus-160-clock.sh bbr
# after it finishes:
./experiments/run-cmab-plus-160-clock.sh cubic
```

The script refuses to start unless nginx reports `SHAPER=clock`, the matching congestion control, and a `tbf` qdisc (`tc.py`, not the trace shaper).

Figures:

- `figures/emulation-cmab-plus-bbr/`
- `figures/emulation-cmab-plus-cubic/`

Confirm a CMAB session URL in `docker logs dashjs-runner` contains `cmabHardened=true`. QoE posts include `cmab_plus`, `clamped`, and `suggested_arm`.
