"""Minimal semantic feature assembly for the IEQ research scaffold.

This dependency-free module is not an RDF reasoner. It makes the experimental
contract executable: observations are joined to rooms and HVAC zones through
explicit graph relations, without using target values.
"""

from collections import defaultdict
from typing import Iterable, Mapping, Sequence

Triple = tuple[str, str, str]


def index_graph(triples: Iterable[Triple]) -> dict[str, dict[str, list[str]]]:
    index: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for subject, predicate, obj in triples:
        if obj not in index[subject][predicate]:
            index[subject][predicate].append(obj)
    return {subject: dict(predicates) for subject, predicates in index.items()}


def assemble_room_features(
    records: Sequence[Mapping[str, object]], triples: Iterable[Triple]
) -> list[dict[str, object]]:
    """Add graph-derived room and HVAC-zone context to sensor observations."""

    graph = index_graph(triples)
    output: list[dict[str, object]] = []
    for record in records:
        sensor = str(record["sensor_id"])
        rooms = graph.get(sensor, {}).get("isPointOf", [])
        room = rooms[0] if rooms else "UNKNOWN"
        zones = graph.get(room, {}).get("isPartOf", []) if room != "UNKNOWN" else []
        zone = zones[0] if zones else "UNKNOWN"
        enriched = dict(record)
        enriched["semantic_room"] = room
        enriched["semantic_hvac_zone"] = zone
        enriched["semantic_mapping_complete"] = int(room != "UNKNOWN" and zone != "UNKNOWN")
        output.append(enriched)
    return output


def mapping_coverage(rows: Sequence[Mapping[str, object]]) -> float:
    if not rows:
        return 0.0
    return sum(int(row.get("semantic_mapping_complete", 0)) for row in rows) / len(rows)

