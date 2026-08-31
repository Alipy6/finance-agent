import time
import logging
import requests
from config import TELEGRAM_BOT_TOKEN
import agent

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def send_message(chat_id: int, text: str) -> None:
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
    try:
        resp = requests.post(url, json=payload, timeout=15)
        # Fallback to plain text if HTML parsing fails
        if resp.status_code == 400 and "parse" in resp.text.lower():
            payload.pop("parse_mode", None)
            requests.post(url, json=payload, timeout=15)
    except Exception as e:
        logger.error(f"Error sending message to Telegram: {e}")


def process_update(update: dict) -> None:
    """Process a single Telegram update dict."""
    message = update.get("message")
    if not message:
        return

    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "").strip()

    if not chat_id or not text:
        return

    logger.info(f"Received question from chat {chat_id}: '{text}'")

    if text.startswith("/start"):
        welcome_msg = (
            "سلام! من ربات ایجنت مالی (Finance Agent) هستم. 🤖\n\n"
            "من از معماری Plan → Act → Synthesize استفاده میکنم و دادههای قیمت طلا و ارز را بهصورت زنده دریافت میکنم.\n\n"
            "میتوانید سؤالات خود را به فارسی یا انگلیسی بپرسید:\n"
            "• مثلاً: «طلا الان گرونه یا ارزون نسبت به هفته پیش؟»\n"
            "• یا: «با ۱۰۰ دلار الان چقدر طلا میتونم بخرم؟»\n"
            "• یا: «قیمت طلا امروز چنده؟»"
        )
        send_message(chat_id, welcome_msg)
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
