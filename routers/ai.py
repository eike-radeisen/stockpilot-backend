from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import AiAnalysis, DEMO_USER_ID
from schemas import AnalyzeRequest, AnalysisOut, InvestmentIdeaRequest, InvestmentIdeaOut
from services.price_service import get_price, get_stock_fundamentals, get_stock_performance, get_stock_news
from services.ai_service import create_ai_analysis, create_investment_ideas, create_fundamental_analysis, create_news_analysis

router = APIRouter(prefix="/ai", tags=["ai"])

@router.post("/analyze-position", response_model=AnalysisOut)
def analyze_position(payload: AnalyzeRequest, db: Session = Depends(get_db)):
    text, risk = create_ai_analysis(
        ticker=payload.ticker.upper(), name=payload.name,
        quantity=payload.quantity, buy_price=payload.buy_price,
        current_price=payload.current_price,
    )
    row = AiAnalysis(user_id=DEMO_USER_ID, ticker=payload.ticker.upper(), analysis_text=text, risk_score=risk)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
    
@router.post("/fundamental-analysis")
def fundamental_analysis(payload: AnalyzeRequest):
    ticker = payload.ticker.upper()

    price_data = get_price(ticker)
    fundamentals = get_stock_fundamentals(ticker)
    performance = get_stock_performance(ticker)

    text, risk = create_fundamental_analysis(
        ticker=ticker,
        name=payload.name,
        price_data=price_data,
        fundamentals=fundamentals,
        performance=performance,
    )

    return {
        "ticker": ticker,
        "analysis_text": text,
        "risk_score": risk,
    }
    
@router.post("/news-analysis")
def news_analysis(payload: dict):
    ticker = payload.get("ticker")
    name = payload.get("name")

    news = get_stock_news(ticker, name)

    text, risk = create_news_analysis(
        ticker=ticker,
        name=name,
        news=news
    )

    return {
        "ticker": ticker,
        "analysis_text": text,
        "risk_score": risk
    }

@router.post("/investment-ideas")
def investment_ideas(payload: dict):
    ideas = create_investment_ideas(**payload)
    return ideas
    
