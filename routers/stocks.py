import os
import requests
from fastapi import APIRouter, Query
from services.price_service import get_price, get_price_history, get_stock_performance, get_stock_fundamentals

router = APIRouter(prefix="/stocks", tags=["stocks"])

@router.get("/search")
def search_stocks(q: str = Query(..., min_length=2)):
    api_key = os.getenv("TWELVE_DATA_API_KEY")
    if not api_key:
        return []

    query = q.strip().lower()

    try:
        response = requests.get(
            "https://api.twelvedata.com/symbol_search",
            params={"symbol": q, "apikey": api_key},
            timeout=10,
        )

        data = response.json()
        raw_items = data.get("data", [])
        results = []

        for item in raw_items:
            symbol = item.get("symbol")
            name = item.get("instrument_name")
            exchange = item.get("exchange")
            country = item.get("country")
            instrument_type = item.get("instrument_type") or ""

            if not symbol or not name:
                continue

            ticker = symbol
            if exchange in ["XETR", "XETRA"] or country == "Germany":
                ticker = f"{symbol}.DE"

            results.append({
                "ticker": ticker,
                "name": name,
                "exchange": exchange,
                "country": country,
                "instrument_type": instrument_type,
                "score": score_stock_result(
                    query=query,
                    symbol=symbol,
                    name=name,
                    exchange=exchange,
                    country=country,
                    instrument_type=instrument_type,
                ),
            })

        results.sort(key=lambda x: x["score"], reverse=True)

        return [
            {
                "ticker": r["ticker"],
                "name": r["name"],
                "exchange": r["exchange"],
                "country": r["country"],
            }
            for r in results[:10]
        ]

    except Exception as e:
        print(f"Stock search failed: {e}")
        return []


def score_stock_result(query, symbol, name, exchange, country, instrument_type):
    score = 0

    symbol_l = (symbol or "").lower()
    name_l = (name or "").lower()
    exchange_l = (exchange or "").upper()
    country_l = (country or "").lower()
    type_l = (instrument_type or "").lower()

    # Exakte Treffer stark bevorzugen
    if symbol_l == query:
        score += 100
    if name_l == query:
        score += 90

    # Beginnt mit Suchbegriff
    if symbol_l.startswith(query):
        score += 70
    if name_l.startswith(query):
        score += 60

    # Enthält Suchbegriff
    if query in symbol_l:
        score += 35
    if query in name_l:
        score += 30

    # Große / relevante Börsen bevorzugen
    if exchange_l in ["NASDAQ", "NYSE"]:
        score += 35
    if exchange_l in ["XETR", "XETRA"]:
        score += 30
    if exchange_l in ["LSE", "LON"]:
        score += 15

    # Länder bevorzugen
    if country_l in ["united states", "usa"]:
        score += 25
    if country_l == "germany":
        score += 25

    # Aktien bevorzugen
    if "common stock" in type_l or "stock" in type_l or "equity" in type_l:
        score += 20

    # Nebenbörsen leicht abwerten
    if exchange_l in ["OTC", "PINK"]:
        score -= 40

    return score


@router.get("/{ticker}/price")
def stock_price(ticker: str):
    return {"ticker": ticker.upper(), "price": get_price(ticker)}

@router.get("/{ticker}/history")
def stock_history(ticker: str, range: str = "6m"):
    return {
        "ticker": ticker.upper(),
        "range": range,
        "history": get_price_history(ticker, range),
         "performance": get_stock_performance(ticker),
    }
    
@router.get("/{ticker}/fundamentals")
def stock_fundamentals(ticker: str):
    return {
        "ticker": ticker.upper(),
        "fundamentals": get_stock_fundamentals(ticker),
    }
    
@router.get("/{ticker}/news")
def stock_news(ticker: str):
    return {
        "ticker": ticker.upper(),
        "news": get_stock_news(ticker)
    }
    