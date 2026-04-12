"""
Groq Inference client for financial news classification.

Uses Groq's free API (OpenAI-compatible) — fast, free tier: 14,400 req/day.
Get a free API key at: https://console.groq.com

Tries models in priority order, falling back if one is rate-limited.
"""

import json
import logging
import os
import time

import requests

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Models tried in order. If rate-limited, falls back to next.
MODELS = [
    "llama-3.1-8b-instant",   # Fast, good quality, high rate limit
    "gemma2-9b-it",           # Google Gemma fallback
    "mixtral-8x7b-32768",     # Mixtral fallback
]

VALID_EVENT_TYPES = {
    "earnings_report", "merger_acquisition", "product_launch",
    "regulatory_action", "executive_change", "lawsuit",
    "partnership", "other", "not_relevant",
}
VALID_SENTIMENTS = {"positive", "negative", "neutral"}

SYSTEM_PROMPT = """\
You are a financial news classifier for a stock market intelligence platform.

FIRST decide: is this article directly relevant to publicly traded companies or financial markets?

NOT relevant examples (return not_relevant):
- Sports, entertainment, celebrity news with no stock angle
- Pure science/space news not tied to a public company
- Local news, crime, politics with no market impact
- Food/lifestyle articles about non-public companies
- Any article where no publicly traded company is meaningfully affected

If NOT relevant, return: {"event_type": "not_relevant", "sentiment": "neutral", "confidence": 1.0}

If RELEVANT, classify into ONE event type and ONE sentiment:

Event types:
- earnings_report: quarterly/annual earnings results
- merger_acquisition: M&A deals, buyouts, takeovers
- product_launch: new products, services, or features announced
- regulatory_action: government or regulatory decisions, fines, approvals
- executive_change: CEO, CFO, or other leadership changes
- lawsuit: legal actions, settlements, court decisions
- partnership: business partnerships or joint ventures
- other: relevant to markets but does not fit the above

Sentiments:
- positive: good news for the company or stock price
- negative: bad news for the company or stock price
- neutral: factual reporting with unclear market impact

Return ONLY valid JSON with no extra text:
{"event_type": "...", "sentiment": "...", "confidence": 0.95}"""


def classify_article(title: str, content: str) -> dict:
    """
    Classify a financial news article using Groq's free inference API.

    Tries each model in MODELS in order. On 429 (rate limit) falls through
    to the next model. Returns a safe fallback dict if all models fail.

    Args:
        title:   Article headline.
        content: Article body text (truncated to fit token limit).

    Returns:
        Dict with keys: {event_type, sentiment, confidence}
    """
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        logger.error("GROQ_API_KEY not set. Cannot classify.")
        return {"event_type": "other", "sentiment": "neutral", "confidence": 0.0, "_permanent_failure": True}

    truncated_content = (content or "")[:3000]
    user_msg = f"Article Title: {title}\nArticle Content: {truncated_content}"

    payload = {
        "model": None,  # filled per model
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0.1,
        "max_tokens": 80,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    for model in MODELS:
        payload["model"] = model
        result = _call_model(GROQ_API_URL, headers, payload, model)
        if result is not None:
            return result
        logger.warning("Model %s failed or unavailable, trying next.", model)

    logger.error("All Groq models failed. Returning fallback classification.")
    return {"event_type": "other", "sentiment": "neutral", "confidence": 0.0, "_permanent_failure": True}


def _call_model(
    url: str,
    headers: dict,
    payload: dict,
    model_name: str,
    max_attempts: int = 3,
) -> dict | None:
    """
    Make one API call to a specific Groq model with retry logic.

    Args:
        url:          Groq chat completions URL.
        headers:      HTTP headers dict.
        payload:      JSON request body.
        model_name:   Human-readable model name for logging.
        max_attempts: Max retry attempts for transient errors.

    Returns:
        Parsed classification dict, or None if the model should be skipped.
    """
    delay = 5.0
    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)

            if response.status_code == 429:
                # Rate limited on this model — skip to next model
                logger.warning("%s rate limited (429). Skipping to next model.", model_name)
                return None

            if response.status_code == 401:
                logger.error("Groq API key invalid (401). Check GROQ_API_KEY in .env.")
                return None

            if response.status_code != 200:
                logger.warning(
                    "%s returned HTTP %d: %s",
                    model_name, response.status_code, response.text[:200],
                )
                return None

            data = response.json()
            raw_text = data["choices"][0]["message"]["content"]
            return _parse_response(raw_text, model_name)

        except requests.exceptions.Timeout:
            logger.warning("%s timed out (attempt %d/%d).", model_name, attempt, max_attempts)
        except requests.exceptions.RequestException as exc:
            logger.warning("%s request error (attempt %d/%d): %s", model_name, attempt, max_attempts, exc)

        if attempt < max_attempts:
            time.sleep(delay)
            delay *= 2

    return None


def _parse_response(raw: str, model_name: str) -> dict | None:
    """
    Extract and validate a JSON classification from the model's raw output.

    Args:
        raw:        Raw text returned by the model.
        model_name: Used only for logging.

    Returns:
        Validated dict with {event_type, sentiment, confidence}, or None.
    """
    text = raw.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    json_start = text.find("{")
    json_end = text.rfind("}") + 1
    if json_start < 0 or json_end <= json_start:
        logger.warning("%s: no JSON found in response: %.150s", model_name, raw)
        return None

    try:
        data = json.loads(text[json_start:json_end])
    except json.JSONDecodeError:
        logger.warning("%s: invalid JSON in response: %.150s", model_name, raw)
        return None

    event_type = data.get("event_type", "other")
    sentiment  = data.get("sentiment", "neutral")
    confidence = float(data.get("confidence", 0.5))

    if event_type not in VALID_EVENT_TYPES:
        logger.debug("%s: unknown event_type '%s', using 'other'.", model_name, event_type)
        event_type = "other"

    if sentiment not in VALID_SENTIMENTS:
        logger.debug("%s: unknown sentiment '%s', using 'neutral'.", model_name, sentiment)
        sentiment = "neutral"

    return {
        "event_type": event_type,
        "sentiment":  sentiment,
        "confidence": max(0.0, min(1.0, confidence)),
    }
