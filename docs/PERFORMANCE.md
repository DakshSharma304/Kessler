# Performance

Measured on the onboarding cloud machine (5 CPU cores, 33 GiB RAM), 2026-10-10 UTC.

## SGP4 batch throughput

The same archived real Vanguard 1 OMM was duplicated solely to isolate `SatrecArray` batch throughput; these are not catalog-coverage claims.

| Objects | Wall time | Failed propagations |
| ---: | ---: | ---: |
| 100 | 0.00210 s | 0 |
| 1,000 | 0.01450 s | 0 |
| 10,000 | 0.21798 s | 0 |

Peak process resident set during that benchmark was 93,560 KiB.

## Scientific/API operations

- Two NASA collision-probability integrations plus the full backend test suite: 1.37 s total test time.
- Fresh 18-candidate maneuver optimization: 1.54 s wall time, 18 completed candidates, 3 nondominated solutions.
- Four serial Chromium end-to-end flows, including maneuver and cleanup optimizations: 9.9 s.

The optimizer target (<30 s) and 10,000-object propagation target for interactive use were met on this fixture benchmark. Full live-catalog memory and source-download benchmarks remain blocked by upstream HTTP 403 access.
