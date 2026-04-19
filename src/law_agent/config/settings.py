"""
Configuration management for Law Agent.

Uses Pydantic Settings to load configuration from:
1. config.yaml (defaults)
2. Environment variables (overrides)

Secrets (DB_PASSWORD, ANTHROPIC_API_KEY) should only be set via environment variables.
"""

from pathlib import Path
from typing import Any, Literal, Optional, Union

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
    base_url: Optional[str] = Field(
        default=None, description="Custom LLM API endpoint URL (optional, for development)"
    )
    auth_token: Optional[str] = Field(
        default=None, description="Authentication token for custom LLM endpoint (optional)"
    )


class DatabaseConfig(BaseModel):
    """Configuration for PostgreSQL database."""

    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, gt=0, lt=65536, description="Database port")
    database: str = Field(default="law_agent", description="Database name")
    user: str = Field(default="postgres", description="Database user")
    password: str = Field(default="", description="Database password (set via DB_PASSWORD env var)")


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


class UIConfig(BaseModel):
    """Configuration for Chainlit UI."""

    show_thinking: bool = Field(default=True, description="Show model thinking/reasoning to user")
    show_tool_calls: bool = Field(default=True, description="Show tool calls and their parameters")
    enable_feedback: bool = Field(default=True, description="Enable thumbs up/down feedback")
    example_questions: list[str] = Field(
        default=[
            "قوانین مرتبط با بیمه را بیان کنید",
            "مراحل ثبت شرکت چیست؟",
            "حقوق و تکالیف کارفرما چیست؟",
        ],
        description="Example questions to show users at startup",
    )


class LoggingConfig(BaseModel):
    """Configuration for logging."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO", description="Logging level"
    )
    format: Literal["json", "text"] = Field(
        default="text", description="Log format (json for production, text for development)"
    )
    file_path: Optional[str] = Field(
        default=None, description="Path to log file (if None, logs to console only)"
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
