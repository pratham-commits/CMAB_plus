# Trace target results

Real Starlink ISL trace (SHAPER=trace, handover loss 100%). Means of five 300 s sessions. Latency and bitrate drop the first 20% of samples. Rebuffer is the post-trim fraction of buffer samples at or below 0.05 s.

| TCP | Target | Player | Latency (s) | Rebuffer (%) | Bitrate (kbps) |
| --- | ---: | --- | ---: | ---: | ---: |
| CUBIC | 3 s | old CMAB | 19.62 | 81.14 | 6000 |
| CUBIC | 3 s | CMAB+ | 6.46 | 14.67 | 851 |
| CUBIC | 3 s | L2A | 4.19 | 0.52 | 316 |
| CUBIC | 4 s | old CMAB | 20.87 | 84.61 | 6000 |
| CUBIC | 4 s | CMAB+ | 7.32 | 12.53 | 832 |
| CUBIC | 4 s | L2A | 4.75 | 1.43 | 329 |
| CUBIC | 5 s | old CMAB | 18.50 | 82.52 | 6000 |
| CUBIC | 5 s | CMAB+ | 8.18 | 11.52 | 893 |
| CUBIC | 5 s | L2A | 5.52 | 0.69 | 301 |
| CUBIC | 6 s | old CMAB | 20.20 | 78.55 | 6000 |
| CUBIC | 6 s | CMAB+ | 8.84 | 12.09 | 935 |
| CUBIC | 6 s | L2A | 6.30 | 0.49 | 330 |
| BBR | 3 s | old CMAB | 7.16 | 28.98 | 5882 |
| BBR | 3 s | CMAB+ | 6.05 | 8.29 | 2658 |
| BBR | 3 s | L2A | 3.91 | 0.77 | 449 |
| BBR | 4 s | old CMAB | 8.14 | 29.60 | 5887 |
| BBR | 4 s | CMAB+ | 6.76 | 6.67 | 2575 |
| BBR | 4 s | L2A | 4.44 | 1.21 | 360 |
| BBR | 5 s | old CMAB | 9.07 | 32.88 | 5884 |
| BBR | 5 s | CMAB+ | 7.24 | 5.60 | 2499 |
| BBR | 5 s | L2A | 5.50 | 0.93 | 482 |
| BBR | 6 s | old CMAB | 10.19 | 31.45 | 5913 |
| BBR | 6 s | CMAB+ | 7.93 | 4.75 | 2917 |
| BBR | 6 s | L2A | 6.41 | 0.51 | 444 |

## CMAB+ versus old CMAB

| TCP | Target | Δ latency (s) | Latency change | Rebuffer change | Bitrate change |
| --- | ---: | ---: | ---: | ---: | ---: |
| CUBIC | 3 s | -13.15 | -67.0% | -81.9% | -5149 kbps |
| CUBIC | 4 s | -13.54 | -64.9% | -85.2% | -5168 kbps |
| CUBIC | 5 s | -10.32 | -55.8% | -86.0% | -5107 kbps |
| CUBIC | 6 s | -11.36 | -56.2% | -84.6% | -5065 kbps |
| BBR | 3 s | -1.11 | -15.5% | -71.4% | -3225 kbps |
| BBR | 4 s | -1.39 | -17.0% | -77.5% | -3312 kbps |
| BBR | 5 s | -1.83 | -20.2% | -83.0% | -3385 kbps |
| BBR | 6 s | -2.26 | -22.2% | -84.9% | -2997 kbps |

## Reading

- Final player includes stall guard. Pass vs old CMAB: rebuffer and latency
  drop without locking at 6000 kbps (holds at every target on both CCs).
- Not a pass vs L2A: L2A keeps near-zero rebuffer at ~300–450 kbps.
- Conference claim: CMAB+ improves the unsafe CMAB bootstrap on this trace;
  it does not replace L2A as the stall-minimizing reference.
