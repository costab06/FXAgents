from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# FRED series IDs for policy/overnight interest rates by currency code.
# Used by the Macro and Carry analysts to calculate rate differentials.
FRED_RATE_SERIES: dict[str, str] = {
    "USD": "DFF",             # Federal Funds Effective Rate (daily)
    "EUR": "ECBDFR",          # ECB Deposit Facility Rate (daily)
    "GBP": "IUDSOIA",         # SONIA — Sterling Overnight Index Average (daily)
    "JPY": "IRSTCI01JPM156N", # Japan call rate (monthly)
    "CHF": "IRSTCI01CHM156N", # Switzerland call rate (monthly)
    "AUD": "RBACORR",         # RBA Cash Rate (monthly)
    "CAD": "CACOQMOV156N",    # Bank of Canada overnight rate (monthly)
    "NZD": "RBNZ_B",          # RBNZ official cash rate (monthly)
    "SEK": "IRSTCI01SEM156N", # Sweden call rate (monthly)
    "NOK": "IRSTCI01NOM156N", # Norway call rate (monthly)
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── Infrastructure ────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    postgres_dsn: str = "postgresql://postgres:postgres@localhost:5432/fx_agent"
    postgres_pool_max_size: int = 10

    # ── EventBus tuning ───────────────────────────────────────────────────────
    max_stream_length: int = 100_000
    max_retries: int = 3
    claim_interval_seconds: int = 30
    min_idle_time_ms: int = 30_000
    idempotency_ttl_seconds: int = 86_400

    # ── Stream names ──────────────────────────────────────────────────────────
    dlq_stream: str = "stream:dlq"
    ingest_prefix: str = "stream:ingest:"
    agent_prefix: str = "stream:agents:"

    routing: dict[str, list[str]] = Field(
        default={
            "fx_market": ["orchestrator"],
            "macro":     ["orchestrator"],
            "news":      ["orchestrator"],
        }
    )

    # ── Pipeline ──────────────────────────────────────────────────────────────
    debate_rounds: int = 2
    default_risk_tolerance: str = "neutral"

    # ── LLM model assignments ─────────────────────────────────────────────────
    llm_default_model: str = "claude-sonnet-4-6"

    agent_models: dict[str, str] = Field(
        default={
            # Analysts
            "macro-analyst":      "claude-opus-4-6",
            "carry-analyst":      "claude-sonnet-4-6",
            "technical-analyst":  "claude-sonnet-4-6",
            "sentiment-analyst":  "claude-sonnet-4-6",
            "news-analyst":       "claude-sonnet-4-6",
            # Researchers
            "bullish-researcher": "claude-opus-4-6",
            "bearish-researcher": "claude-opus-4-6",
            "debate-facilitator": "claude-opus-4-6",
            # Trader
            "trader":             "claude-opus-4-6",
            # Risk
            "risk-aggressive":    "claude-sonnet-4-6",
            "risk-neutral":       "claude-sonnet-4-6",
            "risk-conservative":  "claude-sonnet-4-6",
            "risk-facilitator":   "claude-opus-4-6",
            # Fund manager
            "fund-manager":       "claude-opus-4-6",
        }
    )

    # ── External API credentials ──────────────────────────────────────────────
    anthropic_api_key: str | None = None
    finnhub_api_key: str | None = None
    fred_api_key: str | None = None
    reddit_client_id: str | None = None
    reddit_client_secret: str | None = None
    reddit_user_agent: str = "fx-agent/1.0"

    # ── Default FX pairs ──────────────────────────────────────────────────────
    default_pairs: list[str] = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD"]

    # ── Session schedule ──────────────────────────────────────────────────────
    # Session open times (ET) that trigger the analysis cycle.
    # Format: "HH:MM"
    london_open_et: str = "03:00"
    newyork_open_et: str = "08:00"

    # ── REST server ───────────────────────────────────────────────────────────
    server_host: str = "0.0.0.0"
    server_port: int = Field(default=9000, validation_alias=AliasChoices("server_port", "PORT"))

    def model_for(self, agent_id: str) -> str:
        return self.agent_models.get(agent_id, self.llm_default_model)
