# Мультимодальні маршрути — Авто та Залізниця

Застосунок для побудови маршрутів (автомобіль + залізниця) з гетерогенними даними. Курс «Гетерогенні розподілені бази даних», Бригада 1.

## Архітектура

- **Aggregator** (8080) — фасад, компонує маршрути з обох сервісів (прямі + мультимодальні з пересадкою)
- **Road Service** (8001) — Neo4J, пошук шляхів по автодорогах
- **Railway Service** (8002) — Memgraph, пошук шляхів по залізниці
- **Neo4J** (7687) — граф автодоріг
- **Memgraph** (7688 на хості) — граф залізниці

## Заповнення БД

**Docker**: seed запускається автоматично при `docker compose up`:
- перший запуск — заповнює БД
- наступні — пропускає, якщо дані ще є
- `SEED_DB=true` — примусове заповнення

**Локально**:
```bash
pip install neo4j
./scripts/run_seed.sh
# або: python scripts/seed_all.py
```

## Локальний запуск (без Docker)

**Швидкий тест** (лише агрегатор, mock-дані):
```bash
cd backend && pip install -r requirements.txt
cd aggregator && uvicorn main:app --reload --port 8080
```
Відкрити http://localhost:8080

**Повний запуск з БД** (Neo4J + Memgraph + 3 сервіси):
```bash
# 1. Запустити Neo4J та Memgraph (Docker)
docker run -d -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:5-community
docker run -d -p 7688:7687 memgraph/memgraph-platform

# 2. Заповнити БД
python scripts/seed_neo4j.py
MEMGRAPH_URI=bolt://localhost:7688 python scripts/seed_memgraph.py

# 3. Запустити сервіси (3 термінали)
cd backend/road_service && uvicorn main:app --reload --port 8001
cd backend/railway_service && uvicorn main:app --reload --port 8002
cd backend/aggregator && uvicorn main:app --reload --port 8080
```

## Запуск через Docker

```bash
DOCKER_BUILDKIT=0 docker compose up --build -d
# Seed запускається автоматично, road/railway сервіси чекають на його завершення
```

Відкрити http://localhost:8080

Примусове перезаповнення: `SEED_DB=true docker compose up -d`

## API

- `GET /places` — список населених пунктів
- `POST /routes` — пошук маршрутів (прямі авто/залізниця + мультимодальні з пересадкою)
