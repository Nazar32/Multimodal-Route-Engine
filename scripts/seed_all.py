#!/usr/bin/env python3
"""
Автоматичне заповнення Neo4J та Memgraph.
Запускається при старті контейнерів, якщо:
- SEED_DB=true (примусово)
- або дані ще не заповнені (перший запуск)
"""
import os
import sys
import time
from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
MEMGRAPH_URI = os.getenv("MEMGRAPH_URI", "bolt://localhost:7687")
MEMGRAPH_USER = os.getenv("MEMGRAPH_USER", "")
MEMGRAPH_PASSWORD = os.getenv("MEMGRAPH_PASSWORD", "")
SEED_DB = os.getenv("SEED_DB", "").lower() in ("1", "true", "yes")


def wait_for_db(uri: str, auth, name: str, max_attempts: int = 60) -> bool:
    for i in range(max_attempts):
        try:
            driver = GraphDatabase.driver(uri, auth=auth)
            driver.verify_connectivity()
            driver.close()
            return True
        except Exception:
            if i == 0:
                print(f"Очікування {name}...", flush=True)
            time.sleep(2)
    return False


def count_nodes(uri: str, auth, label: str) -> int:
    try:
        driver = GraphDatabase.driver(uri, auth=auth)
        with driver.session() as session:
            r = session.run(f"MATCH (n:{label}) RETURN count(n) AS c").single()
            count = r["c"] if r else 0
        driver.close()
        return count
    except Exception:
        return 0


def run_seed_neo4j():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import seed_neo4j
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        seed_neo4j.seed(driver)
    finally:
        driver.close()


def run_seed_memgraph():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import seed_memgraph
    auth = (MEMGRAPH_USER, MEMGRAPH_PASSWORD) if MEMGRAPH_USER else ("", "")
    driver = GraphDatabase.driver(MEMGRAPH_URI, auth=auth)
    try:
        seed_memgraph.seed(driver)
    finally:
        driver.close()


def main():
    if not wait_for_db(NEO4J_URI, (NEO4J_USER, NEO4J_PASSWORD), "Neo4J"):
        print("Neo4J недоступна", file=sys.stderr)
        sys.exit(1)
    if not wait_for_db(MEMGRAPH_URI, (MEMGRAPH_USER, MEMGRAPH_PASSWORD) if MEMGRAPH_USER else ("", ""), "Memgraph"):
        print("Memgraph недоступний", file=sys.stderr)
        sys.exit(1)

    neo4j_count = count_nodes(NEO4J_URI, (NEO4J_USER, NEO4J_PASSWORD), "City")
    memgraph_auth = (MEMGRAPH_USER, MEMGRAPH_PASSWORD) if MEMGRAPH_USER else ("", "")
    memgraph_count = count_nodes(MEMGRAPH_URI, memgraph_auth, "Station")

    if not SEED_DB and neo4j_count > 0 and memgraph_count > 0:
        print("Дані вже заповнені, пропуск (SEED_DB=true для примусового заповнення)")
        sys.exit(0)

    print("Заповнення Neo4J...")
    run_seed_neo4j()
    print("Заповнення Memgraph...")
    run_seed_memgraph()
    print("Готово.")


if __name__ == "__main__":
    main()
