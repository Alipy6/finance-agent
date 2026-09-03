import time
import logging
import requests
from config import TELEGRAM_BOT_TOKEN
import agent
import string

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


SMALL_TALK_WORDS = {
    "سلام", "درود", "hi", "hello", "hey", "خداحافظ", "خدافظ", "بای", "bye",
    "چطوری", "چطورید", "ممنون", "مرسی", "thanks", "thank you", "صبح بخیر", "عصر بخیر", "شب بخیر"
}

FINANCIAL_KEYWORDS = {"طلا", "ارز", "دلار", "تتر", "تومان", "نرخ", "قیمت", "چنده", "چقدر", "سکه", "انس", "گرم", "خرید", "فروش"}


def is_small_talk(text: str) -> bool:
    """Return True if message is casual small talk rather than a financial query."""
    cleaned = text.strip().lower().strip(string.punctuation + "؟!،")

    if cleaned.startswith("/"):
        return False

    if any(keyword in cleaned for keyword in FINANCIAL_KEYWORDS):
        return False

    if cleaned in SMALL_TALK_WORDS:
        return True

    words = cleaned.split()
    if len(words) <= 2 and any(w in SMALL_TALK_WORDS for w in words):
        return True

    return False


WELCOME_MESSAGE = (
    "Welcome to <b>Finance Agent AI</b>! 🤖📈\n\n"
    "I am an intelligent financial agent powered by real-time market data and LLM reasoning.\n\n"
    "Here is what I can do for you:\n"
    "• 🥇 <b>Gold Price</b>: Real-time XAU/USD spot & 24k/18k gram prices.\n"
    "• 💵 <b>Toman Rate</b>: Live USDT/Toman conversion rates.\n"
    "• 🪙 <b>Crypto Analysis</b>: Grounded market insights.\n"
    "• 📊 <b>Analyze a Chart</b>: Technical chart guidance.\n"
    "• ❓ <b>Ask Anything</b>: Type any question in Persian or English!\n\n"
    "Select an option below or type your question directly:"
)


def get_main_keyboard() -> dict:
    """Return Telegram inline keyboard reply_markup dict with main action buttons."""
    return {
        "inline_keyboard": [
            [
                {"text": "🥇 Gold Price", "callback_data": "cmd_gold_price"},
                {"text": "💵 Toman Rate", "callback_data": "cmd_toman_rate"}
            ],
            [
                {"text": "🪙 Crypto Analysis", "callback_data": "cmd_crypto_analysis"},
                {"text": "📊 Analyze a Chart", "callback_data": "cmd_analyze_chart"}
            ],
            [
                {"text": "❓ Ask a Question", "callback_data": "cmd_ask_question"}
            ]
        ]
    }


def send_message(chat_id: int, text: str, reply_markup: dict = None) -> None:
    """Send text message to Telegram chat via API."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is missing. Cannot send message.")
        return
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        resp = requests.post(url, json=payload, timeout=15)
        # Fallback to plain text if HTML parsing fails
        if resp.status_code == 400 and "parse" in resp.text.lower():
            payload.pop("parse_mode", None)
            requests.post(url, json=payload, timeout=15)
    except Exception as e:
        logger.error(f"Error sending message to Telegram: {e}")


def answer_callback_query(callback_query_id: str, text: str = None) -> None:
    """Acknowledge Telegram callback query button tap."""
    if not TELEGRAM_BOT_TOKEN or not callback_query_id:
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
    payload = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text

    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"Error answering callback query: {e}")


def process_update(update: dict) -> None:
    """Process a single Telegram update dict (message or callback_query)."""
    # 1. Handle callback_query updates (button taps)
    if "callback_query" in update:
        cb = update["callback_query"]
        cb_id = cb.get("id")
        cb_data = cb.get("data", "")
        message = cb.get("message", {})
        chat_id = message.get("chat", {}).get("id")

        if cb_id:
            answer_callback_query(cb_id)

        if not chat_id:
            return

        logger.info(f"Received callback query '{cb_data}' from chat {chat_id}")

        if cb_data == "cmd_gold_price":
            query_text = "قیمت طلا امروز گرمی و اونسی چنده؟"
        elif cb_data == "cmd_toman_rate":
            query_text = "نرخ تتر و دلار به تومان چنده؟"
        elif cb_data == "cmd_crypto_analysis":
            query_text = "وضعیت کل بازار کریپتو و تتر چطوریه؟"
        elif cb_data == "cmd_analyze_chart":
            send_message(
                chat_id,
                "📊 برای تحلیل نمودار، لطفاً تصویر نمودار یا نام جفتارز مورد نظرتان را به همراه سؤال خود ارسال کنید."
            )
            return
        elif cb_data == "cmd_ask_question":
            send_message(
                chat_id,
                "❓ لطفاً سؤال مالی خود را درباره طلا، تتر یا ارزها بنویسید تا بهصورت دقیق پاسخ دهم."
            )
            return
        else:
            query_text = cb_data

        send_message(chat_id, "⏳ در حال دریافت قیمتهای زنده و تحلیل پاسخ...")
        try:
            answer = agent.run_agent(query_text)
            send_message(chat_id, answer)
        except Exception as e:
            logger.error(f"Unhandled error processing callback query: {e}", exc_info=True)
            send_message(chat_id, "متأسفانه در پاسخگویی خطایی رخ داد. لطفاً دوباره تلاش کنید.")
        return

    # 2. Handle standard message updates
    message = update.get("message")
    if not message:
        return

    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "").strip()

    if not chat_id or not text:
        return

    logger.info(f"Received question from chat {chat_id}: '{text}'")

    if text.startswith("/start"):
        send_message(chat_id, WELCOME_MESSAGE, reply_markup=get_main_keyboard())
        return

    if is_small_talk(text):
        send_message(chat_id, "سلام! میتونی درباره قیمت طلا یا تتر ازم بپرسی.", reply_markup=get_main_keyboard())
        return

    # Notify user that agent is processing
    send_message(chat_id, "⏳ در حال دریافت قیمتهای زنده و تحلیل پاسخ...")

    try:
        # Run Plan -> Act -> Synthesize agent pipeline
        answer = agent.run_agent(text)
        send_message(chat_id, answer)
    except Exception as e:
        logger.error(f"Unhandled error processing query: {e}", exc_info=True)
        send_message(chat_id, "متأسفانه در پاسخگویی خطایی رخ داد. لطفاً دوباره تلاش کنید.")


def start_polling():
    """Main Telegram long-polling loop."""
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN environment variable is not set in local.env or .env!")
        logger.warning("Bot is starting, but cannot fetch updates without a valid token.")

    logger.info("Starting Telegram Finance Agent long-polling loop...")
    offset = 0
    
    while True:
        try:
            if not TELEGRAM_BOT_TOKEN:
                time.sleep(5)
                continue

            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
            params = {
                "offset": offset,
                "timeout": 20
            }
            
            response = requests.get(url, params=params, timeout=25)
            if response.status_code != 200:
                logger.error(f"Telegram getUpdates returned HTTP {response.status_code}: {response.text}")
                time.sleep(5)
                continue

            data = response.json()
            if not data.get("ok"):
                logger.error(f"Telegram getUpdates error: {data}")
                time.sleep(5)
                continue

            updates = data.get("result", [])
            for update in updates:
                update_id = update.get("update_id")
                offset = max(offset, update_id + 1)
                try:
                    process_update(update)
                except Exception as ex:
                    logger.error(f"Error handling update {update_id}: {ex}", exc_info=True)

        except requests.exceptions.Timeout:
            # Long-polling timeout is normal, loop again
            continue
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error in polling loop: {e}")
            time.sleep(5)
        except Exception as e:
            logger.error(f"Unexpected error in polling loop: {e}", exc_info=True)
            time.sleep(5)


if __name__ == "__main__":
    start_polling()
