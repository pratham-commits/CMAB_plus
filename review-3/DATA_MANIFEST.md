# Data manifest

## Final clock matrix

- `data/archives/cmab-plus-cubic-1102-1304.tar.gz`
- SHA-256:
  `0652cda3862b6759a8bbd300ced771d9ec87c7461828a36a90bdc2319a561028`
- 160 sessions: four players × four targets × ten rounds.
- CUBIC, `SHAPER=clock`, rejected one-second latency-triggered step-down.

The retained normal-clock BBR trees and failed BBR trials are:

- `bbr-cmab-plus-1030-0137/`
- `bbr-cmab-plus-rerun/`
- `bbr-cmab-plus-stuck900/`

## Clock non-regression (current CMAB+ code)

### CUBIC

- Extracted: `data/clock-nonreg-cubic/`
- Archive: `data/archives/cmab-plus-clock-nonreg-cubic.tar.gz`
- SHA-256:
  `55716f33b860b4ba1f2c6b0fe4d3c8d3fdaa532d989062707c06ef7d9806f8f3`
- 60 sessions: three players × targets 3/4/5/6 s × five rounds.
- Paper clock (100 Mbit / 50 Mbit handover). Pass: CMAB+ tracks old CMAB.

### BBR

- Extracted: `data/clock-nonreg-bbr/`
- Archive: `data/archives/cmab-plus-clock-nonreg-bbr.tar.gz`
- SHA-256:
  `1b29c2ac41bde0f3c9b32fe817ee80d49acc3ef240c7fda9d021658fa7e41f5f`
- 60 sessions: three players × targets 3/4/5/6 s × five rounds.
- Paper clock. Pass: CMAB+ tracks old CMAB.

## 4 Mbit target robustness

### CUBIC

- Extracted: `data/capacity-4mbit-targets-cubic/`
- Archive: `data/archives/cmab-plus-capacity-4mbit-targets-cubic.tar.gz`
- SHA-256:
  `21b29deccba1f3f202351ce10b85184162ca8a46fd8afea1d664afcef3d1cef0`
- 60 sessions: three players × targets 3/4/5/6 s × five rounds.
- Fixed 4 Mbit. Pass: CMAB+ ~0% rebuffer / ~1.5 Mbps at every target;
  old CMAB stays at 6000 kbps with 72–81% rebuffer.

### BBR

- Extracted: `data/capacity-4mbit-targets-bbr/`
- Archive: `data/archives/cmab-plus-capacity-4mbit-targets-bbr.tar.gz`
- SHA-256:
  `0141ed96b2a282199a9824587c654c197fc496cc86005ed3de3ff8c77146bde7`
- 60 sessions: three players × targets 3/4/5/6 s × five rounds.
- Fixed 4 Mbit. Pass: same pattern as CUBIC (0% rebuffer, ~1475 kbps).

## Trace validity (final player: stall guard on)

Combined archive (canonical for the conference paper):

- Archive: `data/archives/cmab-plus-trace-stallguard-cubic-bbr-20261108.tar.gz`
- SHA-256:
  `27cdf2a5493e126a84390ac889dbc77933aab0f01ad96d4673e8adda97c20d0a`
- Extracted: `data/trace-targets-cubic/` and `data/trace-targets-bbr/`
- 120 sessions: two CCs × three players × targets 3/4/5/6 s × five rounds.
- `SHAPER=trace`. CMAB+ vs old CMAB at 3 s: CUBIC rebuffer ~81% → ~15%
  (851 kbps); BBR ~29% → ~8% (2658 kbps). L2A remains ~0.5–0.8% at
  ~300–450 kbps.
- Pre–stall-guard trees kept as
  `data/trace-targets-{cubic,bbr}.pre-stallguard-20261108/` (old ~33% /
  ~9–12% CUBIC/BBR story). Older separate tarballs
  `cmab-plus-trace-targets-{cubic,bbr}.tar.gz` are superseded for paper
  tables.

## Capacity decision

### CUBIC

- Extracted: `data/capacity-cubic/`
- Archive: `data/archives/cmab-plus-capacity-cubic.tar.gz`
- SHA-256:
  `0040b3d46a0b202ce0f734e383ef57e4876bb580b5874426df905c627050b14f`
- 45 sessions: three capacities × three players × five rounds.

### BBR

- Extracted: `data/capacity-bbr/`
- Archive: `data/archives/cmab-plus-capacity-bbr.tar.gz`
- SHA-256:
  `c62c01d2bdf15222ebdb5318393d59b7ebb93cb2c671e93f64dd4e5c409d9e9d`
- 45 sessions: three capacities × three players × five rounds.

## Integrity checks

```bash
shasum -a 256 review-3/data/archives/*.tar.gz

find review-3/data/capacity-cubic -name playback_latency.json | wc -l
find review-3/data/capacity-bbr -name playback_latency.json | wc -l
```

The expected capacity counts are 45 and 45. `analyze_capacity.py` requires 90
total sessions and 18 aggregate cells before it writes any final results.
