import os
import json
import tempfile
from datetime import datetime, timezone, timedelta
import pytest

from tools import calculator, get_historical_comparison, log_price


def test_calculator_usd_purchase():
    result = calculator(usd_amount=100.0, gold_price_oz_usd=2500.0)
    assert result["status"] == "success"
    purchase = result["results"]["usd_purchase"]
    assert purchase["usd_amount"] == 100.0
    assert purchase["ounces_purchasable"] == 0.04
    assert purchase["grams_24k_purchasable"] == round(0.04 * 31.1034768, 3)


def test_calculator_toman_purchase():
    result = calculator(
        toman_amount=60_000_000,
        toman_rate=60_000,
        gold_price_oz_usd=2000.0
    )
    assert result["status"] == "success"
    purchase = result["results"]["toman_purchase"]
    assert purchase["toman_amount"] == 60_000_000
    assert purchase["equivalent_usd"] == 1000.0
    assert purchase["ounces_purchasable"] == 0.5


def test_calculator_expression():
    result = calculator(expression="100 * 2 + 50")
    assert result["status"] == "success"
    assert result["results"]["expression_result"] == 250.0


def test_calculator_invalid():
    result = calculator()
    assert result["status"] == "error"


def test_historical_comparison_without_history():
    with tempfile.TemporaryDirectory() as tmpdir:
        non_existent_file = os.path.join(tmpdir, "no_history.json")
        result = get_historical_comparison(days_ago=7, file_path=non_existent_file)
        assert result["status"] == "no_data"


def test_historical_comparison_with_history():
    with tempfile.TemporaryDirectory() as tmpdir:
        history_file = os.path.join(tmpdir, "price_history.json")
        
        now = datetime.now(timezone.utc)
        seven_days_ago = (now - timedelta(days=7)).isoformat()
        
        history_data = [
            {"timestamp": seven_days_ago, "price_per_oz_usd": 2400.0},
            {"timestamp": now.isoformat(), "price_per_oz_usd": 2500.0}
        ]
        
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history_data, f)
            
        result = get_historical_comparison(days_ago=7, file_path=history_file)
        assert result["status"] == "success"
        assert result["days_ago"] == 7
        assert result["historical_price_oz_usd"] == 2400.0


def test_historical_comparison_insufficient_history():
    with tempfile.TemporaryDirectory() as tmpdir:
        history_file = os.path.join(tmpdir, "price_history.json")
        
        now = datetime.now(timezone.utc)
        one_hour_ago = (now - timedelta(hours=1)).isoformat()
        
        history_data = [
            {"timestamp": one_hour_ago, "price_per_oz_usd": 2500.0}
        ]
        
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history_data, f)
            
        result = get_historical_comparison(days_ago=7, file_path=history_file)
        assert result["status"] == "insufficient_data"
