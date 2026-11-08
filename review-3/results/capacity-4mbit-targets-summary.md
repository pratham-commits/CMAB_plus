# 4 Mbit target-robustness results

Fixed 4 Mbit clock (handover rate stays 4; mild 100 ms / 1% loss). Means of five 300 s sessions. Latency and bitrate drop the first 20% of samples. Rebuffer is the post-trim fraction of buffer samples at or below 0.05 s.

| TCP | Target | Player | Latency (s) | Rebuffer (%) | Bitrate (kbps) |
| --- | ---: | --- | ---: | ---: | ---: |
| CUBIC | 3 s | old CMAB | 8.56 | 80.59 | 6000 |
| CUBIC | 3 s | CMAB+ | 3.54 | 0.00 | 1457 |
| CUBIC | 3 s | L2A | 3.35 | 0.00 | 1500 |
| CUBIC | 4 s | old CMAB | 9.62 | 78.83 | 6000 |
| CUBIC | 4 s | CMAB+ | 4.20 | 0.00 | 1467 |
| CUBIC | 4 s | L2A | 4.00 | 0.00 | 1500 |
| CUBIC | 5 s | old CMAB | 10.59 | 78.90 | 6000 |
| CUBIC | 5 s | CMAB+ | 5.21 | 0.00 | 1472 |
| CUBIC | 5 s | L2A | 5.00 | 0.00 | 1500 |
| CUBIC | 6 s | old CMAB | 11.64 | 71.70 | 6000 |
| CUBIC | 6 s | CMAB+ | 6.23 | 0.00 | 1469 |
| CUBIC | 6 s | L2A | 6.00 | 0.00 | 1500 |
| BBR | 3 s | old CMAB | 8.62 | 62.05 | 6000 |
| BBR | 3 s | CMAB+ | 3.62 | 0.00 | 1474 |
| BBR | 3 s | L2A | 3.41 | 0.00 | 1500 |
| BBR | 4 s | old CMAB | 9.59 | 64.01 | 6000 |
| BBR | 4 s | CMAB+ | 4.21 | 0.00 | 1477 |
| BBR | 4 s | L2A | 4.00 | 0.00 | 1500 |
| BBR | 5 s | old CMAB | 10.86 | 65.40 | 6000 |
| BBR | 5 s | CMAB+ | 5.22 | 0.00 | 1472 |
| BBR | 5 s | L2A | 5.00 | 0.00 | 1500 |
| BBR | 6 s | old CMAB | 11.85 | 69.23 | 6000 |
| BBR | 6 s | CMAB+ | 6.23 | 0.00 | 1475 |
| BBR | 6 s | L2A | 6.00 | 0.00 | 1500 |

## CMAB+ versus old CMAB

| TCP | Target | Δ latency (s) | Latency change | Rebuffer change | Bitrate change |
| --- | ---: | ---: | ---: | ---: | ---: |
| CUBIC | 3 s | -5.02 | -58.7% | -100.0% | -4543 kbps |
| CUBIC | 4 s | -5.42 | -56.4% | -100.0% | -4533 kbps |
| CUBIC | 5 s | -5.37 | -50.8% | -100.0% | -4528 kbps |
| CUBIC | 6 s | -5.42 | -46.5% | -100.0% | -4531 kbps |
| BBR | 3 s | -5.00 | -58.0% | -100.0% | -4526 kbps |
| BBR | 4 s | -5.38 | -56.1% | -100.0% | -4523 kbps |
| BBR | 5 s | -5.65 | -52.0% | -100.0% | -4528 kbps |
| BBR | 6 s | -5.62 | -47.4% | -100.0% | -4525 kbps |

## Reading

- Pass if CMAB+ stays near the target with ~0% rebuffer and ~1.5 Mbps at every target, while old CMAB stays at 6000 kbps with high rebuffer.
- Compare CMAB+ to L2A on the same run; L2A is the same-batch reference.
