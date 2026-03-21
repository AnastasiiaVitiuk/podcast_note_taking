from sqlalchemy import Column, Integer, Text, Boolean, Float
from app.db import Base

class Episode(Base):
    __tablename__ = "episodes"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(Text)
    transcript = Column(Text)

class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    episode_id = Column(Integer, index=True)
    content = Column(Text)
    timestamp = Column(Float, nullable=True)
    is_full = Column(Boolean, default=False)