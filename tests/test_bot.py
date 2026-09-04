from unittest.mock import patch, MagicMock
from bot import process_update, is_small_talk, get_main_keyboard, WELCOME_MESSAGE


def test_get_main_keyboard():
    keyboard = get_main_keyboard()
    assert "inline_keyboard" in keyboard
    rows = keyboard["inline_keyboard"]
    assert len(rows) == 3
    assert rows[0][0]["text"] == "🥇 Gold Price"
    assert rows[0][0]["callback_data"] == "cmd_gold_price"
    assert rows[0][1]["text"] == "💵 Toman Rate"
    assert rows[0][1]["callback_data"] == "cmd_toman_rate"
    assert rows[1][0]["text"] == "🪙 Crypto Analysis"
    assert rows[1][1]["text"] == "📊 Analyze a Chart"
    assert rows[2][0]["text"] == "❓ Ask a Question"


def test_is_small_talk():
    assert is_small_talk("سلام") is True
    assert is_small_talk("hi") is True
    assert is_small_talk("hello") is True
    assert is_small_talk("خداحافظ") is True
    assert is_small_talk("ممنون") is True
    assert is_small_talk("/start") is False
    assert is_small_talk("طلا الان گرونه یا ارزون؟") is False
    assert is_small_talk("قیمت دلار چنده؟") is False


@patch("bot.send_message")
def test_process_update_start_command(mock_send_message):
    update = {
        "message": {
            "chat": {"id": 12345},
            "text": "/start"
        }
    }
    process_update(update)
    mock_send_message.assert_called_once_with(12345, WELCOME_MESSAGE, reply_markup=get_main_keyboard())


@patch("bot.send_message")
@patch("agent.run_agent")
def test_process_update_small_talk_short_circuits(mock_run_agent, mock_send_message):
    update = {
        "message": {
            "chat": {"id": 12345},
            "text": "سلام"
        }
    }
    process_update(update)

    mock_run_agent.assert_not_called()
    mock_send_message.assert_called_once_with(12345, "سلام! میتونی درباره قیمت طلا یا تتر ازم بپرسی.", reply_markup=get_main_keyboard())


@patch("bot.send_message")
@patch("agent.run_agent")
def test_process_update_financial_query_calls_agent(mock_run_agent, mock_send_message):
    mock_run_agent.return_value = "قیمت طلا ۲۷۰۰ دلار است."
    update = {
        "message": {
            "chat": {"id": 12345},
            "text": "قیمت طلا امروز چنده؟"
        }
    }
    process_update(update)

    mock_run_agent.assert_called_once_with("قیمت طلا امروز چنده؟")


@patch("bot.answer_callback_query")
@patch("bot.send_message")
@patch("agent.run_agent")
def test_process_update_callback_query_gold_price(mock_run_agent, mock_send_message, mock_answer_callback):
    mock_run_agent.return_value = "قیمت طلا هر اونس ۲۷۳۵ دلار است."
    update = {
        "callback_query": {
            "id": "cb_123",
            "data": "cmd_gold_price",
            "message": {
                "chat": {"id": 12345}
            }
        }
    }
    process_update(update)

    mock_answer_callback.assert_called_once_with("cb_123")
    mock_run_agent.assert_called_once_with("قیمت طلا امروز گرمی و اونسی چنده؟")


@patch("bot.answer_callback_query")
@patch("bot.send_message")
@patch("agent.run_agent")
def test_process_update_callback_query_analyze_chart(mock_run_agent, mock_send_message, mock_answer_callback):
    update = {
        "callback_query": {
            "id": "cb_456",
            "data": "cmd_analyze_chart",
            "message": {
                "chat": {"id": 12345}
            }
        }
    }
    process_update(update)

    mock_answer_callback.assert_called_once_with("cb_456")
    mock_run_agent.assert_not_called()
    mock_send_message.assert_called_once()
    assert "لطفاً تصویر نمودار" in mock_send_message.call_args[0][1]
@patch("bot.send_message")
@patch("agent.run_agent")
def test_process_update_english_small_talk(mock_run_agent, mock_send_message):
    update = {
        "message": {
            "chat": {"id": 12345},
            "text": "hello"
        }
    }
    process_update(update)

    mock_run_agent.assert_not_called()
    mock_send_message.assert_called_once_with(12345, "Hello! You can ask me about gold prices or USDT/Toman rates.", reply_markup=get_main_keyboard())


@patch("bot.send_message")
@patch("agent.run_agent")
def test_process_update_english_financial_query(mock_run_agent, mock_send_message):
    mock_run_agent.return_value = "The gold price is $2735 per ounce."
    update = {
        "message": {
            "chat": {"id": 12345},
            "text": "What is the current gold price?"
        }
    }
    process_update(update)

    mock_run_agent.assert_called_once_with("What is the current gold price?")
    calls = mock_send_message.call_args_list
    assert len(calls) == 2
    assert "Fetching live market data" in calls[0][0][1]
    assert calls[1][0][1] == "The gold price is $2735 per ounce."
