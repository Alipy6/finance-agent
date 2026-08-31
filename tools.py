import json
import os
import re
from datetime import datetime, timezone, timedelta
import requests
from config import BRSAPI_KEY, HISTORY_FILE_PATH

GRAMS_PER_TROY_OUNCE = 31.1034768

def log_price(price_usd: float, file_path: str = None) -> None:
    """Log gold spot price with timestamp to local JSON file."""
    path = file_path or HISTORY_FILE_PATH
    history = []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                history = json.load(f)
                if not isinstance(history, list):
                    history = []
        except Exception:
            history = []

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "price_per_oz_usd": float(price_usd)
    }
    history.append(record)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def get_gold_price(file_path: str = None) -> dict:
    """
    Fetch current XAU/USD spot price and 24k gram price from gold-api.com.
    Automatically logs the price to local history file.
    """
    url = "https://api.gold-api.com/price/XAU"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        price_oz = float(data.get("price", 0))
        if price_oz <= 0:
            return {"status": "error", "message": "Invalid gold price returned from API"}

        price_gram_24k = round(price_oz / GRAMS_PER_TROY_OUNCE, 2)
        
        # Log fetched price to history file
        try:
            log_price(price_oz, file_path=file_path)
        except Exception:
            pass

        return {
            "status": "success",
            "symbol": "XAU",
            "price_per_oz_usd": price_oz,
            "price_per_gram_24k_usd": price_gram_24k,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to fetch gold price: {str(e)}"}


def get_toman_rate(api_key: str = None) -> dict:
    """
    Fetch current USDT/Toman rate from brsapi.ir.
    Reads key from environment or parameter.
    """
    key = api_key if api_key is not None else BRSAPI_KEY
    if not key:
        return {
            "status": "unavailable",
            "message": "Toman conversion rate is not available because BRSAPI_KEY environment variable is not configured."
        }

    url = f"https://Api.BrsApi.ir/Market/Gold_Currency.php?key={key}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        currency_list = data.get("currency", [])
        if isinstance(currency_list, list):
            for item in currency_list:
                symbol = item.get("symbol", "").upper()
                name = item.get("name", "")
                if symbol == "USDT_IRT" or symbol == "USDT" or "تتر" in name or "USDT" in name:
                    raw_price = item.get("price")
                    if raw_price is not None:
                        rate = float(raw_price)
                        return {
                            "status": "success",
                            "symbol": "USDT_IRT",
                            "rate_toman": rate,
                            "name": name or "USDT/Toman"
                        }
        
        return {
            "status": "unavailable",
            "message": "USDT_IRT rate symbol not found in BRSAPI response."
        }
    except Exception as e:
        return {
            "status": "unavailable",
            "message": f"Toman conversion isn't available due to BRSAPI fetch error: {str(e)}"
        }


def get_historical_comparison(days_ago: int = 7, file_path: str = None) -> dict:
    """
    Compare current or requested time price with logged historical price in price_history.json.
    """
    path = file_path or HISTORY_FILE_PATH
    if not os.path.exists(path):
        return {
            "status": "no_data",
            "message": "No historical data logged yet in history file."
        }

    try:
        with open(path, "r", encoding="utf-8") as f:
            history = json.load(f)
    except Exception as e:
        return {"status": "error", "message": f"Could not read history file: {str(e)}"}

    if not history or not isinstance(history, list):
        return {
            "status": "no_data",
            "message": "No historical records found in local log file."
        }

    now = datetime.now(timezone.utc)
    target_time = now - timedelta(days=days_ago)

    valid_records = []
    for rec in history:
        ts_str = rec.get("timestamp")
        price = rec.get("price_per_oz_usd")
        if ts_str and price is not None:
            try:
                rec_dt = datetime.fromisoformat(ts_str)
                if rec_dt.tzinfo is None:
                    rec_dt = rec_dt.replace(tzinfo=timezone.utc)
                valid_records.append((rec_dt, price))
            except ValueError:
                continue

    if not valid_records:
        return {"status": "no_data", "message": "No valid historical records parsed."}

    valid_records.sort(key=lambda x: x[0])
    oldest_dt, oldest_price = valid_records[0]

    max_allowed_diff_seconds = (days_ago * 86400) * 0.2
    actual_diff_seconds = (now - oldest_dt).total_seconds()

    # If the oldest logged record is significantly newer than the requested target time
    if (oldest_dt - target_time).total_seconds() > 43200:
        return {
            "status": "insufficient_data",
            "message": f"No historical data available for {days_ago} days ago yet. Oldest record is from {oldest_dt.strftime('%Y-%m-%d %H:%M UTC')}."
        }

    closest_dt, closest_price = min(valid_records, key=lambda x: abs((x[0] - target_time).total_seconds()))

    return {
        "status": "success",
        "days_ago": days_ago,
        "historical_price_oz_usd": closest_price,
        "historical_date": closest_dt.isoformat()
    }


def calculator(usd_amount: float = None, toman_amount: float = None, gold_price_oz_usd: float = None, toman_rate: float = None, expression: str = None) -> dict:
    """
    Perform financial calculation (how much gold can be bought with USD or Toman, or math expression).
    """
    results = {}

    if expression:
        safe_expr = re.sub(r'[^0-9\+\-\*\/\(\)\. ]', '', str(expression))
        try:
            val = eval(safe_expr, {"__builtins__": None}, {})
            results["expression_result"] = round(float(val), 4)
        except Exception as e:
            results["expression_error"] = f"Invalid calculation: {str(e)}"

    if usd_amount is not None and gold_price_oz_usd and gold_price_oz_usd > 0:
        usd = float(usd_amount)
        oz = usd / gold_price_oz_usd
        grams = oz * GRAMS_PER_TROY_OUNCE
        results["usd_purchase"] = {
            "usd_amount": usd,
            "gold_price_oz_usd": gold_price_oz_usd,
            "ounces_purchasable": round(oz, 4),
            "grams_24k_purchasable": round(grams, 3)
        }

    if toman_amount is not None and toman_rate and toman_rate > 0 and gold_price_oz_usd and gold_price_oz_usd > 0:
        toman = float(toman_amount)
        equivalent_usd = toman / toman_rate
        oz = equivalent_usd / gold_price_oz_usd
        grams = oz * GRAMS_PER_TROY_OUNCE
        results["toman_purchase"] = {
            "toman_amount": toman,
            "toman_rate": toman_rate,
            "equivalent_usd": round(equivalent_usd, 2),
            "gold_price_oz_usd": gold_price_oz_usd,
            "ounces_purchasable": round(oz, 4),
            "grams_24k_purchasable": round(grams, 3)
        }

    if not results:
        return {"status": "error", "message": "No valid calculation parameters or inputs provided."}

    return {"status": "success", "results": results}
