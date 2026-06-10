from backend.database import SessionLocal
from sqlalchemy import text

def get_currency_for_country(country: str):
    db = SessionLocal()
    try:
        result = db.execute(
            text("SELECT currency_code, currency_symbol, usd_rate FROM currencies WHERE LOWER(country) = LOWER(:c)"),
            {"c": country}
        ).fetchone()
        if result:
            return {
                "currency_code": result.currency_code,
                "currency_symbol": result.currency_symbol,
                "usd_rate": float(result.usd_rate)
            }
        return {"currency_code": "USD", "currency_symbol": "$", "usd_rate": 1.0}
    finally:
        db.close()

def convert_to_local(usd_amount: float, usd_rate: float) -> float:
    return round(usd_amount * usd_rate, 2)

def convert_to_usd(local_amount: float, usd_rate: float) -> float:
    return round(local_amount / usd_rate, 2)

def get_all_countries():
    db = SessionLocal()
    try:
        result = db.execute(
            text("SELECT country, currency_code, currency_symbol FROM currencies ORDER BY country")
        ).fetchall()
        return [{"country": r.country, "currency_code": r.currency_code, "currency_symbol": r.currency_symbol} for r in result]
    finally:
        db.close()