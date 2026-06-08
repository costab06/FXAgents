"""Sentiment analyst — retail positioning and social sentiment for FX."""

from __future__ import annotations

import asyncio
import json
import logging

from ..infrastructure.llm import LLMCallable
from ..infrastructure.settings import Settings
from .base import fetch_finnhub_fx_news

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an FX sentiment analyst specialising in retail trader positioning,
COT (Commitment of Traders) data, and social media sentiment.

Given available sentiment signals for a currency pair, provide a contrarian or
confirmatory sentiment analysis.

Respond with JSON only (no markdown fences):
{
  "key_points": ["...", "..."],
  "retail_positioning": "net_long|net_short|unknown",
  "sentiment_signal": "bullish_base|bearish_base|neutral",
  "contrarian_note": "...",
  "recommended_direction": "buy|sell|hold",
  "confidence": 0.0-1.0,
  "summary": "..."
}"""


async def _fetch_reddit_sentiment(pair: str, settings: Settings) -> list[str]:
    """Attempt to fetch relevant Reddit posts about the pair."""
    if not (settings.reddit_client_id and settings.reddit_client_secret):
        return []
    try:
        import asyncio
        loop = asyncio.get_event_loop()

        def _sync() -> list[str]:
            import praw
            reddit = praw.Reddit(
                client_id=settings.reddit_client_id,
                client_secret=settings.reddit_client_secret,
                user_agent=settings.reddit_user_agent,
            )
            posts = []
            query = pair[:3] + pair[3:]  # "EURUSD"
            for sub in ["Forex", "investing", "forex"]:
                try:
                    for post in reddit.subreddit(sub).search(query, limit=5, time_filter="week"):
                        posts.append(post.title)
                except Exception:
                    pass
            return posts[:15]

        return await loop.run_in_executor(None, _sync)
    except Exception:
        logger.exception("_fetch_reddit_sentiment failed for %s", pair)
        return []


async def run_sentiment_analyst(
    pair: str,
    llm: LLMCallable,
    settings: Settings,
) -> dict:
    """Gather sentiment signals and produce a sentiment analysis."""
    # Fetch Finnhub news and Reddit posts in parallel
    async def _no_articles():
        return []

    finnhub_articles, reddit_posts = await asyncio.gather(
        fetch_finnhub_fx_news(pair, settings.finnhub_api_key or "", days=7)
        if settings.finnhub_api_key else _no_articles(),
        _fetch_reddit_sentiment(pair, settings),
    )

    news_headlines = [a.get("title", "") for a in finnhub_articles[:10]]
    reddit_titles = reddit_posts[:10]

    base = pair[:3].upper()
    quote = pair[3:].upper()

    sections = []
    if news_headlines:
        sections.append("Recent news headlines:\n" + "\n".join(f"- {h}" for h in news_headlines))
    else:
        sections.append("News headlines: not available.")

    if reddit_titles:
        sections.append("Reddit discussion titles:\n" + "\n".join(f"- {t}" for t in reddit_titles))
    else:
        sections.append("Reddit: not available (no credentials or no posts found).")

    user_msg = f"""Currency pair: {pair} ({base}/{quote})

{chr(10).join(sections)}

Note: COT data is not available in real-time. Base your positioning estimate on
the tone of available signals and your knowledge of current retail FX positioning.

Provide a sentiment analysis for {pair}."""

    raw = await llm(SYSTEM_PROMPT, user_msg)
    try:
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        result = json.loads(text)
    except Exception:
        logger.warning("sentiment_analyst: failed to parse LLM response")
        result = {
            "key_points": [raw[:500]],
            "sentiment_signal": "neutral",
            "recommended_direction": "hold",
            "confidence": 0.3,
            "summary": raw[:300],
        }

    return result
