import json
from unittest.mock import patch, MagicMock
from agent import build_synthesize_prompt, clean_json_text, plan_step, act_step, detect_language, analyze_chart_image


def test_detect_language():
    assert detect_language("قیمت طلا امروز چنده؟") == "fa"
    assert detect_language("سلام، چطوری؟") == "fa"
    assert detect_language("What is the current gold price?") == "en"
    assert detect_language("Hello, how are you?") == "en"
    assert detect_language("100 USD to Toman") == "en"


def test_build_synthesize_prompt_bilingual():
    tool_results = {"status": "success"}

    sys_fa, _ = build_synthesize_prompt("قیمت طلا؟", tool_results, language="fa")
    assert "Respond in Persian" in sys_fa

    sys_en, _ = build_synthesize_prompt("Gold price?", tool_results, language="en")
    assert "Respond in English" in sys_en


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



@patch("tools.get_crypto_price")
def test_act_step_get_crypto_price(mock_crypto):
    mock_crypto.return_value = {
        "status": "success",
        "symbol": "btc",
        "coin_id": "bitcoin",
        "price_usd": 68500.0,
        "change_24h_percent": 2.5
    }

    plan = {"tools": [{"name": "get_crypto_price", "params": {"symbol": "btc"}}]}
    results = act_step(plan)

    mock_crypto.assert_called_once_with(symbol="btc")
    assert "get_crypto_price" in results
    assert results["get_crypto_price"]["price_usd"] == 68500.0


@patch("agent.GEMINI_API_KEY", "mock_key")
@patch("agent.requests.post")
def test_analyze_chart_image_success(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "Bullish trend observed with key resistance at $2750."}]
                }
            }
        ]
    }
    mock_post.return_value = mock_resp

    fake_bytes = b"fake_jpeg_bytes"
    res_en = analyze_chart_image(fake_bytes, caption="Analyze this chart", language="en")
    assert "Bullish trend observed" in res_en

    called_args, called_kwargs = mock_post.call_args
    payload = called_kwargs.get("json", {})
    assert "inline_data" in payload["contents"][0]["parts"][0]
    assert payload["contents"][0]["parts"][0]["inline_data"]["mime_type"] == "image/jpeg"
    assert "Analyze this chart" in payload["contents"][0]["parts"][1]["text"]


@patch("agent.GEMINI_API_KEY", "mock_key")
@patch("agent.requests.post")
def test_analyze_chart_image_failure(mock_post):
    mock_post.side_effect = Exception("API rate limit reached")

    fake_bytes = b"fake_jpeg_bytes"
    res_fa = analyze_chart_image(fake_bytes, caption="تحلیل نمودار", language="fa")
    assert "خطایی رخ داد" in res_fa

    res_en = analyze_chart_image(fake_bytes, caption="Analyze chart", language="en")
    assert "error occurred" in res_en.lower()
