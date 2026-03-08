"""
Заповнення Neo4J графом автодоріг.
Вузли: City (name, lat, lon), ребра: CONNECTED_BY_ROAD (distance_km, speed_limit)
"""
import os
from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

CITIES = [
    ("Київ", 50.4501, 30.5234),
    ("Львів", 49.8397, 24.0297),
    ("Одеса", 46.4825, 30.7233),
    ("Харків", 49.9935, 36.2304),
    ("Дніпро", 48.4647, 35.0462),
    ("Запоріжжя", 47.8388, 35.1396),
    ("Вінниця", 49.2328, 28.4681),
    ("Чернігів", 51.4982, 31.2893),
]

# (from, to, distance_km, speed_limit)
ROADS = [
    ("Київ", "Львів", 540, 90),
    ("Київ", "Одеса", 475, 90),
    ("Київ", "Харків", 481, 110),
    ("Київ", "Дніпро", 478, 110),
    ("Київ", "Вінниця", 268, 90),
    ("Київ", "Чернігів", 145, 90),
    ("Львів", "Вінниця", 365, 90),
    ("Одеса", "Вінниця", 428, 90),
    ("Харків", "Дніпро", 218, 110),
    ("Дніпро", "Запоріжжя", 85, 110),
]


def seed(driver):
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
        for name, lat, lon in CITIES:
            session.run(
                "CREATE (c:City {name: $name, lat: $lat, lon: $lon})",
                name=name, lat=lat, lon=lon
            )
        for a, b, dist, speed in ROADS:
            session.run("""
                MATCH (from:City {name: $a}), (to:City {name: $b})
                CREATE (from)-[:CONNECTED_BY_ROAD {distance_km: $dist, speed_limit: $speed}]->(to)
                CREATE (to)-[:CONNECTED_BY_ROAD {distance_km: $dist, speed_limit: $speed}]->(from)
            """, a=a, b=b, dist=dist, speed=speed)
        print("Neo4J: створено", len(CITIES), "міст та", len(ROADS) * 2, "зв'язків")


if __name__ == "__main__":
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        driver.verify_connectivity()
        seed(driver)
    finally:
        driver.close()
