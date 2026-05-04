from pydantic import BaseModel, Field
from typing import Optional
from pydantic import BaseModel

class PositionCreate(BaseModel):
    ticker: str
    name: str = ""
    quantity: float = Field(gt=0)
    buy_price: float = Field(gt=0)
    buy_date: str = ""
    currency: str = "EUR"

class PositionOut(PositionCreate):
    id: int
    current_price: Optional[float] = None
    current_price_eur: Optional[float] = None
    current_currency: Optional[str] = None
    current_value: Optional[float] = None
    profit_loss: Optional[float] = None
    profit_loss_pct: Optional[float] = None
    daily_change_pct: float | None = None

    class Config:
        from_attributes = True

class WatchlistCreate(BaseModel):
    ticker: str
    name: str = ""
    note: str = ""

class WatchlistOut(WatchlistCreate):
    id: int
    current_price: Optional[float] = None
    current_price_eur: Optional[float] = None
    current_currency: Optional[str] = None
    daily_change_pct: float | None = None

    class Config:
        from_attributes = True

class AnalyzeRequest(BaseModel):
    ticker: str
    name: str = ""
    quantity: float | None = None
    buy_price: float | None = None
    current_price: float | None = None

class AnalysisOut(BaseModel):
    id: int
    ticker: str
    analysis_text: str
    risk_score: int
    class Config:
        from_attributes = True

class InvestmentIdeaRequest(BaseModel):
    horizon: str
    risk_level: str
    goal: str
    region: str
    amount: float | None = None
    exclusions: str | None = None
    sector: str | None = None
    market_cap: str | None = None
    popularity: str | None = None

class InvestmentIdeaOut(BaseModel):
    analysis_text: str
    risk_score: int