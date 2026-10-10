# Data sources

- CelesTrak GP OMM: public orbital elements; approximately two-hour refresh target.
- CelesTrak SOCRATES Plus: published conjunction screening; approximately 10–11-hour refresh target.
- NASA CARA Analysis Tools: historical CDM validation fixtures only.
- Jonathan McDowell's GCAT: intended physical/status metadata source. Code parses/counts TSV rows but does not normalize, persist, or join properties; catalog preservation of uncertainty/missing values is not implemented.

Downloaded-source status supports URL, retrieval time, checksum, parse result, and count, but dataset timestamps/coverage are incomplete. Bytes are cached before parsing, so last-known-good retention is unreliable for malformed successful responses. Startup loads the archive rather than fetching sources; refresh is manual. GP queries only the active group, not the whole catalog; classification is incomplete. SOCRATES maximum probability is an external screening metric—not Kessler's covariance-based Pc.

## Current environment status (2026-10-10 UTC)

Previous direct requests to CelesTrak GP/SOCRATES and GCAT returned HTTP 403, including an approved retry with an identifiable user agent. This audit reread stored status without retrying sources. No live counts are claimed. This is cloud-specific evidence, not proof that local/Modal access fails. Unavailable statuses remain; encounters are not invented.

For deterministic offline validation, the repository contains:

- A real Vanguard 1 OMM from the `python-sgp4` sample. Dataset status and Explore label it stale/archived; propagated state metadata does not consistently inherit stale status, so not every response correctly reports freshness.
- Two historical NASA CARA CDMs at the repository-pinned commit `ce0f00722c56808755ee0adbe47a4e3d56439484`: Terra / Iridium-33 debris and Terra / SL-16 debris.

NASA fixtures stay separate from the current catalog, but Avoidance always chooses the first historical fixture, ignoring current encounter selection. GP has real-fixture parsing evidence; SOCRATES tests use synthetic CSV, not verified published rows. GCAT integration and freshness propagation are incomplete. See [the audit](IMPLEMENTATION_AUDIT.md).
