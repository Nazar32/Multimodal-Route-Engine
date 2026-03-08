"""
Aggregator Service — фасад системи.
Оркеструє запити до Road та Railway сервісів, об'єднує маршрути.
"""
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import os
import httpx

app = FastAPI(title="Multimodal Routes Aggregator")

ROAD_SERVICE_URL = os.getenv("ROAD_SERVICE_URL", "http://localhost:8001")
RAILWAY_SERVICE_URL = os.getenv("RAILWAY_SERVICE_URL", "http://localhost:8002")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RouteRequest(BaseModel):
    departure: str
    arrival: str


class RouteSegment(BaseModel):
    transport: str
    from_place: str
    to_place: str
    distance_km: Optional[float] = None
    duration_min: Optional[int] = None
    details: Optional[dict] = None


class Route(BaseModel):
    segments: list[RouteSegment]
    total_distance_km: float
    total_duration_min: int
    transport_types: list[str]


class RoutesResponse(BaseModel):
    departure: str
    arrival: str
    routes: list[Route]


@app.get("/places")
async def get_places():
    """Отримати список населених пунктів з обох сервісів."""
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            road_resp = await client.get(f"{ROAD_SERVICE_URL}/places")
            railway_resp = await client.get(f"{RAILWAY_SERVICE_URL}/places")
            road_places = road_resp.json() if road_resp.status_code == 200 else []
            railway_places = railway_resp.json() if railway_resp.status_code == 200 else []
            # Об'єднуємо та дедуплікуємо
            all_places = list({p["name"]: p for p in road_places + railway_places}.values())
            return sorted(all_places, key=lambda x: x["name"])
        except httpx.ConnectError:
            # Fallback: повертаємо статичний список для локальної розробки
            return [
                {"name": "Київ", "id": "kyiv", "type": "city"},
                {"name": "Львів", "id": "lviv", "type": "city"},
                {"name": "Одеса", "id": "odesa", "type": "city"},
                {"name": "Харків", "id": "kharkiv", "type": "city"},
                {"name": "Дніпро", "id": "dnipro", "type": "city"},
                {"name": "Запоріжжя", "id": "zaporizhzhia", "type": "city"},
                {"name": "Вінниця", "id": "vinnytsia", "type": "city"},
                {"name": "Чернігів", "id": "chernihiv", "type": "city"},
            ]


def _route_from_dict(r: dict) -> Route:
    """Нормалізація словника маршруту в Route."""
    segs = []
    for s in r.get("segments", []):
        seg = {k: v for k, v in s.items() if k in ("transport", "from_place", "to_place", "distance_km", "duration_min", "details")}
        segs.append(RouteSegment(**seg))
    return Route(
        segments=segs,
        total_distance_km=r.get("total_distance_km", 0),
        total_duration_min=r.get("total_duration_min", 0),
        transport_types=r.get("transport_types", []),
    )


def _compose_multimodal(
    road_leg: dict, rail_leg: dict, transfer_point: str
) -> Route:
    """Компонування одного мультимодального маршруту з двох сегментів."""
    segs = []
    total_km = 0.0
    total_min = 0
    for leg in [road_leg, rail_leg]:
        for s in leg.get("segments", []):
            segs.append(RouteSegment(
                transport=s.get("transport", ""),
                from_place=s.get("from_place", ""),
                to_place=s.get("to_place", ""),
                distance_km=s.get("distance_km"),
                duration_min=s.get("duration_min"),
                details=s.get("details"),
            ))
        total_km += leg.get("total_distance_km", 0)
        total_min += leg.get("total_duration_min", 0)
    return Route(
        segments=segs,
        total_distance_km=total_km,
        total_duration_min=total_min,
        transport_types=["road", "railway"],
    )


@app.post("/routes", response_model=RoutesResponse)
async def find_routes(request: RouteRequest):
    """Знайти мультимодальні маршрути: прямі (авто/залізниця) + комбіновані (пересадка)."""
    A, B = request.departure, request.arrival
    async with httpx.AsyncClient(timeout=10.0) as client:
        road_routes = []
        railway_routes = []
        road_places = set()
        railway_places = set()

        try:
            road_resp = await client.post(
                f"{ROAD_SERVICE_URL}/routes",
                json={"departure": A, "arrival": B},
            )
            if road_resp.status_code == 200:
                road_routes = road_resp.json().get("routes", [])
            places_resp = await client.get(f"{ROAD_SERVICE_URL}/places")
            if places_resp.status_code == 200:
                road_places = {p["name"] for p in places_resp.json()}
        except httpx.ConnectError:
            pass

        try:
            railway_resp = await client.post(
                f"{RAILWAY_SERVICE_URL}/routes",
                json={"departure": A, "arrival": B},
            )
            if railway_resp.status_code == 200:
                railway_routes = railway_resp.json().get("routes", [])
            places_resp = await client.get(f"{RAILWAY_SERVICE_URL}/places")
            if places_resp.status_code == 200:
                railway_places = {p["name"] for p in places_resp.json()}
        except httpx.ConnectError:
            pass

    all_routes: list[Route] = []

    # 1. Прямі маршрути (лише авто)
    for r in road_routes:
        all_routes.append(_route_from_dict(r))

    # 2. Прямі маршрути (лише залізниця)
    for r in railway_routes:
        all_routes.append(_route_from_dict(r))

    # 3. Мультимодальні: пересадка в проміжній точці
    transfer_points = (road_places & railway_places) - {A, B}
    for T in transfer_points:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                road_a_t = await client.post(
                    f"{ROAD_SERVICE_URL}/routes",
                    json={"departure": A, "arrival": T},
                )
                rail_t_b = await client.post(
                    f"{RAILWAY_SERVICE_URL}/routes",
                    json={"departure": T, "arrival": B},
                )
                if road_a_t.status_code == 200 and rail_t_b.status_code == 200:
                    r1 = road_a_t.json().get("routes", [])
                    r2 = rail_t_b.json().get("routes", [])
                    if r1 and r2:
                        # Авто A→T + Залізниця T→B (беремо найшвидший варіант)
                        road_leg = min(r1, key=lambda x: x.get("total_duration_min", 0))
                        rail_leg = min(r2, key=lambda x: x.get("total_duration_min", 0))
                        all_routes.append(_compose_multimodal(road_leg, rail_leg, T))

                rail_a_t = await client.post(
                    f"{RAILWAY_SERVICE_URL}/routes",
                    json={"departure": A, "arrival": T},
                )
                road_t_b = await client.post(
                    f"{ROAD_SERVICE_URL}/routes",
                    json={"departure": T, "arrival": B},
                )
                if rail_a_t.status_code == 200 and road_t_b.status_code == 200:
                    r1 = rail_a_t.json().get("routes", [])
                    r2 = road_t_b.json().get("routes", [])
                    if r1 and r2:
                        # Залізниця A→T + Авто T→B
                        rail_leg = min(r1, key=lambda x: x.get("total_duration_min", 0))
                        road_leg = min(r2, key=lambda x: x.get("total_duration_min", 0))
                        all_routes.append(_compose_multimodal(rail_leg, road_leg, T))
        except httpx.ConnectError:
            continue

    # Сортуємо за часом
    all_routes.sort(key=lambda r: r.total_duration_min)

    if not all_routes:
        all_routes = _get_mock_routes(A, B)

    return RoutesResponse(departure=A, arrival=B, routes=all_routes)


def _get_mock_routes(departure: str, arrival: str) -> list[Route]:
    """Mock маршрути для локальної розробки без БД."""
    mock_data = {
        ("Київ", "Львів"): [
            Route(
                segments=[
                    RouteSegment(transport="road", from_place="Київ", to_place="Львів", distance_km=540, duration_min=360, details={"speed_limit": 90}),
                ],
                total_distance_km=540,
                total_duration_min=360,
                transport_types=["road"],
            ),
            Route(
                segments=[
                    RouteSegment(transport="railway", from_place="Київ", to_place="Львів", duration_min=330, details={"train_type": "Інтерсіті"}),
                ],
                total_distance_km=540,
                total_duration_min=330,
                transport_types=["railway"],
            ),
        ],
        ("Київ", "Одеса"): [
            Route(
                segments=[
                    RouteSegment(transport="road", from_place="Київ", to_place="Одеса", distance_km=475, duration_min=330, details={"speed_limit": 90}),
                ],
                total_distance_km=475,
                total_duration_min=330,
                transport_types=["road"],
            ),
            Route(
                segments=[
                    RouteSegment(transport="railway", from_place="Київ", to_place="Одеса", duration_min=420, details={"train_type": "Нічний"}),
                ],
                total_distance_km=475,
                total_duration_min=420,
                transport_types=["railway"],
            ),
        ],
    }
    key = (departure, arrival)
    if key in mock_data:
        return mock_data[key]
    # Загальний mock для будь-якої пари
    return [
        Route(
            segments=[
                RouteSegment(transport="road", from_place=departure, to_place=arrival, distance_km=200, duration_min=150),
            ],
            total_distance_km=200,
            total_duration_min=150,
            transport_types=["road"],
        ),
        Route(
            segments=[
                RouteSegment(transport="railway", from_place=departure, to_place=arrival, duration_min=180),
            ],
            total_distance_km=200,
            total_duration_min=180,
            transport_types=["railway"],
        ),
    ]


# Статичні файли фронтенду — після API-маршрутів
# Шлях до frontend: локально — ../../frontend, в Docker — ../frontend
_frontend = Path(__file__).resolve().parent.parent.parent / "frontend"
if not _frontend.exists():
    _frontend = Path(__file__).resolve().parent.parent / "frontend"
if _frontend.exists():
    app.mount("/", StaticFiles(directory=_frontend, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
