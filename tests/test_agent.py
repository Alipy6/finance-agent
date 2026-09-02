import json
from unittest.mock import patch
from agent import build_synthesize_prompt, clean_json_text, plan_step, act_step


def test_build_synthesize_prompt():
    user_question = "طلا الان گرونه یا ارزون نسبت به هفته پیش؟"
    tool_results = {
        "get_gold_price": {
            "status": "success",
            "price_per_oz_usd": 2735.5,
            "price_per_gram_24k_usd": 87.95
        },
        "get_historical_comparison": {
            "status": "success",
            "days_ago": 7,
            "historical_price_oz_usd": 2680.0
        }
    }

    sys_prompt, user_msg = build_synthesize_prompt(user_question, tool_results)

    # Check system prompt safety rules
    assert "STRICT REQUIREMENTS" in sys_prompt
    assert "Do NOT invent, assume, or guess" in sys_prompt

    # Check user message contents
    assert user_question in user_msg
    assert "2735.5" in user_msg
    assert "2680.0" in user_msg


def test_clean_json_text():
    raw_markdown = "```json\n{\"tools\": [{\"name\": \"get_gold_price\"}]}\n```"
    cleaned = clean_json_text(raw_markdown)
    assert cleaned == "{\"tools\": [{\"name\": \"get_gold_price\"}]}"


@patch("agent.call_omniroute_llm")
def test_plan_step(mock_llm):
    mock_llm.return_value = '{"tools": [{"name": "get_gold_price"}, {"name": "get_toman_rate"}]}'
    
    plan = plan_step("قیمت طلا چنده؟")
    assert "tools" in plan
    assert len(plan["tools"]) == 2
    assert plan["tools"][0]["name"] == "get_gold_price"


@patch("tools.get_gold_price")
@patch("tools.get_toman_rate")
def test_act_step(mock_toman, mock_gold):
    mock_gold.return_value = {
        "status": "success",
        "price_per_oz_usd": 2700.0,
        "price_per_gram_24k_usd": 86.8
    }
    mock_toman.return_value = {
        "status": "success",
        "symbol": "USDT_IRT",
        "rate_toman": 60000.0
    }

    plan = {"tools": [{"name": "get_gold_price"}, {"name": "get_toman_rate"}]}
    results = act_step(plan)

    assert "get_gold_price" in results
    assert "get_toman_rate" in results
    assert results["get_gold_price"]["price_per_oz_usd"] == 2700.0
    assert results["get_toman_rate"]["rate_toman"] == 60000.0
    assert "computed_toman_prices" in results
    assert results["computed_toman_prices"]["gram_24k_toman"] == 5208000.0
    assert results["computed_toman_prices"]["gram_18k_toman"] == 3906000.0


@patch("tools.get_gold_price")
@patch("tools.get_toman_rate")
def test_act_step_auto_fetch_toman_and_gold(mock_toman, mock_gold):
    mock_gold.return_value = {
        "status": "success",
        "price_per_oz_usd": 2500.0,
        "price_per_gram_24k_usd": 80.38
    }
    mock_toman.return_value = {
        "status": "success",
        "symbol": "USDT_IRT",
        "rate_toman": 60000.0
    }

    # Plan only specifies calculator with toman_amount, neither gold nor toman planned
    plan = {
        "tools": [
            {
                "name": "calculator",
                "params": {"toman_amount": 60000000.0}
            }
        ]
    }
    results = act_step(plan)

    # Should auto-fetch both get_gold_price and get_toman_rate
    mock_gold.assert_called_once()
    mock_toman.assert_called_once()
    assert "get_gold_price" in results
    assert "get_toman_rate" in results
    assert "calculator" in results
    assert results["calculator"]["status"] == "success"
