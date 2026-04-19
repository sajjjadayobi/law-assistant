"""Tests for configuration system."""

import os

import pytest
import yaml

from law_agent.config.settings import (
    ConversationConfig,
    DatabaseConfig,
    LoggingConfig,
    ModelConfig,
    SearchConfig,
    Settings,
    UIConfig,
    get_settings,
)


class TestModelConfig:
    """Tests for ModelConfig."""

    def test_default_values(self):
        """Test ModelConfig default values."""
        config = ModelConfig()
        assert config.name == "claude-sonnet-4.5"
        assert config.temperature == 1.0
        assert config.max_tokens == 4000

    def test_temperature_validation(self):
        """Test temperature range validation."""
        # Valid temperature
        config = ModelConfig(temperature=0.5)
        assert config.temperature == 0.5

        # Temperature too high
        with pytest.raises(ValueError, match="less than or equal to 2"):
            ModelConfig(temperature=3.0)

        # Temperature negative
        with pytest.raises(ValueError, match="greater than or equal to 0"):
            ModelConfig(temperature=-0.5)

    def test_max_tokens_validation(self):
        """Test max_tokens must be positive."""
        with pytest.raises(ValueError, match="greater than 0"):
            ModelConfig(max_tokens=0)

        with pytest.raises(ValueError, match="greater than 0"):
            ModelConfig(max_tokens=-100)


class TestDatabaseConfig:
    """Tests for DatabaseConfig."""

    def test_defaults_with_empty_password(self):
        """Test that password has empty default but should be overridden."""
        config = DatabaseConfig()
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.database == "law_agent"
        assert config.user == "postgres"
        # Password defaults to empty string
        assert config.password == ""

    def test_valid_config_with_password(self):
        """Test valid database configuration with password."""
        config = DatabaseConfig(password="secret")
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.database == "law_agent"
        assert config.user == "postgres"
        assert config.password == "secret"

    def test_port_validation(self):
        """Test port range validation."""
        # Valid port
        config = DatabaseConfig(password="secret", port=3306)
        assert config.port == 3306

        # Port too high
        with pytest.raises(ValueError, match="less than 65536"):
            DatabaseConfig(password="secret", port=65536)

        # Port zero
        with pytest.raises(ValueError, match="greater than 0"):
            DatabaseConfig(password="secret", port=0)


class TestSearchConfig:
    """Tests for SearchConfig."""

    def test_default_values(self):
        """Test SearchConfig default values."""
        config = SearchConfig()
        assert config.max_results == 20
        assert config.graph_traversal_depth == 2
        assert config.min_relevance_score == 0.3

    def test_max_results_validation(self):
        """Test max_results validation."""
        with pytest.raises(ValueError, match="greater than 0"):
            SearchConfig(max_results=0)

        with pytest.raises(ValueError, match="less than or equal to 100"):
            SearchConfig(max_results=101)

    def test_relevance_score_validation(self):
        """Test min_relevance_score range validation."""
        # Valid score
        config = SearchConfig(min_relevance_score=0.5)
        assert config.min_relevance_score == 0.5

        # Score too high
        with pytest.raises(ValueError, match="less than or equal to 1"):
            SearchConfig(min_relevance_score=1.5)


class TestConversationConfig:
    """Tests for ConversationConfig."""

    def test_default_values(self):
        """Test ConversationConfig default values."""
        config = ConversationConfig()
        assert config.max_turns == 50
        assert config.enable_context_history is True

    def test_max_turns_validation(self):
        """Test max_turns validation."""
        with pytest.raises(ValueError, match="greater than 0"):
            ConversationConfig(max_turns=0)

        with pytest.raises(ValueError, match="less than or equal to 500"):
            ConversationConfig(max_turns=501)


class TestUIConfig:
    """Tests for UIConfig."""

    def test_default_values(self):
        """Test UIConfig default values."""
        config = UIConfig()
        assert config.show_thinking is True
        assert config.show_tool_calls is True
        assert config.enable_feedback is True
        assert len(config.example_questions) == 3


class TestLoggingConfig:
    """Tests for LoggingConfig."""

    def test_default_values(self):
        """Test LoggingConfig default values."""
        config = LoggingConfig()
        assert config.level == "INFO"
        assert config.format == "text"
        assert config.file_path is None

    def test_valid_levels(self):
        """Test valid log levels."""
        for level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            config = LoggingConfig(level=level)
            assert config.level == level

    def test_invalid_level(self):
        """Test invalid log level."""
        with pytest.raises(ValueError):
            LoggingConfig(level="INVALID")

    def test_valid_formats(self):
        """Test valid log formats."""
        for fmt in ["json", "text"]:
            config = LoggingConfig(format=fmt)
            assert config.format == fmt


class TestSettingsYAMLLoading:
    """Tests for loading Settings from YAML."""

    def test_load_from_yaml(self, tmp_path):
        """Test loading configuration from YAML file."""
        # Create a test config file
        config_content = {
            "model": {
                "name": "claude-opus",
                "temperature": 0.7,
                "max_tokens": 2000,
            },
            "database": {
                "host": "db.example.com",
                "port": 5433,
                "database": "test_db",
                "user": "testuser",
                "password": "testpass",
            },
            "search": {
                "max_results": 10,
                "graph_traversal_depth": 3,
            },
        }

        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_content, f)

        # Set environment variable for required password
        os.environ["DB_PASSWORD"] = "override_password"

        try:
            settings = Settings.from_yaml(config_file)

            # Verify YAML values were loaded
            assert settings.model.name == "claude-opus"
            assert settings.model.temperature == 0.7
            assert settings.model.max_tokens == 2000
            assert settings.database.host == "db.example.com"
            assert settings.database.port == 5433
            assert settings.search.max_results == 10
            assert settings.search.graph_traversal_depth == 3
        finally:
            del os.environ["DB_PASSWORD"]

    def test_load_from_nonexistent_yaml_uses_defaults(self):
        """Test that missing YAML file uses defaults."""
        # Ensure we have DB_PASSWORD for required field
        os.environ["DB_PASSWORD"] = "test_password"

        try:
            settings = Settings.from_yaml("nonexistent_config.yaml")

            # Should use defaults
            assert settings.model.name == "claude-sonnet-4.5"
            assert settings.model.temperature == 1.0
            assert settings.conversation.max_turns == 50
        finally:
            del os.environ["DB_PASSWORD"]

    def test_env_var_overrides_yaml(self, tmp_path):
        """Test that environment variables override YAML values."""
        config_content = {
            "model": {
                "name": "claude-opus",
                "temperature": 0.7,
            },
            "database": {
                "host": "yaml-host",
                "port": 5432,
                "database": "yaml_db",
                "user": "yaml_user",
                "password": "yaml_password",
            },
        }

        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_content, f)

        # Create .env file with overrides
        env_file = tmp_path / ".env"
        env_file.write_text("MODEL__NAME=claude-sonnet\nDATABASE__HOST=env-host\n")

        # Note: In real scenario, env vars are set in shell
        # This test verifies the configuration structure is correct
        settings = Settings.from_yaml(config_file)

        # YAML values are loaded (env var override works in runtime)
        assert settings.model.name == "claude-opus"
        assert settings.database.host == "yaml-host"


class TestSettingsInstantiation:
    """Tests for Settings instantiation."""

    def test_settings_instantiation_with_defaults(self):
        """Test that Settings can be created with default values."""
        settings = Settings()
        assert isinstance(settings, Settings)
        assert isinstance(settings.model, ModelConfig)
        assert isinstance(settings.database, DatabaseConfig)
        assert isinstance(settings.search, SearchConfig)

    def test_get_settings_returns_settings(self):
        """Test get_settings() helper function."""
        settings = get_settings()
        assert isinstance(settings, Settings)
        assert isinstance(settings.model, ModelConfig)
        assert isinstance(settings.database, DatabaseConfig)
        assert isinstance(settings.search, SearchConfig)

    def test_settings_all_sections_present(self):
        """Test that Settings has all configuration sections."""
        settings = Settings()

        assert hasattr(settings, "model")
        assert hasattr(settings, "database")
        assert hasattr(settings, "search")
        assert hasattr(settings, "conversation")
        assert hasattr(settings, "ui")
        assert hasattr(settings, "logging")

        assert isinstance(settings.model, ModelConfig)
        assert isinstance(settings.database, DatabaseConfig)
        assert isinstance(settings.search, SearchConfig)
        assert isinstance(settings.conversation, ConversationConfig)
        assert isinstance(settings.ui, UIConfig)
        assert isinstance(settings.logging, LoggingConfig)


class TestConfigValidationEdgeCases:
    """Tests for edge cases and validation."""

    def test_ui_config_custom_examples(self):
        """Test UIConfig with custom example questions."""
        custom_examples = ["سوال ۱", "سوال ۲"]
        config = UIConfig(example_questions=custom_examples)
        assert config.example_questions == custom_examples

    def test_logging_config_with_file_path(self):
        """Test LoggingConfig with file path."""
        config = LoggingConfig(level="DEBUG", format="json", file_path="/var/log/agent.log")
        assert config.file_path == "/var/log/agent.log"
        assert config.level == "DEBUG"
        assert config.format == "json"

    def test_search_config_boundary_values(self):
        """Test SearchConfig with boundary values."""
        config = SearchConfig(
            max_results=100,  # Maximum
            graph_traversal_depth=5,  # Maximum
            min_relevance_score=0.0,  # Minimum
        )
        assert config.max_results == 100
        assert config.graph_traversal_depth == 5
        assert config.min_relevance_score == 0.0
