# Performance

## Real loaded-catalog API check — 2026-10-10 UTC

One warm, local HTTP run against the real active-group snapshot (16,701 objects):

| Operation | Wall time | Result |
| --- | ---: | --- |
| Retrieve all 17 catalog pages and parse JSON | 1.585 s | 16,701 IDs, consistent snapshot checksum |
| POST positions, batch SGP4/ITRS, receive and parse JSON | 1.831 s | 16,701 states, zero failed objects |

These timings include local HTTP transfer/client parsing but exclude the original
upstream download and browser rendering. Single-run evidence, not an FPS,
concurrency, cold-start, or user-machine performance guarantee.

Loading update: the actual positions API now uses batch SGP4/ITRS and was exercised
with a real 16,701-object snapshot in browser verification (16,701 states, no errors).
This is functional catalog-scale evidence, not an FPS/concurrency benchmark. The
measurements and API-loop limitations below refer to the pre-repair baseline; see
[current loading evidence](CATALOG_LOADING.md).

Previously recorded on the onboarding cloud machine (5 CPU cores, 33 GiB RAM), 2026-10-10 UTC. These benchmarks were not rerun for the documentation correction; current test/build timings are in [CHECKPOINTS.md](CHECKPOINTS.md).

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

The historical 18-candidate run was below 30 s, but the default enumeration evaluates only the first burn time, not a complete time search. Batch-helper timings exclude API serialization, ITRS conversions, transfer, and browser rendering; the actual positions API does not use that helper. They do not establish interactive 10,000-object performance. Actual search, trajectory API, refined encounter, simultaneous-request, 100-candidate, cleanup, and full-catalog/browser benchmarks remain unverified. Live-source access was previously blocked by HTTP 403 in this cloud.
