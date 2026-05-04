import os
import requests
from functools import lru_cache
from time import time
import yfinance as yf
from datetime import date, timedelta

_NEWS_CACHE = {}
NEWS_TTL_SECONDS = 3 * 60 * 60  # 3 Stunden

_FUNDAMENTALS_CACHE = {}
FUNDAMENTALS_TTL_SECONDS = 24 * 60 * 60

_PRICE_CACHE = {}
_HISTORY_CACHE = {}

PRICE_TTL_SECONDS = 60 * 60
HISTORY_TTL_SECONDS = 24 * 60 * 60

_FX_CACHE = {}
FX_TTL_SECONDS = 12 * 60 * 60




@lru_cache(maxsize=128)
def normalize_ticker(ticker: str) -> str:
    return ticker.strip().upper()

def transform_twelve_data_symbol(symbol: str) -> dict:
    # Deutsche Aktien automatisch umwandeln
    if symbol.endswith(".DE"):
        base = symbol.replace(".DE", "")
        return {"symbol": base, "exchange": "XETR"}

    # Standard (US etc.)
    return {"symbol": symbol}



def get_finnhub_price(symbol: str) -> float | None:
    if symbol.endswith(".DE"):
        return None

    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        return None

    try:
        response = requests.get(
            "https://finnhub.io/api/v1/quote",
            params={"symbol": symbol, "token": api_key},
            timeout=10,
        )
        data = response.json()

        price = data.get("c")
        if price and float(price) > 0:
            return float(price)

        print(f"Finnhub no price for {symbol}: {data}")
        return None

    except Exception as e:
        print(f"Finnhub failed for {symbol}: {e}")
        return None


def get_price(ticker: str) -> dict | None:
    symbol = normalize_ticker(ticker)
    now = time()

    # --- Cache ---
    cached = _PRICE_CACHE.get(symbol)
    if cached and now - cached["ts"] < PRICE_TTL_SECONDS:
        return cached["data"]

    # --- 1. Twelve Data 
    price_data = get_yfinance_price(symbol)

    # --- 2. yfinance fallback ---
    if price_data is None:
        price_data = get_twelve_data_price(symbol)

    # --- speichern ---
    if price_data:
        _PRICE_CACHE[symbol] = {
            "data": price_data,
            "ts": now
        }
        return price_data

    # auch Fehler kurz cachen, damit nicht gespammt wird
    _PRICE_CACHE[symbol] = {"data": None, "ts": now}
    return None
    
def get_twelve_data_price(symbol: str) -> dict | None:
    api_key = os.getenv("TWELVE_DATA_API_KEY")
    if not api_key:
        return None

    try:
        params = transform_twelve_data_symbol(symbol)
        params["apikey"] = api_key

        response = requests.get(
            "https://api.twelvedata.com/price",
            params=params,
            timeout=10,
        )

        data = response.json()
        price = data.get("price")

        if price is not None:
            return {
                "price": float(price),
                "currency": data.get("currency") or guess_currency(symbol),
            }

        print(f"Twelve Data no price for {symbol}: {data}")
        return None

    except Exception as e:
        print(f"Twelve Data failed for {symbol}: {e}")
        return None
        
def guess_currency(symbol: str) -> str:
    if symbol.endswith(".DE"):
        return "EUR"
    return "USD"
        

def get_fx_rate(from_currency: str, to_currency: str = "EUR") -> float | None:
    from_currency = (from_currency or "").upper()
    to_currency = (to_currency or "").upper()

    if not from_currency or not to_currency:
        return None

    if from_currency == to_currency:
        return 1.0

    cache_key = f"{from_currency}_{to_currency}"
    now = time()

    cached = _FX_CACHE.get(cache_key)
    if cached and now - cached["ts"] < FX_TTL_SECONDS:
        return cached["rate"]

    try:
        ticker = yf.Ticker(f"{from_currency}{to_currency}=X")
        hist = ticker.history(period="5d")

        if not hist.empty:
            rate = float(hist["Close"].dropna().iloc[-1])
            _FX_CACHE[cache_key] = {"rate": rate, "ts": now}
            return rate

    except Exception as e:
        print(f"yfinance FX failed for {from_currency}/{to_currency}: {e}")

    _FX_CACHE[cache_key] = {"rate": None, "ts": now}
    return None
    
def get_price_history(ticker: str, range: str = "6m") -> list[dict]:
    symbol = normalize_ticker(ticker)
    cache_key = f"{symbol}_{range}"
    now = time()

    cached = _HISTORY_CACHE.get(cache_key)
    if cached and now - cached["ts"] < HISTORY_TTL_SECONDS:
        return cached["data"]

    api_key = os.getenv("TWELVE_DATA_API_KEY")
    if not api_key:
        return []

    outputsize_by_range = {
        "6m": 130,
        "1y": 260,
        "5y": 1300,
    }

    outputsize = outputsize_by_range.get(range, 130)

    try:
        params = transform_twelve_data_symbol(symbol)
        params.update({
            "apikey": api_key,
            "interval": "1day",
            "outputsize": outputsize,
        })

        response = requests.get(
            "https://api.twelvedata.com/time_series",
            params=params,
            timeout=10,
        )

        data = response.json()
        values = data.get("values", [])

        if not values:
            print(f"No history for {symbol}: {data}")

            rows = get_yfinance_history(symbol, range)

            _HISTORY_CACHE[cache_key] = {"data": rows, "ts": now}
            return rows

        rows = []
        for item in reversed(values):
            rows.append({
                "date": item.get("datetime"),
                "close": float(item.get("close")),
            })

        _HISTORY_CACHE[cache_key] = {"data": rows, "ts": now}
        return rows

    except Exception as e:
        print(f"History lookup failed for {ticker}: {e}")

        rows = get_yfinance_history(symbol, range)

        _HISTORY_CACHE[cache_key] = {"data": rows, "ts": now}
        return rows
        
def calc_performance(rows: list[dict]) -> float | None:
    if len(rows) < 2:
        return None

    first = rows[0].get("close")
    last = rows[-1].get("close")

    if not first or not last:
        return None

    return (last / first - 1.0) * 100.0


def calc_daily_change(rows: list[dict]) -> float | None:
    if len(rows) < 2:
        return None

    previous = rows[-2].get("close")
    last = rows[-1].get("close")

    if not previous or not last:
        return None

    return (last / previous - 1.0) * 100.0


def get_stock_performance(ticker: str) -> dict:
    history_6m = get_price_history(ticker, "6m")
    history_1y = get_price_history(ticker, "1y")
    history_5y = get_price_history(ticker, "5y")

    return {
        "daily": calc_daily_change(history_6m),
        "6m": calc_performance(history_6m),
        "1y": calc_performance(history_1y),
        "5y": calc_performance(history_5y),
    }
    
def safe_float(value):
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def pct_change(new, old):
    new = safe_float(new)
    old = safe_float(old)
    if new is None or old in (None, 0):
        return None
    return (new / old - 1.0) * 100.0


def get_statement_value(statement, keys):
    for key in keys:
        if key in statement.index:
            values = statement.loc[key].dropna()
            if len(values) > 0:
                return values.iloc[0]
    return None


def get_statement_value_previous(statement, keys):
    for key in keys:
        if key in statement.index:
            values = statement.loc[key].dropna()
            if len(values) > 1:
                return values.iloc[1]
    return None


def get_stock_fundamentals(ticker: str) -> dict:
    symbol = normalize_ticker(ticker)
    now = time()

    cached = _FUNDAMENTALS_CACHE.get(symbol)
    if cached and now - cached["ts"] < FUNDAMENTALS_TTL_SECONDS:
        return cached["data"]

    fundamentals = {
        "market_cap": None,
        "enterprise_value": None,
        "pe_ratio": None,
        "forward_pe": None,
        "price_to_book": None,
        "price_to_sales": None,
        "ev_to_ebitda": None,

        "dividend_yield": None,
        "payout_ratio": None,

        "fifty_two_week_high": None,
        "fifty_two_week_low": None,
        "sector": None,
        "industry": None,
        "currency": None,

        "revenue": None,
        "revenue_growth_yoy": None,
        "net_income": None,
        "net_income_growth_yoy": None,
        "gross_margin": None,
        "operating_margin": None,
        "profit_margin": None,
        "ebitda_margin": None,

        "roe": None,
        "roa": None,
        "debt_to_equity": None,
        "total_debt": None,
        "free_cashflow": None,
        "operating_cashflow": None,
        
        "business_summary": None,
        "website": None,
        "country": None,
        "employees": None,
    }

    api_key = os.getenv("TWELVE_DATA_API_KEY")
    if api_key:
        try:
            params = transform_twelve_data_symbol(symbol)
            params["apikey"] = api_key

            stats_response = requests.get(
                "https://api.twelvedata.com/statistics",
                params=params,
                timeout=10,
            )
            stats = stats_response.json()
            s = stats.get("statistics", {})

            fundamentals["market_cap"] = s.get("valuations_metrics", {}).get("market_capitalization")
            fundamentals["pe_ratio"] = s.get("valuations_metrics", {}).get("trailing_pe")
            fundamentals["dividend_yield"] = s.get("dividends_and_splits", {}).get("forward_annual_dividend_yield")
            fundamentals["fifty_two_week_high"] = s.get("stock_price_summary", {}).get("fifty_two_week_high")
            fundamentals["fifty_two_week_low"] = s.get("stock_price_summary", {}).get("fifty_two_week_low")

            profile_response = requests.get(
                "https://api.twelvedata.com/profile",
                params=params,
                timeout=10,
            )
            profile = profile_response.json()

            fundamentals["sector"] = profile.get("sector")
            fundamentals["industry"] = profile.get("industry")
            fundamentals["currency"] = profile.get("currency")

        except Exception as e:
            print(f"Twelve Data fundamentals failed for {symbol}: {e}")

    try:
        yf_ticker = yf.Ticker(symbol)
        info = yf_ticker.info or {}

        fundamentals["market_cap"] = fundamentals["market_cap"] or info.get("marketCap")
        fundamentals["enterprise_value"] = info.get("enterpriseValue")
        fundamentals["pe_ratio"] = fundamentals["pe_ratio"] or info.get("trailingPE")
        fundamentals["forward_pe"] = info.get("forwardPE")
        fundamentals["price_to_book"] = info.get("priceToBook")
        fundamentals["price_to_sales"] = info.get("priceToSalesTrailing12Months")
        fundamentals["ev_to_ebitda"] = info.get("enterpriseToEbitda")

        raw_div_yield = fundamentals["dividend_yield"]
        if raw_div_yield is None:
            raw_div_yield = info.get("dividendYield")

        if raw_div_yield is not None:
            try:
                raw_div_yield = float(raw_div_yield)
                fundamentals["dividend_yield"] = raw_div_yield * 100 if raw_div_yield < 1 else raw_div_yield
            except Exception:
                fundamentals["dividend_yield"] = None

        raw_payout = info.get("payoutRatio")
        if raw_payout is not None:
            raw_payout = float(raw_payout)
            fundamentals["payout_ratio"] = raw_payout * 100 if raw_payout < 1 else raw_payout

        fundamentals["fifty_two_week_high"] = fundamentals["fifty_two_week_high"] or info.get("fiftyTwoWeekHigh")
        fundamentals["fifty_two_week_low"] = fundamentals["fifty_two_week_low"] or info.get("fiftyTwoWeekLow")
        fundamentals["sector"] = fundamentals["sector"] or info.get("sector")
        fundamentals["industry"] = fundamentals["industry"] or info.get("industry")
        fundamentals["currency"] = fundamentals["currency"] or info.get("currency")
        
        fundamentals["business_summary"] = info.get("longBusinessSummary")
        fundamentals["website"] = info.get("website")
        fundamentals["country"] = info.get("country")
        fundamentals["employees"] = info.get("fullTimeEmployees")

        fundamentals["profit_margin"] = (
            float(info["profitMargins"]) * 100 if info.get("profitMargins") is not None else None
        )
        fundamentals["operating_margin"] = (
            float(info["operatingMargins"]) * 100 if info.get("operatingMargins") is not None else None
        )
        fundamentals["gross_margin"] = (
            float(info["grossMargins"]) * 100 if info.get("grossMargins") is not None else None
        )
        fundamentals["ebitda_margin"] = (
            float(info["ebitdaMargins"]) * 100 if info.get("ebitdaMargins") is not None else None
        )
        fundamentals["roe"] = (
            float(info["returnOnEquity"]) * 100 if info.get("returnOnEquity") is not None else None
        )
        fundamentals["roa"] = (
            float(info["returnOnAssets"]) * 100 if info.get("returnOnAssets") is not None else None
        )
        fundamentals["debt_to_equity"] = info.get("debtToEquity")
        fundamentals["total_debt"] = info.get("totalDebt")
        fundamentals["free_cashflow"] = info.get("freeCashflow")
        fundamentals["operating_cashflow"] = info.get("operatingCashflow")
        fundamentals["revenue_growth_yoy"] = (
            float(info["revenueGrowth"]) * 100 if info.get("revenueGrowth") is not None else None
        )

        # Zusätzliche Berechnung aus Statements
        income = yf_ticker.income_stmt

        if income is not None and not income.empty:
            revenue_now = get_statement_value(income, ["Total Revenue", "Operating Revenue"])
            revenue_prev = get_statement_value_previous(income, ["Total Revenue", "Operating Revenue"])

            net_income_now = get_statement_value(income, ["Net Income"])
            net_income_prev = get_statement_value_previous(income, ["Net Income"])

            fundamentals["revenue"] = fundamentals["revenue"] or safe_float(revenue_now)
            fundamentals["revenue_growth_yoy"] = fundamentals["revenue_growth_yoy"] or pct_change(revenue_now, revenue_prev)

            fundamentals["net_income"] = safe_float(net_income_now)
            fundamentals["net_income_growth_yoy"] = pct_change(net_income_now, net_income_prev)

            gross_profit = get_statement_value(income, ["Gross Profit"])
            operating_income = get_statement_value(income, ["Operating Income", "Operating Income or Loss"])
            ebitda = get_statement_value(income, ["EBITDA", "Normalized EBITDA"])

            if revenue_now:
                fundamentals["gross_margin"] = fundamentals["gross_margin"] or (safe_float(gross_profit) / safe_float(revenue_now) * 100 if gross_profit is not None else None)
                fundamentals["operating_margin"] = fundamentals["operating_margin"] or (safe_float(operating_income) / safe_float(revenue_now) * 100 if operating_income is not None else None)
                fundamentals["ebitda_margin"] = fundamentals["ebitda_margin"] or (safe_float(ebitda) / safe_float(revenue_now) * 100 if ebitda is not None else None)
                fundamentals["profit_margin"] = fundamentals["profit_margin"] or (safe_float(net_income_now) / safe_float(revenue_now) * 100 if net_income_now is not None else None)

    except Exception as e:
        print(f"yfinance fundamentals failed for {symbol}: {e}")

    _FUNDAMENTALS_CACHE[symbol] = {"data": fundamentals, "ts": now}
    return fundamentals
    
def get_yfinance_price(symbol: str) -> dict | None:
    try:
        yf_symbol = symbol

        # Yahoo nutzt deutsche Ticker meist direkt wie ALV.DE, SAP.DE usw.
        ticker = yf.Ticker(yf_symbol)

        fast = ticker.fast_info
        price = fast.get("last_price") if fast else None
        currency = fast.get("currency") if fast else None

        if price:
            return {
                "price": float(price),
                "currency": currency or "EUR",
            }

        hist = ticker.history(period="5d")
        if not hist.empty:
            return {
                "price": float(hist["Close"].dropna().iloc[-1]),
                "currency": currency or "EUR",
            }

    except Exception as e:
        print(f"yfinance price failed for {symbol}: {e}")

    return None
    
def get_yfinance_history(symbol: str, range: str = "6m") -> list[dict]:
    period_map = {
        "6m": "6mo",
        "1y": "1y",
        "5y": "5y",
    }

    period = period_map.get(range, "6mo")

    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, interval="1d")

        if hist.empty:
            return []

        rows = []
        for date, row in hist.iterrows():
            rows.append({
                "date": date.strftime("%Y-%m-%d"),
                "close": float(row["Close"]),
            })

        return rows

    except Exception as e:
        print(f"yfinance history failed for {symbol}: {e}")
        return []
        
def get_stock_news(ticker: str, name: str | None = None) -> list[dict]:
    symbol = normalize_ticker(ticker)
    now = time()

    cached = _NEWS_CACHE.get(symbol)
    if cached and now - cached["ts"] < NEWS_TTL_SECONDS:
        return cached["data"]

    news = get_yfinance_news(symbol)

    if not news:
        news = get_finnhub_news(symbol)

    if not news:
        news = get_news(symbol)

    if (not news or len(news) < 2) and name:
        news = get_news(name)  # 👉 Fallback auf Firmenname

    _NEWS_CACHE[symbol] = {"data": news, "ts": now}
    print("NEWS QUERY:", symbol, name)
    return news

def clean_news_items(news: list[dict], limit: int = 10) -> list[dict]:
    cleaned = []

    for item in news:
        title = item.get("title") or item.get("headline")
        if not title:
            continue

        cleaned.append({
            "title": title,
            "publisher": item.get("publisher") or item.get("source") or "Unbekannte Quelle",
            "link": item.get("link") or item.get("url"),
            "summary": item.get("summary") or item.get("description") or "",
            "date": item.get("providerPublishTime") or item.get("datetime"),
        })

        if len(cleaned) >= limit:
            break

    return cleaned


def get_yfinance_news(symbol: str) -> list[dict]:
    try:
        t = yf.Ticker(symbol)
        return clean_news_items(t.news or [])
    except Exception as e:
        print(f"yfinance news failed for {symbol}: {e}")
        return []


def get_finnhub_news(symbol: str) -> list[dict]:
    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        return []

    # Finnhub company-news ist für US-Symbole am zuverlässigsten.
    # Für .DE, .OL usw. oft leer oder nicht verfügbar.
    if "." in symbol:
        return []

    today = date.today()
    start = today - timedelta(days=21)

    try:
        response = requests.get(
            "https://finnhub.io/api/v1/company-news",
            params={
                "symbol": symbol,
                "from": start.isoformat(),
                "to": today.isoformat(),
                "token": api_key,
            },
            timeout=10,
        )

        data = response.json()

        if isinstance(data, dict) and data.get("error"):
            print(f"Finnhub news error for {symbol}: {data}")
            return []

        if not isinstance(data, list):
            print(f"Finnhub news unexpected response for {symbol}: {data}")
            return []

        return clean_news_items(data)

    except Exception as e:
        print(f"Finnhub news failed for {symbol}: {e}")
        return []

NEWS_API_KEY = os.getenv("NEWS_API_KEY")

def get_news(query):
    url = "https://newsapi.org/v2/everything"

    params = {
        "q": query,
        "sortBy": "publishedAt",
        "pageSize": 5,
        "apiKey": NEWS_API_KEY,
    }

    try:
        res = requests.get(url, params=params)
        data = res.json()

        articles = data.get("articles", [])

        return [
            {
                "title": a["title"],
                "publisher": a["source"]["name"],
                "link": a["url"],
                "summary": a.get("description") or "",
                "date": a["publishedAt"],
            }
            for a in articles
        ]

    except Exception as e:
        print("News API error:", e)
        return []