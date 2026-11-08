# BBR emulation audit report

- **Audited at (UTC):** 2026-10-11T05:10:44.301590Z
- **Production runs (300 s):** 160 (expected 160)
- **Smoke runs (60 s):** 3 — excluded from paper plots
- **160 matrix complete:** True
- **Production runs with hard issues:** 0
- **IQR statistical outliers (informational):** 34

## Smoke sessions (do not aggregate)

- `abrDynamic-1010-0405-target-latency-3s-duration-60-bitrate-variable-0`
- `abrDynamic-1010-0416-target-latency-3s-duration-60-bitrate-variable-0`
- `abrDynamic-1010-0418-target-latency-3s-duration-60-bitrate-variable-0`

## Matrix gaps

- None

## Anomalies (actionable)

- None — production set looks consistent.

## IQR outliers (review only)

- iqr_latency ('abrDynamic', 3): `abrDynamic-1010-0432-target-latency-3s-duration-300-bitrate-variable-1`
- iqr_latency ('abrLoLP', 3): `abrLoLP-1010-0432-target-latency-3s-duration-300-bitrate-variable-8`
- iqr_latency ('abrL2A', 4): `abrL2A-1010-0432-target-latency-4s-duration-300-bitrate-variable-7`
- iqr_latency ('abrL2A', 4): `abrL2A-1010-0432-target-latency-4s-duration-300-bitrate-variable-1`
- iqr_latency ('abrLoLP', 4): `abrLoLP-1010-0432-target-latency-4s-duration-300-bitrate-variable-0`
- iqr_latency ('abrCMAB', 5): `abrCMAB-1010-0432-target-latency-5s-duration-300-bitrate-variable-3`
- iqr_latency ('abrCMAB', 6): `abrCMAB-1010-0432-target-latency-6s-duration-300-bitrate-variable-3`
- iqr_latency ('abrCMAB', 6): `abrCMAB-1010-0432-target-latency-6s-duration-300-bitrate-variable-7`
- iqr_latency ('abrL2A', 6): `abrL2A-1010-0432-target-latency-6s-duration-300-bitrate-variable-1`
- iqr_latency ('abrLoLP', 6): `abrLoLP-1010-0432-target-latency-6s-duration-300-bitrate-variable-2`
- iqr_latency ('abrLoLP', 6): `abrLoLP-1010-0432-target-latency-6s-duration-300-bitrate-variable-6`
- iqr_latency ('abrLoLP', 6): `abrLoLP-1010-0432-target-latency-6s-duration-300-bitrate-variable-9`
- iqr_rebuffer ('abrLoLP', 3): `abrLoLP-1010-0432-target-latency-3s-duration-300-bitrate-variable-1`
- iqr_rebuffer ('abrLoLP', 3): `abrLoLP-1010-0432-target-latency-3s-duration-300-bitrate-variable-8`
- iqr_rebuffer ('abrLoLP', 4): `abrLoLP-1010-0432-target-latency-4s-duration-300-bitrate-variable-0`
- iqr_rebuffer ('abrL2A', 6): `abrL2A-1010-0432-target-latency-6s-duration-300-bitrate-variable-1`
- iqr_rebuffer ('abrLoLP', 6): `abrLoLP-1010-0432-target-latency-6s-duration-300-bitrate-variable-2`
- iqr_bitrate ('abrCMAB', 3): `abrCMAB-1010-0432-target-latency-3s-duration-300-bitrate-variable-3`
- iqr_bitrate ('abrDynamic', 3): `abrDynamic-1010-0432-target-latency-3s-duration-300-bitrate-variable-7`
- iqr_bitrate ('abrCMAB', 4): `abrCMAB-1010-0432-target-latency-4s-duration-300-bitrate-variable-0`
- iqr_bitrate ('abrDynamic', 4): `abrDynamic-1010-0432-target-latency-4s-duration-300-bitrate-variable-0`
- iqr_bitrate ('abrDynamic', 4): `abrDynamic-1010-0432-target-latency-4s-duration-300-bitrate-variable-8`
- iqr_bitrate ('abrL2A', 4): `abrL2A-1010-0432-target-latency-4s-duration-300-bitrate-variable-0`
- iqr_bitrate ('abrL2A', 4): `abrL2A-1010-0432-target-latency-4s-duration-300-bitrate-variable-4`
- iqr_bitrate ('abrL2A', 4): `abrL2A-1010-0432-target-latency-4s-duration-300-bitrate-variable-2`
- iqr_bitrate ('abrL2A', 4): `abrL2A-1010-0432-target-latency-4s-duration-300-bitrate-variable-5`
- iqr_bitrate ('abrLoLP', 4): `abrLoLP-1010-0432-target-latency-4s-duration-300-bitrate-variable-4`
- iqr_bitrate ('abrL2A', 5): `abrL2A-1010-0432-target-latency-5s-duration-300-bitrate-variable-2`
- iqr_bitrate ('abrL2A', 5): `abrL2A-1010-0432-target-latency-5s-duration-300-bitrate-variable-0`
- iqr_bitrate ('abrL2A', 5): `abrL2A-1010-0432-target-latency-5s-duration-300-bitrate-variable-9`
- … and 4 more (see anomalies.json)
