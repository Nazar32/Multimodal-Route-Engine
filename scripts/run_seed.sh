#!/bin/bash
# Ручне заповнення Neo4J та Memgraph (локально).
# При docker compose seed запускається автоматично.

set -e
cd "$(dirname "$0")/.."

# Для локального запуску: Neo4J 7687, Memgraph 7688
export NEO4J_URI="${NEO4J_URI:-bolt://localhost:7687}"
export NEO4J_USER="${NEO4J_USER:-neo4j}"
export NEO4J_PASSWORD="${NEO4J_PASSWORD:-password}"
export MEMGRAPH_URI="${MEMGRAPH_URI:-bolt://localhost:7688}"
export SEED_DB="${SEED_DB:-true}"  # примусово при ручному запуску

python scripts/seed_all.py
