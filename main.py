from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
from collections import defaultdict
from config import openwether
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import SessionLocal
from models import WeatherEntry
from sqlalchemy.future import select
from pydantic import BaseModel
from fastapi import Body
from fastapi import Path
from sqlalchemy import func
from sqlalchemy import select




app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

W_API_KEY = openwether

async def validate_city_name(city_name: str) -> bool:
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={W_API_KEY}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
    if response.status_code == 200:
        return True
    return False


@app.get("/")
async def read_index():
    file_path = os.path.join("static", "index.html")
    return FileResponse(file_path)

async def get_db():
    async with SessionLocal() as session:
        yield session

class WeatherEntryCreate(BaseModel):
    location: str
    temperature: float
    description: str
    date: str


@app.post("/weather-db")
async def create_weather_entry(weather: WeatherEntryCreate = Body(...), db: AsyncSession = Depends(get_db)):
    is_valid = await validate_city_name(weather.location)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid city name")

    new_entry = WeatherEntry(
        location=weather.location,
        temperature=weather.temperature,
        description=weather.description,
        date=weather.date,
    )
    db.add(new_entry)
    await db.commit()
    await db.refresh(new_entry)
    return new_entry


@app.get("/weather-db")
async def read_all_entries(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WeatherEntry))
    return result.scalars().all()


@app.put("/weather-db/{entry_id}")
async def update_entry(
    entry_id: int,
    weather: WeatherEntryCreate = Body(...),
    db: AsyncSession = Depends(get_db)
):
    is_valid = await validate_city_name(weather.location)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid city name")

    result = await db.execute(select(WeatherEntry).where(WeatherEntry.id == entry_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    entry.location = weather.location
    entry.temperature = weather.temperature
    entry.description = weather.description
    entry.date = weather.date

    await db.commit()
    await db.refresh(entry)
    return entry



@app.delete("/weather-db/{entry_id}")
async def delete_entry(entry_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WeatherEntry).where(WeatherEntry.id == entry_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    await db.delete(entry)
    await db.commit()
    return {"message": "Deleted"}


@app.get("/weather")
async def get_weather(
    location: str = Query(None, description="City name or place name"),
    postal: str = Query(None, description="Postal code and Country name such as 94040,us"),
    coords: str = Query(None, description="Coordinates as lat,lon")
):
    if location:
        query = f"q={location}"
    elif postal:
        parts = postal.split(',')
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="Postal must be in 'zip code, country name' format")
        zi, con = parts
        query = f"zip={zi},{con}"

    elif coords:
        # coords format: "lat,lon"
        parts = coords.split(',')
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="Coordinates must be in 'lat,lon' format")
        lat, lon = parts
        query = f"lat={lat.strip()}&lon={lon.strip()}"
        
    else:
        raise HTTPException(status_code=400, detail="No valid location parameter provided")

    url = f"http://api.openweathermap.org/data/2.5/forecast?{query}&appid={W_API_KEY}"

    async with httpx.AsyncClient() as client:
        response = await client.get(url)

    if response.status_code != 200:
        raise HTTPException(status_code=404, detail="Location not found or API error")

    data = response.json()

    first_forecast = data['list'][0]
    weather_info = first_forecast["weather"][0]

    current_weather = {
        "location": data["city"]["name"],
        "temperature_celsius": round(first_forecast["main"]["temp"] - 273.15, 2),
        "weather_description": weather_info["description"],
        "icon": weather_info["icon"],
        "date_time": first_forecast["dt_txt"],
        "wind_speed": first_forecast["wind"]["speed"],
        "humidity": first_forecast["main"]["humidity"],
        "pressure": first_forecast["main"]["pressure"],
        "visibility": first_forecast.get("visibility", None), 
    }

    daily_data = defaultdict(list)
    for item in data['list']:
        date_str = item['dt_txt'].split(' ')[0]
        daily_data[date_str].append(item)

    forecast_list = []
    for date_str, items in list(daily_data.items())[1:6]:
        temps = [entry['main']['temp'] for entry in items]
        temps_c = [temp - 273.15 for temp in temps]
        max_temp = round(max(temps_c), 1)
        min_temp = round(min(temps_c), 1)
        weather = items[0]['weather'][0]

        forecast_list.append({
            "date": date_str,
            "temp_max": max_temp,
            "temp_min": min_temp,
            "icon": weather['icon'],
            "weather_description": weather['description']
        })

    return {
        "current": current_weather,
        "forecast": forecast_list
    }



@app.get("/forecast")
async def get_forecast(location: str = Query(..., description="City name")):
    return await get_weather(location)
