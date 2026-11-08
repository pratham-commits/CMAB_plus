# Capacity experiment results

All values are means of five 300 s sessions at a 3 s target. Latency and bitrate drop the first 20% of samples. Rebuffer is the post-trim fraction of buffer samples at or below 0.05 s.

| TCP | Capacity | Player | Latency (s) | Rebuffer (%) | Bitrate (kbps) |
| --- | ---: | --- | ---: | ---: | ---: |
| CUBIC | 8 Mbit | old CMAB | 6.73 | 3.31 | 5854 |
| CUBIC | 8 Mbit | CMAB+ | 6.48 | 2.85 | 5721 |
| CUBIC | 8 Mbit | L2A | 5.15 | 0.45 | 5075 |
| CUBIC | 4 Mbit | old CMAB | 8.58 | 82.25 | 6000 |
| CUBIC | 4 Mbit | CMAB+ | 3.54 | 0.00 | 1473 |
| CUBIC | 4 Mbit | L2A | 3.36 | 0.00 | 1500 |
| CUBIC | 1 Mbit | old CMAB | 23.96 | 98.79 | 6000 |
| CUBIC | 1 Mbit | CMAB+ | 7.23 | 16.54 | 888 |
| CUBIC | 1 Mbit | L2A | 3.47 | 0.00 | 450 |
| BBR | 8 Mbit | old CMAB | 6.22 | 1.77 | 5828 |
| BBR | 8 Mbit | CMAB+ | 6.63 | 3.49 | 5804 |
| BBR | 8 Mbit | L2A | 4.32 | 0.00 | 6000 |
| BBR | 4 Mbit | old CMAB | 8.66 | 65.69 | 6000 |
| BBR | 4 Mbit | CMAB+ | 3.62 | 0.00 | 1477 |
| BBR | 4 Mbit | L2A | 3.40 | 0.00 | 1500 |
| BBR | 1 Mbit | old CMAB | 47.04 | 99.13 | 6000 |
| BBR | 1 Mbit | CMAB+ | 3.85 | 0.00 | 450 |
| BBR | 1 Mbit | L2A | 3.69 | 0.00 | 450 |

## Direct CMAB+ versus old CMAB

| TCP | Capacity | Latency reduction | Rebuffer reduction |
| --- | ---: | ---: | ---: |
| CUBIC | 8 Mbit | 3.7% | 13.9% |
| CUBIC | 4 Mbit | 58.7% | 100.0% |
| CUBIC | 1 Mbit | 69.8% | 83.3% |
| BBR | 8 Mbit | -6.6% | -97.0% |
| BBR | 4 Mbit | 58.2% | 100.0% |
| BBR | 1 Mbit | 91.8% | 100.0% |

## Reading

- **4 Mbit is the central result.** Under both CUBIC and BBR, old CMAB keeps requesting 6000 kbps and rebuffers 65.69–82.25%. CMAB+ selects about 1475 kbps, reaches 3.54–3.62 s, and has 0% rebuffer. L2A is 3.36–3.40 s at 1500 kbps.
- **1 Mbit shows a transport-dependent limit.** BBR CMAB+ matches L2A at 450 kbps with 0% rebuffer. CUBIC CMAB+ chooses about 888 kbps and still rebuffers 16.54%; it remains much better than old CMAB but not competitive with L2A.
- **8 Mbit is not an improvement.** The top rung nominally fits. CMAB+ is close to old CMAB, but both have multi-second latency and some rebuffer; L2A is better.
- The result supports a narrow claim: throughput feasibility prevents old CMAB's forced-top-rung collapse when capacity lies below the top video rung. It does not establish that CMAB+ generally beats L2A.
