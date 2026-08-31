# Finance Agent 🤖📈

A Telegram bot that operates as a genuine AI Agent using a **Plan → Act → Synthesize** architecture. Unlike basic chatbots that generate answers directly from parametric memory (which leads to hallucinated numbers or outdated prices), Finance Agent fetches live spot prices and historical logs before synthesizing answers strictly grounded in real data.

---

## 🏛 Architecture & Design Decision

### Why Plan → Act → Synthesize?
Standard chatbots answer questions in a single LLM call. When asked about current or past market rates (e.g. *"Is gold expensive compared to last week?"*), a single-shot LLM will either refuse to answer or fabricate plausible-sounding prices (hallucination).

Finance Agent solves this by decoupling reasoning from data retrieval into three clear steps:

1. **Plan**:
   The incoming question is sent to an LLM via OmniRoute's local endpoint (`http://localhost:20128/v1`, model `auto`). The system prompt instructs the model to return a structured JSON plan specifying **which tools** need to be called (e.g., `get_gold_price`, `get_toman_rate`, `get_historical_comparison`, `calculator`). The LLM does **not** answer the question at this step.

2. **Act**:
   The agent parses the plan JSON and executes the required tool functions:
   - `get_gold_price()`: Fetches live XAU/USD spot price and 24k gram price from `gold-api.com`. Automatically logs price & timestamp to `price_history.json`.
   - `get_toman_rate()`: Fetches USDT/Toman rate from `brsapi.ir` using `BRSAPI_KEY`. If key is missing or call fails, gracefully skips and notes unavailability.
   - `get_historical_comparison(days_ago)`: Reads local `price_history.json` to calculate change compared to past logged runs. If history is insufficient, reports this honestly without guessing.
   - `calculator(...)`: Pure Python arithmetic for math or purchasing power calculations (e.g., *"How much gold can I buy with $100?"*).

3. **Synthesize**:
   A second LLM call receives the user's original question **and** the actual tool execution results as context. A strict system prompt explicitly forbids inventing any statistic or rate not present in the results. The LLM produces a natural, accurate response in Persian.

---

## 🚀 Getting Started

### 1. Prerequisites
- **Python 3.9+**
- **OmniRoute**: Local LLM endpoint must be running at `http://localhost:20128/v1` (with model `auto` available).

### 2. Installation
```bash
git clone <repository_url>
cd finance-agent
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy `.env.example` to `local.env` (or `.env`):
```bash
cp .env.example local.env
```
Edit `local.env`:
```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
BRSAPI_KEY=your_brsapi_key_here
OMNIROUTE_BASE_URL=http://localhost:20128/v1
OMNIROUTE_MODEL=auto
HISTORY_FILE_PATH=price_history.json
```

### 4. Running the Tests
Run pytest to verify tools, historical comparison, and prompt synthesis:
```bash
pytest
```

### 5. Running the Bot
Make sure OmniRoute is running locally on port 20128, then run:
```bash
python bot.py
```

---

## 📁 Project Structure

- `config.py` — Environment configuration loader.
- `tools.py` — Data fetching tools (`gold-api.com`, `brsapi.ir`), historical logger (`price_history.json`), and calculator.
- `agent.py` — Plan → Act → Synthesize pipeline functions using OmniRoute local OpenAI API.
- `bot.py` — Telegram long-polling loop with error resilience.
- `tests/` — Pytest unit tests for tools and agent logic.
- `.env.example` — Environment template.
- `requirements.txt` — Project dependencies (`requests`, `python-dotenv`, `pytest`).
