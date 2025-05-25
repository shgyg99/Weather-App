import asyncio
from database import Base, engine
from models import WeatherEntry

async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

asyncio.run(init_models())
