from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Position, DEMO_USER_ID
from schemas import PositionCreate, PositionOut
from services.price_service import get_price, get_fx_rate, get_stock_performance



router = APIRouter(prefix="/portfolio", tags=["portfolio"])

def enrich(pos: Position) -> PositionOut:
    price_data = get_price(pos.ticker)

    current_price = None
    current_price_eur = None
    current_currency = None
    current_value = None
    profit_loss = None
    profit_loss_pct = None

    if price_data:
        current_price = price_data["price"]
        current_currency = price_data.get("currency", "EUR")

        fx = get_fx_rate(current_currency, "EUR")

        if fx is not None and current_price is not None:
            current_price_eur = current_price * fx
        else:
            current_price_eur = None

        current_value = current_price_eur * pos.quantity
        invested = pos.buy_price * pos.quantity
        profit_loss = current_value - invested
        profit_loss_pct = (profit_loss / invested) * 100 if invested else None
        
    performance = get_stock_performance(pos.ticker)
    daily_change_pct = performance.get("daily")

    return PositionOut(
        id=pos.id,
        ticker=pos.ticker,
        name=pos.name,
        quantity=pos.quantity,
        buy_price=pos.buy_price,
        buy_date=pos.buy_date,
        currency=pos.currency,
        current_price=current_price,
        current_price_eur=current_price_eur,
        current_currency=current_currency,
        current_value=current_value,
        profit_loss=profit_loss,
        profit_loss_pct=profit_loss_pct,
        daily_change_pct=daily_change_pct,
    )

@router.get("", response_model=list[PositionOut])
def list_positions(db: Session = Depends(get_db)):
    return [enrich(p) for p in db.query(Position).filter(Position.user_id == DEMO_USER_ID).all()]

@router.post("", response_model=PositionOut)
def create_position(payload: PositionCreate, db: Session = Depends(get_db)):
    data = payload.model_dump()
    data["ticker"] = payload.ticker.upper()

    pos = Position(**data, user_id=DEMO_USER_ID)

    db.add(pos)
    db.commit()
    db.refresh(pos)
    return enrich(pos)

@router.delete("/{position_id}")
def delete_position(position_id: int, db: Session = Depends(get_db)):
    pos = db.get(Position, position_id)
    if not pos:
        raise HTTPException(status_code=404, detail="Position not found")
    db.delete(pos)
    db.commit()
    return {"ok": True}
