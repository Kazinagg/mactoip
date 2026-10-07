from contextlib import asynccontextmanager
from typing import Optional
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, HTMLResponse
from sqlalchemy.orm import Session

from mactoip.database import get_db, init_db
from mactoip.utils import normalize_mac
from mactoip.schemas import (
    HeartbeatRequest,
    HeartbeatResponse,
    DeviceResponse,
    DeviceIPResponse,
    DeviceUpdateRequest,
)
from mactoip import crud
from mactoip.config import HOST, PORT

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="MAC-to-IP Registry",
    description="Централизованный сервер учета и разрешения IP-адресов контроллеров Wiren Board по MAC-адресам",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _build_device_response(device) -> DeviceResponse:
    return DeviceResponse(
        id=device.id,
        mac=device.mac,
        ip=device.ip,
        hostname=device.hostname,
        comment=device.comment,
        first_seen=device.first_seen,
        last_seen=device.last_seen,
        update_count=device.update_count,
    )

@app.get("/api/health", tags=["System"])
def health_check(db: Session = Depends(get_db)):
    devices = crud.get_all_devices(db)
    return {
        "status": "ok",
        "total_devices": len(devices),
    }

@app.post(
    "/api/devices/heartbeat",
    response_model=HeartbeatResponse,
    summary="Регистрация / обновление устройства (Heartbeat)",
    tags=["Devices"],
)
@app.post(
    "/api/devices/register",
    response_model=HeartbeatResponse,
    include_in_schema=False,
)
def device_heartbeat(payload: HeartbeatRequest, db: Session = Depends(get_db)):
    """
    Принимает MAC и текущий IP от контроллера:
    - Если устройство новое — сохраняет в базе данных (`created`).
    - Если устройство уже есть и IP изменился — обновляет IP (`ip_updated`).
    - Если устройство уже есть и IP тот же — обновляет метку времени last_seen (`heartbeat`).
    """
    device, state = crud.upsert_device(db, payload)

    messages = {
        "created": f"Новое устройство {device.mac} успешно зарегистрировано",
        "ip_updated": f"IP устройства {device.mac} обновлен на {device.ip}",
        "heartbeat": f"Данные устройства {device.mac} актуализированы",
    }

    return HeartbeatResponse(
        status=state,
        message=messages.get(state, "OK"),
        device=_build_device_response(device),
    )

@app.get(
    "/api/devices",
    response_model=list[DeviceResponse],
    summary="Получить список всех устройств",
    tags=["Devices"],
)
def list_devices(
    search: Optional[str] = Query(None, description="Фильтр по части MAC, IP, Hostname или комментарию"),
    db: Session = Depends(get_db),
):
    """Возвращает список всех зарегистрированных устройств с датами первого и последнего обновления."""
    devices = crud.get_all_devices(db)
    result = []
    
    search_lower = search.lower().strip() if search else None

    for dev in devices:
        if search_lower:
            match_mac = search_lower in dev.mac.lower()
            match_ip = search_lower in dev.ip.lower()
            match_host = bool(dev.hostname and search_lower in dev.hostname.lower())
            match_comment = bool(dev.comment and search_lower in dev.comment.lower())
            if not (match_mac or match_ip or match_host or match_comment):
                continue

        result.append(_build_device_response(dev))

    return result

@app.get(
    "/api/devices/{mac}",
    response_model=DeviceResponse,
    summary="Получить информацию об устройстве по MAC",
    tags=["Devices"],
)
def get_device(mac: str, db: Session = Depends(get_db)):
    """Возвращает детальную информацию об устройстве по его MAC-адресу."""
    try:
        norm_mac = normalize_mac(mac)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    device = crud.get_device_by_mac(db, norm_mac)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Устройство с MAC-адресом '{norm_mac}' не найдено",
        )

    return _build_device_response(device)

@app.get(
    "/api/devices/{mac}/ip",
    summary="Получить текущий IP-адрес по MAC",
    tags=["Devices"],
    responses={
        200: {
            "content": {
                "application/json": {},
                "text/plain": {"example": "192.168.1.120"},
            }
        }
    },
)
def get_device_ip(
    mac: str,
    output_format: str = Query("json", alias="format", description="Формат вывода: 'json' или 'text'"),
    db: Session = Depends(get_db),
):
    """
    Возвращает текущий IP-адрес устройства по MAC.
    Удобно для скриптов автоматизации: при ?format=text возвращает чистый IP.
    """
    try:
        norm_mac = normalize_mac(mac)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    device = crud.get_device_by_mac(db, norm_mac)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Устройство с MAC '{norm_mac}' не найдено",
        )

    if output_format.lower() in ("text", "plain"):
        return PlainTextResponse(content=device.ip)

    return DeviceIPResponse(
        mac=device.mac,
        ip=device.ip,
        last_seen=device.last_seen,
        update_count=device.update_count,
    )

@app.patch(
    "/api/devices/{mac}",
    response_model=DeviceResponse,
    summary="Обновить метаданные устройства (hostname, комментарий)",
    tags=["Devices"],
)
def update_device(
    mac: str,
    payload: DeviceUpdateRequest,
    db: Session = Depends(get_db),
):
    """Позволяет вручную назначить человекопонятное имя или комментарий (локацию) устройству."""
    try:
        norm_mac = normalize_mac(mac)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    device = crud.update_device_meta(db, norm_mac, payload)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Устройство с MAC '{norm_mac}' не найдено",
        )

    return _build_device_response(device)

@app.delete(
    "/api/devices/{mac}",
    summary="Удалить устройство из реестра",
    tags=["Devices"],
)
def delete_device(mac: str, db: Session = Depends(get_db)):
    """Удаляет устройство из базы данных."""
    try:
        norm_mac = normalize_mac(mac)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    deleted = crud.delete_device_by_mac(db, norm_mac)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Устройство с MAC '{norm_mac}' не найдено",
        )

    return {"status": "deleted", "mac": norm_mac}

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index_view():
    """Отдает страницу веб-интерфейса мониторинга устройств."""
    html_file = Path(__file__).resolve().parent / "static" / "index.html"
    if html_file.exists():
        return HTMLResponse(content=html_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>MAC-to-IP Registry API</h1><p>Документация доступна на <a href='/docs'>/docs</a></p>")

def start():
    """Точка входа для запуска через консоль или скрипт."""
    import uvicorn
    uvicorn.run("mactoip.main:app", host=HOST, port=PORT, reload=True)

if __name__ == "__main__":
    start()
