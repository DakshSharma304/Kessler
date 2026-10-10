from __future__ import annotations

from app.models import CleanupOptimizeRequest, CleanupPortfolio, CleanupSelection


def optimize_cleanup(request: CleanupOptimizeRequest) -> CleanupPortfolio:
    weights = {
        "balanced": (1.0, 1.0, 1.0),
        "persistence": (2.5, 0.75, 0.75),
        "exposure": (0.75, 2.5, 0.75),
        "consequence": (0.75, 0.75, 2.5),
    }[request.priority]
    candidates = {item.object_id: item for item in request.candidates}
    covered_edges: set[int] = set()
    selected: list[CleanupSelection] = []
    remaining = request.budget
    total_benefit = 0.0
    while len(selected) < request.max_objects:
        best = None
        for candidate in candidates.values():
            if candidate.effort > remaining or any(s.candidate.object_id == candidate.object_id for s in selected):
                continue
            intrinsic = weights[0] * candidate.persistence + weights[1] * candidate.exposure + weights[2] * candidate.consequence
            incident = sum(edge.weight for index, edge in enumerate(request.edges) if index not in covered_edges and candidate.object_id in {edge.object_a, edge.object_b})
            benefit = intrinsic + incident
            ratio = benefit / candidate.effort
            key = (ratio, benefit, candidate.object_id)
            if best is None or key > best[0]:
                best = (key, candidate, benefit)
        if best is None:
            break
        _, candidate, benefit = best
        selected.append(CleanupSelection(
            candidate=candidate,
            marginal_benefit=benefit,
            reason=f"Selected for marginal {request.priority} proxy benefit {benefit:.3f} at effort {candidate.effort:.3f}.",
        ))
        remaining -= candidate.effort
        total_benefit += benefit
        covered_edges.update(index for index, edge in enumerate(request.edges) if candidate.object_id in {edge.object_a, edge.object_b})
    selected_ids = {item.candidate.object_id for item in selected}
    alternatives = [item for item in request.candidates if item.object_id not in selected_ids][:10]
    return CleanupPortfolio(
        selected=selected,
        alternatives=alternatives,
        total_effort=request.budget - remaining,
        modeled_benefit=total_benefit,
        remaining_budget=remaining,
        assumptions=[
            "Scores are relative persistence, exposure, and consequence proxies—not operational risk or monetary value.",
            "Shared encounter-edge benefit is counted once and marginal benefits are recomputed after each selection.",
        ],
    )
