# main.py
import base64
import os
from datetime import datetime
from typing import Optional

import httpx
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse

# ---------- 1С OData константы ----------
BASE_URL = "https://avibus.gars-ykt.ru:4443/avitest/odata/standard.odata"
USERNAME = "ХАКАТОН"
PASSWORD = "123456"

# ---------- технические helpers ----------
def _basic_headers() -> dict:
    token = base64.b64encode(f"{USERNAME}:{PASSWORD}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {token}"}

async def _odata_get(path: str) -> dict:
    """
    Универсальный GET к 1С с Basic-auth и отключённой проверкой SSL
    (у 1С самоподписанный сертификат)
    """
    url = f"{BASE_URL}/{path}"
    async with httpx.AsyncClient(verify=False, timeout=30) as client:
        resp = await client.get(url, headers=_basic_headers())
    if resp.status_code != 200:
        raise HTTPException(resp.status_code, detail=resp.text[:300])
    # 1С иногда отдаёт BOM – обрежем
    text = resp.text.lstrip("\ufeff")
    try:
        return resp.json()
    except ValueError as e:
        raise HTTPException(502, detail=f"1С вернул не-JSON: {e}  (first-200: {text[:200]})")

# ---------- FastAPI ----------
app = FastAPI(title="1С GARS – точные примеры запросов")

# 1. Маршруты
# GET /Catalog_Маршруты?$format=json
@app.get("/routes")
async def routes():
    return await _odata_get("Catalog_Маршруты?$format=json")

# 2. Тарифы
# GET /Catalog_Тарифы?$format=json
@app.get("/tariffs")
async def tariffs():
    return await _odata_get("Catalog_Тарифы?$format=json")

# 3. Рейсы по датам
# GET /Document_Рейс?$filter=Date ge datetime'2025-01-01T00:00:00' and Date le datetime'2025-01-31T23:59:59'&$format=json
@app.get("/trips")
async def trips(
    date_from: str = Query("2025-01-01", regex=r"\d{4}-\d{2}-\d{2}"),
    date_to: str = Query("2025-01-31", regex=r"\d{4}-\d{2}-\d{2}")
):
    dt_start = datetime.fromisoformat(date_from)
    dt_end = datetime.fromisoformat(date_to).replace(hour=23, minute=59, second=59)
    filter_str = (
        f"Date ge datetime'{dt_start.isoformat(timespec='seconds')}' and "
        f"Date le datetime'{dt_end.isoformat(timespec='seconds')}'"
    )
    path = f"Document_Рейс?$filter={filter_str}&$format=json"
    return await _odata_get(path)

# 4. Расписание рейсов
# GET /InformationRegister_РасписаниеРейсов?$filter=Period ge datetime'2025-01-01T00:00:00' and Period le datetime'2025-01-31T23:59:59'&$format=json
@app.get("/schedule")
async def schedule(
    date_from: str = Query("2025-01-01", regex=r"\d{4}-\d{2}-\d{2}"),
    date_to: str = Query("2025-01-31", regex=r"\d{4}-\d{2}-\d{2}")
):
    dt_start = datetime.fromisoformat(date_from)
    dt_end = datetime.fromisoformat(date_to).replace(hour=23, minute=59, second=59)
    filter_str = (
        f"Period ge datetime'{dt_start.isoformat(timespec='seconds')}' and "
        f"Period le datetime'{dt_end.isoformat(timespec='seconds')}'"
    )
    path = f"InformationRegister_РасписаниеРейсов?$filter={filter_str}&$format=json"
    return await _odata_get(path)

# ---------- запуск ----------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)