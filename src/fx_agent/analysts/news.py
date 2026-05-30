"""News analyst — FX-relevant news via Finnhub."""

from __future__ import annotations

import json
import logging

from ..infrastructure.llm import LLMCallable
from ..infrastructure.settings import Settings
from .base import fetch_finnhub_fx_news

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an FX news analyst. Given recent news headlines and summaries
relevant to a currency pair, assess the news-driven sentiment and potential price impact.

Respond with JSON only (no markdown fences):
{
  "key_points": ["...", "..."],
  "news_sentiment": "bullish_base|bearish_base|mixed|neutral",
  "impact_level": "high|medium|low",
  "key_themes": ["...", "..."],
  "recommended_direction": "buy|sell|hold",
  "confidence": 0.0-1.0,
  "summary": "...",
  "articles_reviewed": 0
}"""


async def run_news_analyst(
    pair: str,
    llm: LLMCallable,
    settings: Settings,
) -> dict:
    """Fetch FX news and produce a news analysis."""
    articles = []
    if settings.finnhub_api_key:
        articles = await fetch_finnhub_fx_news(pair, settings.finnhub_api_key, days=3)

    if articles:
        articles_text = "\n".join(
            f"- [{a.get('publisher', 'unknown')}] {a.get('title', '')}: {a.get('summary', '')[:200]}"
            for a in articles
        )
    else:
        articles_text = "No articles available from Finnhub."

    base = pair[:3].upper()
    quote = pair[3:].upper()

    user_msg = f"""Currency pair: {pair} ({base}/{quote})
Number of articles: {len(articles)}

Recent news:
{articles_text}

Analyse the news sentiment and its likely impact on {pair}."""

    raw = await llm(SYSTEM_PROMPT, user_msg)
    try:
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        result = json.loads(text)
    except Exception:
        logger.warning("news_analyst: failed to parse LLM response")
        result = {
            "key_points": [raw[:500]],
            "news_sentiment": "neutral",
            "recommended_direction": "hold",
            "confidence": 0.3,
            "summary": raw[:300],
            "articles_reviewed": len(articles),
        }

    result["articles_reviewed"] = len(articles)
    return result
