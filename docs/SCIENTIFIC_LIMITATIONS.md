# Scientific limitations

Kessler is a research and educational prototype, not operational flight software. Catalog elements and third-party screening predictions can be stale or based on different orbit solutions. SGP4 is used for catalog propagation; maneuver simulations use a documented two-body + J2 force model and are hypothetical. Collision probability is unavailable without covariance unless a user explicitly opts into a labeled uncertainty assumption. Secondary screening is scoped and must never be interpreted as a guarantee of safety. Cleanup scores are transparent proxies rather than calibrated damages or mission costs.

- The current environment could not retrieve live upstream data (HTTP 403), so its globe uses one clearly marked archived real-data object and current SOCRATES coverage is empty.
- The maneuver model omits maneuver execution uncertainty, tracking updates, drag, solar/lunar gravity, solar radiation pressure, propulsion feasibility, and covariance propagation.
- The optimizer therefore uses nominal clearance for its current interactive historical workflow and labels every result `UNSCREENED`.
- Targeted secondary screening is implemented and unit-tested for applicable same-epoch trajectory sets, but the historical UI case correctly does not screen against today's catalog.
- Decay outputs are broad low/nominal/high drag scenario bands. They are not precise reentry dates and do not include ground-casualty estimates.
- Cleanup effort and benefit are dimensionless proxies. They are not prices, mission manifests, or calibrated expected loss.
