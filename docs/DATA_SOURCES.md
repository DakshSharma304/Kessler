# Data sources

- CelesTrak GP OMM: public orbital elements; approximately two-hour refresh target.
- CelesTrak SOCRATES Plus: published conjunction screening; approximately 10–11-hour refresh target.
- NASA CARA Analysis Tools: historical CDM validation fixtures only.
- Jonathan McDowell's GCAT: physical and status metadata, retaining uncertainty and missing values.

Every cached artifact records its URL, retrieval time, checksum, parse result, and count. A published SOCRATES maximum-probability value is an external screening metric—not Kessler's covariance-based probability.

## Current environment status (2026-10-10 UTC)

Direct requests to CelesTrak GP, CelesTrak SOCRATES, and GCAT all returned HTTP 403, including a direct approved retry with an identifiable user agent. No live counts are claimed. The application retains explicit unavailable statuses and never invents encounters.

For deterministic offline validation, the repository contains:

- A real Vanguard 1 OMM record distributed as the `python-sgp4` sample, labeled stale/archived in every response and UI view.
- Two historical NASA CARA CDMs at the repository-pinned commit `ce0f00722c56808755ee0adbe47a4e3d56439484`: Terra / Iridium-33 debris and Terra / SL-16 debris.

Historical fixtures are separate from current-mode data and are never mixed with current catalog states.
