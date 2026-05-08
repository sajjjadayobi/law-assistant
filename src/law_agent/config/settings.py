"""
Configuration management for Law Agent.

Uses Pydantic Settings to load configuration from:
1. config.yaml (defaults)
2. Environment variables (overrides)

Secrets (DB_PASSWORD, LLM_AUTH_TOKEN) should only be set via environment variables.
Model-agnostic: Uses LLM_AUTH_TOKEN and LLM_BASE_URL instead of provider-specific keys.
"""

import os
from pathlib import Path
from typing import Any, Literal, Union

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ModelConfig(BaseModel):
    """Configuration for LLM model."""

    name: str = Field(default="claude-sonnet-4.5", description="Name of the Claude model to use")
    temperature: float = Field(
        default=1.0,
        ge=0.0,
        le=2.0,
        description="Model temperature (0.0-2.0). Higher = more creative. Use 1.0 for balanced behavior.",
    )
    max_tokens: int = Field(
        default=4000, gt=0, le=16000, description="Maximum tokens for model response"
    )
    retries: int = Field(
        default=1, gt=0, le=10, description="Number of retries for transient LLM errors"
    )
    base_url: str | None = Field(
        default=None, description="Custom LLM API endpoint URL (reads from LLM_BASE_URL env var)"
    )
    auth_token: str | None = Field(
        default=None, description="Authentication token for LLM (reads from LLM_AUTH_TOKEN env var)"
    )

    def __init__(self, **data: Any):
        """Initialize ModelConfig and load from environment variables."""
        # Load from environment variables (model-agnostic)
        if "base_url" not in data and os.getenv("LLM_BASE_URL"):
            data["base_url"] = os.getenv("LLM_BASE_URL")
        if "auth_token" not in data and os.getenv("LLM_AUTH_TOKEN"):
            data["auth_token"] = os.getenv("LLM_AUTH_TOKEN")

        # Fallback to legacy ANTHROPIC_API_KEY for backwards compatibility
        if "auth_token" not in data and os.getenv("ANTHROPIC_API_KEY"):
            data["auth_token"] = os.getenv("ANTHROPIC_API_KEY")

        super().__init__(**data)


class DatabaseConfig(BaseModel):
    """Configuration for PostgreSQL database."""

    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, gt=0, lt=65536, description="Database port")
    database: str = Field(default="law_agent", description="Database name")
    user: str = Field(default="postgres", description="Database user")
    password: str = Field(default="", description="Database password (set via DB_PASSWORD env var)")
    pool_size: int = Field(
        default=5, gt=0, le=100, description="Minimum number of connections in the pool"
    )
    max_overflow: int = Field(
        default=10, gt=0, le=100, description="Maximum number of overflow connections"
    )
    echo: bool = Field(default=False, description="Log all SQL queries (for debugging)")


class SearchConfig(BaseModel):
    """Configuration for document search."""

    max_results: int = Field(
        default=20, gt=0, le=100, description="Maximum number of search results to return per query"
    )
    graph_traversal_depth: int = Field(
        default=2, gt=0, le=5, description="Maximum depth for following relations in document graph"
    )
    min_relevance_score: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Minimum relevance score threshold for search results",
    )
    hard_limit: int = Field(
        default=100,
        gt=0,
        le=1000,
        description="Hard maximum limit for search results (prevents excessive DB load)",
    )
    related_docs_default_limit: int = Field(
        default=10,
        gt=0,
        le=100,
        description="Default limit for related documents search",
    )
    relevance_score_step: float = Field(
        default=0.05,
        ge=0.01,
        le=0.1,
        description="Score decrement per result position for ranking",
    )
    max_tags_per_result: int = Field(
        default=3,
        gt=0,
        le=10,
        description="Maximum tags to include per search result (reduces token usage)",
    )
    relations_prefetch_limit: int = Field(
        default=1000,
        gt=0,
        le=10000,
        description="Maximum relations to prefetch when getting document details",
    )
    related_docs_relevance_score: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Fixed relevance score for documents related via citations",
    )


class ConversationConfig(BaseModel):
    """Configuration for multi-turn conversations."""

    max_turns: int = Field(
        default=50,
        gt=0,
        le=500,
        description="Hard limit on conversation turns to prevent runaway costs",
    )
    enable_context_history: bool = Field(
        default=True, description="Whether to use conversation history for context"
    )


class StarterQuestion(BaseModel):
    """A starter question for the Chainlit welcome screen."""

    message: str = Field(..., description="Full question text (used as button label)")
    icon: str = Field(
        default="/public/law.svg", description="Path to SVG icon for the starter button"
    )


class UIConfig(BaseModel):
    """Configuration for Chainlit UI."""

    show_thinking: bool = Field(default=True, description="Show model thinking/reasoning to user")
    show_tool_calls: bool = Field(default=True, description="Show tool calls and their parameters")
    enable_feedback: bool = Field(default=True, description="Enable thumbs up/down feedback")
    citation_base_url: str = Field(
        default="https://iran.ir/en/law",
        description="Base URL for citation links in agent responses",
    )
    example_questions: list[str] = Field(
        default=[
            "قوانین مرتبط با بیمه را بیان کنید",
            "مراحل ثبت شرکت چیست؟",
            "حقوق و تکالیف کارفرما چیست؟",
        ],
        description="Example questions to show users at startup (legacy)",
    )


class ObservabilityConfig(BaseModel):
    """Configuration for observability integration (Phoenix tracing/feedback)."""

    phoenix_endpoint: str = Field(
        default="http://localhost:6006",
        description="Arize Phoenix endpoint for sending feedback and spans",
    )
    http_timeout: float = Field(
        default=5.0,
        gt=0,
        le=60,
        description="HTTP timeout for requests to observability backend",
    )


class LoggingConfig(BaseModel):
    """Configuration for logging."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO", description="Logging level"
    )
    format: Literal["json", "text"] = Field(
        default="text", description="Log format (json for production, text for development)"
    )
    file_path: str | None = Field(
        default=None, description="Path to log file (if None, logs to console only)"
    )
    max_file_bytes: int = Field(
        default=10485760,
        gt=0,
        description="Maximum file size in bytes before rotation",
    )
    backup_count: int = Field(
        default=5,
        gt=0,
        le=100,
        description="Number of backup log files to keep",
    )


class Settings(BaseSettings):
    """Main configuration class that loads from config.yaml and environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        extra="allow",  # Allow extra env vars without validation error
    )

    model: ModelConfig = Field(default_factory=ModelConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    conversation: ConversationConfig = Field(default_factory=ConversationConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: Any,
        env_settings: Any,
        dotenv_settings: Any,
        file_secret_settings: Any,
    ) -> tuple[Any, ...]:
        """Customize the order of settings sources.

        Priority (highest to lowest):
        1. Environment variables
        2. Init settings (from kwargs)
        3. .env file settings
        4. Defaults
        """
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )

    @classmethod
    def from_yaml(cls, config_file: Union[str, Path] = "config.yaml") -> "Settings":
        """Load settings from YAML file and environment variables.

        Args:
            config_file: Path to config.yaml file

        Returns:
            Settings instance with values merged from YAML and env vars
        """
        import os

        config_file = Path(config_file)

        # Load YAML file if it exists
        yaml_data = {}
        if config_file.exists():
            with open(config_file) as f:
                content = yaml.safe_load(f)
                if content:
                    yaml_data = content

        # Apply environment variable overrides for nested fields
        # This handles settings like DATABASE__PASSWORD=value
        if yaml_data.get("database") is None:
            yaml_data["database"] = {}

        # Override database password from environment if set
        if "DB_PASSWORD" in os.environ:
            if not isinstance(yaml_data.get("database"), dict):
                yaml_data["database"] = {}
            yaml_data["database"]["password"] = os.environ["DB_PASSWORD"]

        # Create settings instance
        return cls(**yaml_data)


def get_settings() -> Settings:
    """Get or create the global Settings instance.

    This is the primary way to access configuration throughout the application.

    Returns:
        Settings instance
    """
    return Settings.from_yaml()
