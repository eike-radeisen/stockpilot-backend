from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import WatchlistItem, DEMO_USER_ID
from schemas import WatchlistCreate, WatchlistOut
from services.price_service import get_price, get_stock_performance

router = APIRouter(prefix="/watchlist", tags=["watchlist"])

from services.price_service import get_price, get_fx_rate

def enrich(item: WatchlistItem) -> WatchlistOut:
    price_data = get_price(item.ticker)

    current_price = None
    current_price_eur = None
    current_currency = None


    if price_data:
        current_price = price_data.get("price")
        current_currency = price_data.get("currency", "EUR")

        fx = get_fx_rate(current_currency, "EUR") or 1.0
        current_price_eur = current_price * fx if current_price is not None else None
        
    performance = get_stock_performance(item.ticker)
    daily_change_pct = performance.get("daily")

    return WatchlistOut(
        id=item.id,
        ticker=item.ticker,
        name=item.name,
        note=item.note,
        current_price=current_price,
        current_price_eur=current_price_eur,
        current_currency=current_currency,
        daily_change_pct=daily_change_pct,
    )
@router.get("", response_model=list[WatchlistOut])
def list_watchlist(db: Session = Depends(get_db)):
    return [enrich(i) for i in db.query(WatchlistItem).filter(WatchlistItem.user_id == DEMO_USER_ID).all()]

@router.post("", response_model=WatchlistOut)
def create_watchlist_item(payload: WatchlistCreate, db: Session = Depends(get_db)):
    data = payload.model_dump()
    data["ticker"] = payload.ticker.upper()

    item = WatchlistItem(**data, user_id=DEMO_USER_ID)

    db.add(item)
    db.commit()
    db.refresh(item)
    return enrich(item)

@router.delete("/{item_id}")
def delete_watchlist_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(WatchlistItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Watchlist item not found")
    db.delete(item)
    db.commit()
    return {"ok": True}
