from sqlalchemy import Column, Integer, String, Float
from database import Base

class WeatherEntry(Base):
    __tablename__ = "weather_data"

    id = Column(Integer, primary_key=True, index=True)
    location = Column(String, index=True)
    temperature = Column(Float)
    description = Column(String)
    date = Column(String)
