"""Data persistence layer for Law Agent using Chainlit's SQL Alchemy integration."""

from law_assistant.data.data_layer import get_data_layer, reset_data_layer

__all__ = ["get_data_layer", "reset_data_layer"]
