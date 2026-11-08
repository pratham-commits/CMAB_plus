# Clock non-regression results

Paper clock: 100 Mbit normal, 50 Mbit / 100 ms / 1% loss at 12/27/42/57. Means of five 300 s sessions. Latency and bitrate drop the first 20% of samples. Rebuffer is the post-trim fraction of buffer samples at or below 0.05 s.

| TCP | Target | Player | Latency (s) | Rebuffer (%) | Bitrate (kbps) |
| --- | ---: | --- | ---: | ---: | ---: |
| CUBIC | 3 s | old CMAB | 4.09 | 0.00 | 5363 |
| CUBIC | 3 s | CMAB+ | 4.24 | 0.00 | 5420 |
| CUBIC | 3 s | L2A | 4.02 | 0.00 | 6000 |
| CUBIC | 4 s | old CMAB | 4.52 | 0.00 | 5292 |
| CUBIC | 4 s | CMAB+ | 4.54 | 0.00 | 5433 |
| CUBIC | 4 s | L2A | 4.37 | 0.00 | 6000 |
| CUBIC | 5 s | old CMAB | 5.29 | 0.00 | 5430 |
| CUBIC | 5 s | CMAB+ | 5.24 | 0.00 | 5448 |
| CUBIC | 5 s | L2A | 5.03 | 0.00 | 6000 |
| CUBIC | 6 s | old CMAB | 6.28 | 0.00 | 5378 |
| CUBIC | 6 s | CMAB+ | 6.27 | 0.00 | 5462 |
| CUBIC | 6 s | L2A | 6.02 | 0.00 | 6000 |
| BBR | 3 s | old CMAB | 3.45 | 0.00 | 5251 |
| BBR | 3 s | CMAB+ | 3.44 | 0.00 | 5255 |
| BBR | 3 s | L2A | 3.06 | 0.00 | 6000 |
| BBR | 4 s | old CMAB | 4.21 | 0.00 | 5252 |
| BBR | 4 s | CMAB+ | 4.23 | 0.00 | 5290 |
| BBR | 4 s | L2A | 4.08 | 0.00 | 6000 |
| BBR | 5 s | old CMAB | 5.51 | 0.26 | 5201 |
| BBR | 5 s | CMAB+ | 5.23 | 0.08 | 5285 |
| BBR | 5 s | L2A | 5.08 | 0.00 | 6000 |
| BBR | 6 s | old CMAB | 6.23 | 0.00 | 5340 |
| BBR | 6 s | CMAB+ | 6.31 | 0.38 | 5329 |
| BBR | 6 s | L2A | 6.06 | 0.00 | 6000 |

## CMAB+ versus old CMAB

| TCP | Target | Δ latency (s) | Latency change | Rebuffer change | Bitrate change |
| --- | ---: | ---: | ---: | ---: | ---: |
| CUBIC | 3 s | +0.15 | +3.6% | +0.0% | +57 kbps |
| CUBIC | 4 s | +0.02 | +0.4% | +0.0% | +141 kbps |
| CUBIC | 5 s | -0.05 | -1.0% | +0.0% | +18 kbps |
| CUBIC | 6 s | -0.01 | -0.2% | +0.0% | +84 kbps |
| BBR | 3 s | -0.02 | -0.5% | +0.0% | +3 kbps |
| BBR | 4 s | +0.02 | +0.5% | +0.0% | +38 kbps |
| BBR | 5 s | -0.28 | -5.1% | -68.2% | +83 kbps |
| BBR | 6 s | +0.08 | +1.3% | +0.4% | -11 kbps |

## Reading

- Pass if CMAB+ stays in the same class as old CMAB: similar bitrate, near-zero rebuffer, latency within a few tenths of a second.
- Absolute latency can sit above the Review I ~3.2 s CUBIC number if this emulation is harsher; L2A on the same run is the same-run reference.
- Fail if CMAB+ collapses toward a few hundred kbps, or if the 3 s row cuts bitrate the way the rejected 1 s latency step-down did.
