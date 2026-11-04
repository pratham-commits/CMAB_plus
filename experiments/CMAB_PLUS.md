# CMAB+ (hardened abrCMAB)

Same LinTS CMAB. Three extra guards, off unless `cmabHardened=true`:

1. After each 15 s handover slot, the probe target is the highest rung at or below safe throughput, not the top of the ladder.
2. After that window, LinTS still cannot exceed safe throughput (`getSafeAverageThroughput`, already × 0.9).
3. When the quality already playing is faster than measured throughput, the rung steps down one and cannot rise on that decision. Otherwise the throughput-clamped suggestion is used. Latency sitting a little over the target is not a cut.
4. Switch priority is DEFAULT only for an upward switch that was cut down to safe throughput. A downward switch stays STRONG.

Trial notes: `experiments/CMAB_PLUS_TRIALS.md`.

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

## GCP — capacity decision, 15 sessions per speed

Old CMAB, CMAB+, and L2A, 3 s target, 5 rounds. Speeds are 8, then 4, then 1 Mbit. About 4 hours per congestion control. Do not run CUBIC and BBR at the same time.

```bash
cd ~/mmsys24-starlink-livestreaming
chmod +x experiments/run-capacity-decision.sh
./experiments/run-capacity-decision.sh cubic
# after it finishes:
./experiments/run-capacity-decision.sh bbr
```

One speed only: `./experiments/run-capacity-decision.sh cubic 4`.

The script refuses to start a speed unless nginx is `SHAPER=clock` at that rate. Runner `CMAB_HARDENED` must be `0`. Old CMAB URLs have no `cmabHardened=true`. CMAB+ URLs do, and their folders are named `abrCMABPlus-...`. Figures land in `figures/emulation-capacity-<cc>-<rate>mbit/`. Each speed is done when the log says `Video Streaming completed` and that folder has 15 `playback_latency.json` files.

## GCP — clock non-regression, targets 3/4/5/6 s

Paper clock (100 Mbit normal, 50 Mbit handover). Old CMAB, CMAB+, L2A. Five rounds per cell. 60 sessions per congestion control, about 5 hours of video. Do not run CUBIC and BBR at the same time.

```bash
cd ~/mmsys24-starlink-livestreaming
chmod +x experiments/run-clock-nonregression.sh
./experiments/run-clock-nonregression.sh cubic
# after it finishes:
./experiments/run-clock-nonregression.sh bbr
```

Figures: `figures/emulation-clock-nonreg-cubic/` and `figures/emulation-clock-nonreg-bbr/`. Expect 60 `playback_latency.json` files each. The script refuses to start unless nginx is `SHAPER=clock` at 100 Mbit with handover rate 50.
