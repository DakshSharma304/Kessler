from __future__ import annotations

import json
import resource
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from app.data import parse_gp_json
from app.orbital import propagate_catalog_teme


def main() -> None:
    fixture = Path(__file__).parents[1] / "data" / "fixtures" / "gp_sample.json"
    obj = parse_gp_json(fixture.read_bytes(), source="archived real OMM benchmark fixture")[0][0]
    results = []
    for count in (100, 1_000, 10_000):
        objects = [obj] * count
        start = perf_counter()
        errors, _ = propagate_catalog_teme(objects, datetime(2026, 10, 10, tzinfo=UTC))
        results.append({
            "objects": count, "wall_seconds": perf_counter() - start,
            "failed_propagations": int((errors != 0).sum()),
            "fixture_note": "same archived real Vanguard 1 OMM duplicated to isolate batch throughput",
        })
    print(json.dumps({"propagation": results, "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}, indent=2))


if __name__ == "__main__":
    main()
