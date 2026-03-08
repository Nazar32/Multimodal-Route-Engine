"""
Заповнення Memgraph графом залізниці.
Вузли: Station (name), ребра: CONNECTED_BY_RAIL (distance_km, duration_min, train_type)
"""
import os
from neo4j import GraphDatabase

# Memgraph використовує Bolt протокол, як Neo4J
MEMGRAPH_URI = os.getenv("MEMGRAPH_URI", "bolt://localhost:7687")
MEMGRAPH_USER = os.getenv("MEMGRAPH_USER", "")  # за замовчуванням без авторизації
MEMGRAPH_PASSWORD = os.getenv("MEMGRAPH_PASSWORD", "")

STATIONS = ["Київ", "Львів", "Одеса", "Харків", "Дніпро", "Запоріжжя", "Вінниця", "Чернігів"]

# (from, to, distance_km, duration_min, train_type)
RAILS = [
    ("Київ", "Львів", 540, 330, "Інтерсіті"),
    ("Київ", "Львів", 540, 420, "Нічний"),
    ("Київ", "Одеса", 475, 420, "Нічний"),
    ("Київ", "Одеса", 475, 510, "Пасажирський"),
    ("Київ", "Харків", 481, 300, "Інтерсіті"),
    ("Київ", "Харків", 481, 420, "Швидкий"),
    ("Київ", "Дніпро", 478, 360, "Інтерсіті"),
    ("Київ", "Вінниця", 268, 180, "Швидкий"),
    ("Київ", "Чернігів", 145, 120, "Приміський"),
    ("Львів", "Вінниця", 365, 300, "Швидкий"),
    ("Одеса", "Вінниця", 428, 360, "Швидкий"),
    ("Харків", "Дніпро", 218, 180, "Інтерсіті"),
    ("Дніпро", "Запоріжжя", 85, 60, "Приміський"),
]


def seed(driver):
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
        for name in STATIONS:
            session.run("CREATE (s:Station {name: $name})", name=name)
        count = 0
        for a, b, dist, dur, train in RAILS:
            session.run("""
                MATCH (from:Station {name: $a}), (to:Station {name: $b})
                CREATE (from)-[:CONNECTED_BY_RAIL {distance_km: $dist, duration_min: $dur, train_type: $train}]->(to)
                CREATE (to)-[:CONNECTED_BY_RAIL {distance_km: $dist, duration_min: $dur, train_type: $train}]->(from)
            """, a=a, b=b, dist=dist, dur=dur, train=train)
            count += 2
        print("Memgraph: створено", len(STATIONS), "станцій та", count, "зв'язків")


if __name__ == "__main__":
    auth = (MEMGRAPH_USER, MEMGRAPH_PASSWORD) if MEMGRAPH_USER else ("", "")
    driver = GraphDatabase.driver(MEMGRAPH_URI, auth=auth)
    try:
        driver.verify_connectivity()
        seed(driver)
    finally:
        driver.close()
