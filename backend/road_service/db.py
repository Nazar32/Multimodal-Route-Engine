"""
Підключення до Neo4J та пошук маршрутів по автодорогах.
"""
import os
from typing import Optional
from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

_driver: Optional[GraphDatabase.driver] = None


def get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    return _driver


def is_available() -> bool:
    try:
        print("Neo4J is available")
        get_driver().verify_connectivity()
        return True
    except Exception:
        print("Neo4J is not available")
        return False


def get_places():
    """Список міст з Neo4J."""
    with get_driver().session() as session:
        result = session.run("MATCH (c:City) RETURN c.name AS name, c.lat AS lat, c.lon AS lon")
        
        response = [
            {"name": r["name"], "id": r["name"].lower().replace(" ", "_"), "type": "city", "lat": r["lat"], "lon": r["lon"]}
            for r in result
        ]
        print("Road routes result:", response)
        return response


def find_routes(departure: str, arrival: str) -> list[dict]:
    """
    Пошук маршрутів між містами (найкоротші за відстанню).
    Повертає список маршрутів з сегментами.
    """
    with get_driver().session() as session:
        # Використовуємо shortestPath з варіативною довжиною
        # Збираємо всі шляхи, обчислюємо загальну відстань, сортуємо
        result = session.run("""
            MATCH path = (a:City {name: $departure})-[:CONNECTED_BY_ROAD*1..5]-(b:City {name: $arrival})
            WITH path,
                 reduce(d = 0.0, r IN relationships(path) | d + r.distance_km) AS total_km,
                 reduce(t = 0, r IN relationships(path) | t + toInteger(r.distance_km / r.speed_limit * 60)) AS total_min
            WITH path, total_km, total_min
            ORDER BY total_km ASC
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
                dist = rel.get("distance_km", 0)
                speed = rel.get("speed_limit", 90)
                duration = int(dist / speed * 60) if speed else 0
                segments.append({
                    "transport": "road",
                    "from_place": start_node["name"],
                    "to_place": end_node["name"],
                    "distance_km": dist,
                    "duration_min": duration,
                    "details": {"speed_limit": speed},
                })
            if segments:
                routes.append({
                    "segments": segments,
                    "total_distance_km": total_km,
                    "total_duration_min": total_min,
                    "transport_types": ["road"],
                })
        return routes
