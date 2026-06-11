"""FX market data aggregator and smart order router."""

from .aggregator import MarketAggregator
from .models import (
    AggregatedQuote,
    FeedStatus,
    Fill,
    OrderRequest,
    OrderStatus,
    OrderType,
    Quote,
    RoutingDecision,
    Side,
)
from .sor import SmartOrderRouter

__all__ = [
    "MarketAggregator",
    "SmartOrderRouter",
    "Quote",
    "AggregatedQuote",
    "OrderRequest",
    "Fill",
    "RoutingDecision",
    "Side",
    "OrderType",
    "OrderStatus",
    "FeedStatus",
]
