from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import Base, engine
from routers import portfolio, watchlist, stocks, ai
from dotenv import load_dotenv
load_dotenv()

Base.metadata.create_all(bind=engine)

app = FastAPI(title="StockPilot MVP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # für Entwicklung ok
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(portfolio.router)
app.include_router(watchlist.router)
app.include_router(stocks.router)
app.include_router(ai.router)

@app.get("/")
def root():
    return {"status": "ok", "app": "StockPilot MVP"}