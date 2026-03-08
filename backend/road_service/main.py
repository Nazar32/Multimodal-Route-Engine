"""
Road Service — аналіз автодоріг.
Розраховує маршрути з урахуванням відстані та швидкості.
Використовує Neo4J для пошуку шляхів.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from db import get_places as db_get_places, find_routes as db_find_routes, is_available as db_available

app = FastAPI(title="Road Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Fallback при відсутності Neo4J
FALLBACK_PLACES = [
    {"name": "Київ", "id": "kyiv", "type": "city", "lat": 50.4501, "lon": 30.5234},
    {"name": "Львів", "id": "lviv", "type": "city", "lat": 49.8397, "lon": 24.0297},
    {"name": "Одеса", "id": "odesa", "type": "city", "lat": 46.4825, "lon": 30.7233},
    {"name": "Харків", "id": "kharkiv", "type": "city", "lat": 49.9935, "lon": 36.2304},
    {"name": "Дніпро", "id": "dnipro", "type": "city", "lat": 48.4647, "lon": 35.0462},
    {"name": "Запоріжжя", "id": "zaporizhzhia", "type": "city", "lat": 47.8388, "lon": 35.1396},
    {"name": "Вінниця", "id": "vinnytsia", "type": "city", "lat": 49.2328, "lon": 28.4681},
    {"name": "Чернігів", "id": "chernihiv", "type": "city", "lat": 51.4982, "lon": 31.2893},
]
ROAD_GRAPH = {
    ("Київ", "Львів"): (540, 90), ("Київ", "Одеса"): (475, 90), ("Київ", "Харків"): (481, 110),
    ("Київ", "Дніпро"): (478, 110), ("Київ", "Вінниця"): (268, 90), ("Київ", "Чернігів"): (145, 90),
    ("Львів", "Вінниця"): (365, 90), ("Одеса", "Вінниця"): (428, 90),
    ("Харків", "Дніпро"): (218, 110), ("Дніпро", "Запоріжжя"): (85, 110),
}


class RouteRequest(BaseModel):
    departure: str
    arrival: str


def _mock_routes(departure: str, arrival: str) -> list[dict]:
    key = (departure, arrival)
    rev = (arrival, departure)
    if key not in ROAD_GRAPH and rev not in ROAD_GRAPH:
        return []
    dist, speed = ROAD_GRAPH.get(key) or ROAD_GRAPH.get(rev)
    duration = int(dist / speed * 60)
    return [{
        "segments": [{
            "transport": "road", "from_place": departure, "to_place": arrival,
            "distance_km": dist, "duration_min": duration, "details": {"speed_limit": speed},
        }],
        "total_distance_km": dist, "total_duration_min": duration, "transport_types": ["road"],
    }]


@app.get("/places")
async def get_places():
    if db_available():
        return db_get_places()
    return FALLBACK_PLACES


@app.post("/routes")
async def find_routes(request: RouteRequest):
    if db_available():
        routes = db_find_routes(request.departure, request.arrival)
        if routes:
            return {"routes": routes}
    return {"routes": _mock_routes(request.departure, request.arrival)}


@app.get("/health")
async def health():
    return {"status": "ok", "neo4j": db_available()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
