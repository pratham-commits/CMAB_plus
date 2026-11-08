# Review II raw data (per-run JSON)

Full session trees are **not** copied into `review-2/` (160 runs × ~15 JSON files each ≈ hundreds of MB).

## Canonical BBR clock matrix (160 × 300 s)

**In repo:**

`review-ii-bbr-extension/deliverables/bbr-clock-160-deliverable-20261018-0535/figures/emulation-bbr-clock/`

Layout (same as Review I):

```text
emulation-bbr-clock/
  target-3s/
    abrCMAB-1017-0606-target-latency-3s-duration-300-bitrate-variable-0/
      playback_latency.json
      buffer.json
      bitrates.json
      arms.json
      …
  target-4s/ … target-6s/
```

## Review I CUBIC (baseline)

`~/BITS/ACN/Project/review 1/mmsys24-starlink-livestreaming/figures/emulation/`

Prefix: **0929-1424** (Review I batch).

## Superseded BBR trace matrix (do not use for primary claims)

`review-ii-bbr-extension/figures/emulation-bbr/` — prefix **1010-0432**, `SHAPER=trace`.

## Deliverable tarball

`~/Downloads/bbr-clock-160-deliverable-20261018-0535.tar.gz` includes `figures/`, `meta/`, `docker-logs/`.

## Session name regex (for scripts)

```text
^(abr\w+)-\d+-(\d+)-target-latency-(\d+)s-duration-(\d+)-bitrate-variable-(\d+)$
```

Aggregation uses **duration=300** only (60 s smoke runs excluded).
