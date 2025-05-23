from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os

app = FastAPI()

# تنظیم CORS (اینجا برای همین پروژه فقط)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # موقتاً همه منابع مجاز
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = "4d1943b2553231af7d58e8a46cf873f6"  # کلید API خودت رو اینجا بذار

@app.get("/")
async def read_index():
    file_path = os.path.join("static", "index.html")
    return FileResponse(file_path)

@app.get("/weather")
async def get_weather(location: str = Query(..., description="City name or zip code")):
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={location}&appid={API_KEY}"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
    
    if response.status_code != 200:
        raise HTTPException(status_code=404, detail="Location not found or API error")
    
    data = response.json()
    result = {
        "location": data.get("name"),
        "temperature": data["main"]["temp"],
        "weather": data["weather"][0]["description"],
        "icon": data["weather"][0]["icon"]
    }
    return result
