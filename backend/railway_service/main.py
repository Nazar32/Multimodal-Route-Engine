"""
Railway Service — аналіз залізниці.
Розраховує маршрути потягом, враховує розклад та типи потягів.
Використовує Memgraph для пошуку шляхів.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from db import get_places as db_get_places, find_routes as db_find_routes, is_available as db_available

app = FastAPI(title="Railway Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Fallback при відсутності Memgraph
FALLBACK_PLACES = [
    {"name": "Київ", "id": "kyiv", "type": "station"},
    {"name": "Львів", "id": "lviv", "type": "station"},
    {"name": "Одеса", "id": "odesa", "type": "station"},
    {"name": "Харків", "id": "kharkiv", "type": "station"},
    {"name": "Дніпро", "id": "dnipro", "type": "station"},
    {"name": "Запоріжжя", "id": "zaporizhzhia", "type": "station"},
    {"name": "Вінниця", "id": "vinnytsia", "type": "station"},
    {"name": "Чернігів", "id": "chernihiv", "type": "station"},
]
RAILWAY_GRAPH = {
    ("Київ", "Львів"): [(540, 330, "Інтерсіті"), (540, 420, "Нічний")],
    ("Київ", "Одеса"): [(475, 420, "Нічний"), (475, 510, "Пасажирський")],
    ("Київ", "Харків"): [(481, 300, "Інтерсіті"), (481, 420, "Швидкий")],
    ("Київ", "Дніпро"): [(478, 360, "Інтерсіті")],
    ("Київ", "Вінниця"): [(268, 180, "Швидкий")],
    ("Київ", "Чернігів"): [(145, 120, "Приміський")],
    ("Львів", "Вінниця"): [(365, 300, "Швидкий")],
    ("Одеса", "Вінниця"): [(428, 360, "Швидкий")],
    ("Харків", "Дніпро"): [(218, 180, "Інтерсіті")],
    ("Дніпро", "Запоріжжя"): [(85, 60, "Приміський")],
}


class RouteRequest(BaseModel):
    departure: str
    arrival: str


def _mock_routes(departure: str, arrival: str) -> list[dict]:
    key = (departure, arrival)
    rev = (arrival, departure)
    connections = RAILWAY_GRAPH.get(key) or RAILWAY_GRAPH.get(rev)
    if not connections:
        return []
    routes = []
    for dist, duration, train_type in connections:
        routes.append({
            "segments": [{
                "transport": "railway", "from_place": departure, "to_place": arrival,
                "distance_km": dist, "duration_min": duration, "details": {"train_type": train_type},
            }],
            "total_distance_km": dist, "total_duration_min": duration, "transport_types": ["railway"],
        })
    return routes


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
    return {"status": "ok", "memgraph": db_available()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
