from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Text
from database import Base

DEMO_USER_ID = 1

class Position(Base):
    __tablename__ = "positions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, default=DEMO_USER_ID, index=True)
    ticker = Column(String, index=True, nullable=False)
    name = Column(String, default="")
    quantity = Column(Float, nullable=False)
    buy_price = Column(Float, nullable=False)
    buy_date = Column(String, default="")
    currency = Column(String, default="EUR")
    created_at = Column(DateTime, default=datetime.utcnow)

class WatchlistItem(Base):
    __tablename__ = "watchlist"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, default=DEMO_USER_ID, index=True)
    ticker = Column(String, index=True, nullable=False)
    name = Column(String, default="")
    note = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

class AiAnalysis(Base):
    __tablename__ = "ai_analyses"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, default=DEMO_USER_ID, index=True)
    ticker = Column(String, index=True, nullable=False)
    analysis_text = Column(Text, nullable=False)
    risk_score = Column(Integer, default=50)
    created_at = Column(DateTime, default=datetime.utcnow)
