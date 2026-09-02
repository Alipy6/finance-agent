from unittest.mock import patch, MagicMock
from bot import process_update, is_small_talk


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
@patch("agent.run_agent")
def test_process_update_small_talk_short_circuits(mock_run_agent, mock_send_message):
    update = {
        "message": {
            "chat": {"id": 12345},
            "text": "سلام"
        }
    }
    process_update(update)

    # agent.run_agent should NOT be called for small talk
    mock_run_agent.assert_not_called()
    # A reply should be sent
    mock_send_message.assert_called_once_with(12345, "سلام! میتونی درباره قیمت طلا یا تتر ازم بپرسی.")


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

    # agent.run_agent SHOULD be called for financial questions
    mock_run_agent.assert_called_once_with("قیمت طلا امروز چنده؟")
