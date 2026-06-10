CURRENCY_RATES = {
    "₹": 83.50,
    "د.إ": 3.67,
    "S$": 1.35,
    "฿": 35.50,
    "$": 1.00,
    "£": 0.79,
    "¥": 149.50,
    "A$": 1.53,
    "C$": 1.36,
    "RM": 4.72,
    "€": 0.92,
    "Fr": 0.90,
    "R$": 4.97,
    "R": 18.63,
    "﷼": 3.75,
    "₺": 32.00,
    "NZ$": 1.63,
    "HK$": 7.82,
    "₫": 24500.00,
    "KD": 0.31,
    "Rs": 83.50
}

def local_to_usd(local_amount: float, currency_symbol: str) -> float:
    rate = CURRENCY_RATES.get(currency_symbol, 83.50)
    return round(local_amount / rate, 2)

def usd_to_local(usd_amount: float, currency_symbol: str) -> float:
    rate = CURRENCY_RATES.get(currency_symbol, 83.50)
    return round(usd_amount * rate, 2)