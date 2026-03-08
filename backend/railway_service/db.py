"""
Підключення до Memgraph та пошук маршрутів по залізниці.
"""
import os
from typing import Optional
from neo4j import GraphDatabase

MEMGRAPH_URI = os.getenv("MEMGRAPH_URI", "bolt://localhost:7687")
MEMGRAPH_USER = os.getenv("MEMGRAPH_USER", "")
MEMGRAPH_PASSWORD = os.getenv("MEMGRAPH_PASSWORD", "")

_driver: Optional[GraphDatabase.driver] = None


def get_driver():
    global _driver
    if _driver is None:
        auth = (MEMGRAPH_USER, MEMGRAPH_PASSWORD) if MEMGRAPH_USER else ("", "")
        _driver = GraphDatabase.driver(MEMGRAPH_URI, auth=auth)
    return _driver


def is_available() -> bool:
    try:
        get_driver().verify_connectivity()
        return True
    except Exception:
        return False


def get_places():
    """Список станцій з Memgraph."""
    with get_driver().session() as session:
        result = session.run("MATCH (s:Station) RETURN s.name AS name")
        return [
            {"name": r["name"], "id": r["name"].lower().replace(" ", "_"), "type": "station"}
            for r in result
        ]


def find_routes(departure: str, arrival: str) -> list[dict]:
    """
    Пошук маршрутів між станціями (найкоротші за часом).
    Memgraph може мати кілька ребер між однією парою (різні типи потягів).
    """
    with get_driver().session() as session:
        # Шляхи з варіативною довжиною, сортуємо за часом
        result = session.run("""
            MATCH path = (a:Station {name: $departure})-[:CONNECTED_BY_RAIL*1..5]-(b:Station {name: $arrival})
            WITH path,
                 reduce(d = 0.0, r IN relationships(path) | d + r.distance_km) AS total_km,
                 reduce(t = 0, r IN relationships(path) | t + r.duration_min) AS total_min
            WITH path, total_km, total_min
            ORDER BY total_min ASC
            LIMIT 5
            RETURN path, total_km, total_min
        """, departure=departure, arrival=arrival)

        routes = []
        for record in result:
            path = record["path"]
            total_km = record["total_km"]
            total_min = record["total_min"]
            segments = []
            for i, rel in enumerate(path.relationships):
                start_node = path.nodes[i]
                end_node = path.nodes[i + 1]
                dur = rel.get("duration_min", 0)
                train_type = rel.get("train_type", "")
                segments.append({
                    "transport": "railway",
                    "from_place": start_node["name"],
                    "to_place": end_node["name"],
                    "distance_km": rel.get("distance_km"),
                    "duration_min": dur,
                    "details": {"train_type": train_type} if train_type else None,
                })
            if segments:
                routes.append({
                    "segments": segments,
                    "total_distance_km": total_km,
                    "total_duration_min": total_min,
                    "transport_types": ["railway"],
                })
        return routes
