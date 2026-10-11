# Scientific limitations

Playback now interpolates real SGP4/ITRS samples on the GPU for display only.
300-second cubic-Hermite sample spacing and Float32 rendering introduce additional
approximation. No collision/risk/maneuver result uses these interpolated markers.
Accuracy checks are snapshot-specific, not scientific error bounds. See
[INTERPOLATED_PLAYBACK.md](INTERPOLATED_PLAYBACK.md).

Loading update: current GP fetching succeeded for 16,701 active-group objects;
automatic loading/cache/UI pagination and batch API are repaired. The old one-object
cloud condition below is baseline evidence, not the present catalog state. No new
SOCRATES/GCAT fetch occurred. Full debris coverage, element-age applicability,
partial orbit display, current encounters, and scientific planner limitations remain.
See [CATALOG_LOADING.md](CATALOG_LOADING.md).

Kessler is a partial research/educational prototype, not operational flight software.
Scientific routines and product workflows must be evaluated separately. See
[the evidence-backed audit](IMPLEMENTATION_AUDIT.md).

- Cloud runtime: one archived object, no SOCRATES encounters. Stored previous 403s
  do not prove local/Modal failure. Old elements are propagated at current UI time;
  state metadata does not consistently inherit freshness/applicability warnings.
- SGP4 is real, but the 90-minute display is not a full orbit. Time-dependent ITRS
  paths must not be confused with a closed inertial orbital-shape visualization.
- Current analysis does not minimize TCA locally. Assumed-current Pc uses incorrect
  XY projection. SOCRATES MAX_PROB remains an external screening metric.
- Two historical NASA probability regressions pass; arbitrary CDM frames/units,
  radius assumptions, conditioning, and independent NASA numerical validation are
  incomplete. Fixture agreement does not validate every input.
- Hypothetical gravity+J2 maneuvers omit execution error, drag, solar/lunar forces,
  tracking updates, propulsion feasibility, and covariance propagation. Baseline
  and modified minima are not equivalently refined; epoch/frame checks and numerical
  convergence are not fully validated.
- Avoidance uses first historical case, not selected current encounter. Default
  optimizer evaluates first burn time only. Results are UNSCREENED; nominal
  separation is not collision probability or evidence of actual safety.
- Standalone straight-line screening is not integrated. Synthetic crossings do not
  establish conservative curved-orbit coverage. Internal “complete” status does
  not establish catalog-level safety.
- Hardcoded decay lifetime bands lack cited physical validation and are not
  integrated. A justified model or unavailable state is required, not supported
  lifetime/reentry claims.
- Cleanup math is real, but inputs are arbitrary: index-based effort, constant
  exposure/consequence, unsupported persistence. Proxy labeling does not make
  those inputs scientifically grounded. GCAT mass/status/dimensions are not joined.
- No actual maneuver, precise reentry, ground-casualty forecast, mission cost, or
  operational spacecraft capability is established.
