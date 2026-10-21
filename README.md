# 🤖📈 Finance Agent — Grounded Plan → Act → Synthesize Financial AI

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Architecture](https://img.shields.io/badge/Agent_Pattern-Plan_%E2%86%92_Act_%E2%86%92_Synthesize-10b981)
![Gemini](https://img.shields.io/badge/LLM_%26_Vision-Google_Gemini_API-8E75B2?logo=googlegemini&logoColor=white)
![Telegram](https://img.shields.io/badge/Interface-Telegram_Bot_API-26A5E4?logo=telegram&logoColor=white)
![Pytest](https://img.shields.io/badge/Tests-Pytest_Verified-6366f1?logo=pytest&logoColor=white)

A multi-modal Telegram AI Agent engineered around a deterministic **Plan → Act → Synthesize** execution pipeline. Unlike single-shot chatbots that hallucinate market rates from outdated parametric memory, **Finance Agent** dynamically plans tool calls, queries live spot gold, cryptocurrency, and domestic currency APIs, performs exact arithmetic, and synthesizes bilingual (**Persian & English**) responses strictly grounded in fetched data.

---

## 🏛️ Architectural Design: Why Plan → Act → Synthesize?

```text
User Query (Text / Chart Photo)
       │
       ├──► [Photo Detected] ──► Gemini Multimodal Vision API ──► Observational Chart Analysis
       │
       └──► [Text Query]
                 │
                 ▼
         ┌───────────────┐
         │  1. PLAN STEP │  LLM analyzes intent & outputs a strict JSON tool execution plan
         └───────┬───────┘
                 │  {"tools": [{"name": "get_gold_price"}, {"name": "get_toman_rate"}, ...]}
                 ▼
         ┌───────────────┐
         │  2. ACT STEP  │  Python executes deterministic tools & financial calculations
         └───────┬───────┘
                 │  Live XAU/USD, 24K/18K Toman Gold, USDT/IRT, CoinGecko Crypto, History Delta
                 ▼
         ┌───────────────┐
         │ 3. SYNTHESIZE │  LLM generates a grounded answer strictly from tool_results JSON
         └───────────────┘
Integrated Agent Tools (tools.py)
get_gold_price(): Fetches real-time international spot gold (XAU/USD) and 24K gram prices from api.gold-api.com, automatically logging records to price_history.json.

get_toman_rate(): Queries live USDT/IRT Toman exchange rates via BrsApi.ir with multi-source public exchange fallbacks (TetherLand, Wallex, Nobitex) and automatically computes 24K & 18K Gram Gold in Tomans plus Intrinsic Emami Coin Valuation.

get_crypto_price(symbol): Fetches live USD spot prices and 24-hour percentage changes for major cryptocurrencies (BTC, ETH, SOL, TON, BNB, XRP, DOGE, etc.) via CoinGecko.

get_historical_comparison(days_ago): Compares current gold prices against timestamped local historical logs without guessing when history is insufficient.

calculator(...): Safe arithmetic evaluator and purchasing-power converter (calculates exact ounces and 24K/18K grams purchasable with any USD or Toman budget).

analyze_chart_image(...): Multimodal technical chart analyzer powered by Google Gemini Vision—identifies trend structure, support/resistance zones, and visible indicators from user-uploaded chart screenshots.

🚀 Quick Start
1. Clone & Install Dependencies
Bash
git clone https://github.com/Alipy6/finance-agent.git
cd finance-agent
pip install -r requirements.txt
2. Configure Environment Variables
Copy .env.example to local.env (or .env) and provide your keys:

Bash
cp .env.example local.env
Code snippet
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
BRSAPI_KEY=your_brsapi_key_here
GEMINI_API_KEY=your_gemini_api_key_here
HISTORY_FILE_PATH=price_history.json
3. Run the Automated Test Suite
Bash
pytest -v
4. Launch the Agent Bot
Bash
python bot.py
📁 Repository Structure
Plaintext
finance-agent/
├── agent.py                     # Plan → Act → Synthesize LLM pipeline & Gemini Vision analyzer
├── tools.py                     # Market data tools (Gold, USDT/Toman, Crypto, History, Calculator)
├── bot.py                       # Telegram Bot long-polling loop, inline keyboards & photo handler
├── config.py                    # Environment configuration & path resolver
├── tests/                       # Comprehensive unit tests for tools, planner, and synthesizer
├── .github/workflows/ci.yml     # Automated GitHub Actions Pytest workflow
├── .env.example                 # Environment variable template
└── requirements.txt             # Dependencies (requests, python-dotenv, pytest)
