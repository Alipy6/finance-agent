import json
import logging
import re
import requests
from config import OMNIROUTE_BASE_URL, OMNIROUTE_MODEL
import tools

logger = logging.getLogger(__name__)

PLANNER_SYSTEM_PROMPT = """You are an expert financial AI planner agent.
Your job is to analyze the user's question and choose which tool calls are required to answer it.

Available tools:
1. "get_gold_price": Fetch current gold spot price per ounce (USD) and 24k gram price. Parameters: none.
2. "get_toman_rate": Fetch current USDT to Toman rate. Parameters: none.
3. "get_historical_comparison": Compare gold price with logged past data. Parameters: {"days_ago": <int, default 7>}.
4. "calculator": Calculate gold amount from USD/Toman or evaluate math expression. Parameters: {"usd_amount": <float>, "toman_amount": <float>, "expression": <string>}.

Instructions:
- Output ONLY a valid JSON object. Do not include markdown code block quotes (like ```json), commentary, or extra text.
- Do NOT attempt to answer the user's question yet.
- Return format must match:
{
  "tools": [
    {"name": "tool_name", "params": {}}
  ]
}
"""


def call_omniroute_llm(system_prompt: str, user_message: str, model: str = None, base_url: str = None) -> str:
    """Call OmniRoute OpenAI-compatible endpoint using requests."""
    url = f"{(base_url or OMNIROUTE_BASE_URL)}/chat/completions"
    payload = {
        "model": model or OMNIROUTE_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.1
    }
    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def clean_json_text(text: str) -> str:
    """Strip markdown codeblock wrappers if present."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def plan_step(user_question: str) -> dict:
    """Step 1: Ask LLM to output JSON execution plan."""
    try:
        raw_output = call_omniroute_llm(PLANNER_SYSTEM_PROMPT, user_question)
        cleaned = clean_json_text(raw_output)
        plan = json.loads(cleaned)
        if isinstance(plan, dict) and "tools" in plan:
            return plan
    except Exception as e:
        logger.warning(f"Plan parsing failed or OmniRoute call failed: {e}. Falling back to default plan.")
    
    return {"tools": [{"name": "get_gold_price"}, {"name": "get_toman_rate"}]}


def act_step(plan: dict) -> dict:
    """Step 2: Execute tool functions according to plan."""
    results = {}
    tool_list = plan.get("tools", [])

    gold_data = None
    toman_data = None

    for item in tool_list:
        name = item.get("name")
        params = item.get("params", {}) or {}

        if name == "get_gold_price":
            gold_data = tools.get_gold_price()
            results["get_gold_price"] = gold_data
        elif name == "get_toman_rate":
            toman_data = tools.get_toman_rate()
            results["get_toman_rate"] = toman_data
        elif name == "get_historical_comparison":
            days_ago = int(params.get("days_ago", 7))
            results["get_historical_comparison"] = tools.get_historical_comparison(days_ago=days_ago)

    has_calc = any(item.get("name") == "calculator" for item in tool_list)
    if has_calc and not gold_data:
        gold_data = tools.get_gold_price()
        results["get_gold_price"] = gold_data

    for item in tool_list:
        name = item.get("name")
        params = item.get("params", {}) or {}

        if name == "calculator":
            gold_price = gold_data.get("price_per_oz_usd") if (gold_data and gold_data.get("status") == "success") else None
            toman_rate = toman_data.get("rate_toman") if (toman_data and toman_data.get("status") == "success") else None
            
            calc_result = tools.calculator(
                usd_amount=params.get("usd_amount"),
                toman_amount=params.get("toman_amount"),
                gold_price_oz_usd=gold_price,
                toman_rate=toman_rate,
                expression=params.get("expression")
            )
            results["calculator"] = calc_result

    return results


def build_synthesize_prompt(user_question: str, tool_results: dict) -> tuple[str, str]:
    """Construct system prompt and user message for synthesize step."""
    system_prompt = (
        "You are an AI financial agent. Respond to the user's question in Persian based ONLY on the provided tool data.\n"
        "STRICT REQUIREMENTS:\n"
        "1. Base your answer strictly on the fetched data provided below.\n"
        "2. Do NOT invent, assume, or guess any price, exchange rate, math calculation, or statistic not present in the tool results.\n"
        "3. If historical data or Toman rate is reported as unavailable or missing in tool results, state honestly in Persian that this information is not available.\n"
        "4. Provide a clear, natural, and concise answer in Persian."
    )
    
    context_str = json.dumps(tool_results, ensure_ascii=False, indent=2)
    user_message = f"User Question: {user_question}\n\nTool Results:\n{context_str}"
    
    return system_prompt, user_message


def synthesize_step(user_question: str, tool_results: dict) -> str:
    """Step 3: Call LLM to synthesize data-grounded final answer in Persian."""
    sys_prompt, user_msg = build_synthesize_prompt(user_question, tool_results)
    return call_omniroute_llm(sys_prompt, user_msg)


def run_agent(user_question: str) -> str:
    """Full Plan -> Act -> Synthesize execution pipeline with error handling."""
    try:
        plan = plan_step(user_question)
        tool_results = act_step(plan)
        final_answer = synthesize_step(user_question, tool_results)
        return final_answer
    except Exception as e:
        logger.error(f"Error in agent workflow: {e}", exc_info=True)
        return "متأسفانه در پردازش درخواست شما خطایی رخ داد. لطفاً از فعال بودن سرویس OmniRoute و اتصال اینترنت اطمینان حاصل کنید."

        cleaned = clean_json_text(raw_output)
        plan = json.loads(cleaned)
        if isinstance(plan, dict) and "tools" in plan:
            return plan
    except Exception as e:
        logger.warning(f"Plan parsing failed or OmniRoute call failed: {e}. Falling back to default plan.")
    
    return {"tools": [{"name": "get_gold_price"}, {"name": "get_toman_rate"}]}
