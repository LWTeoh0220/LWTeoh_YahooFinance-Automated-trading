"""
Configuration management module
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class StockConfig:
    """Single stock configuration"""
    
    def __init__(self, symbol: str, name: str, target_price: float, 
                 condition: str = ">=", enabled: bool = True):
        self.symbol = symbol
        self.name = name
        self.target_price = target_price
        self.condition = condition  # ">=", "<=", ">", "<"
        self.enabled = enabled
    
    def check_price(self, current_price: float) -> bool:
        """Check if current price meets condition"""
        if self.condition == ">=":
            return current_price >= self.target_price
        elif self.condition == "<=":
            return current_price <= self.target_price
        elif self.condition == ">":
            return current_price > self.target_price
        elif self.condition == "<":
            return current_price < self.target_price
        return False


class Config:
    """Main configuration class"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.stocks: List[StockConfig] = []
        self.settings: Dict[str, Any] = {}
        
        # LINE API credentials from environment
        self.line_channel_token = os.getenv("LINE_CHANNEL_TOKEN")
        self.line_channel_secret = os.getenv("LINE_CHANNEL_SECRET")
        self.line_user_id = os.getenv("LINE_USER_ID")
        
        # Settings from environment (env has highest priority)
        self._env_check_interval = os.getenv("CHECK_INTERVAL_MINUTES")
        self._env_database_path = os.getenv("DATABASE_PATH")

        # Effective settings (defaults, then overridden after config is loaded)
        self.check_interval_minutes = 15
        self.database_path = "stock_monitor.db"
        self.price_fetch_retries = 3
        self.retry_backoff_seconds = 2.0
        self.request_delay_seconds = 1.5
        self.notification_cooldown_minutes = 0
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        
        self.load_config()
        self._apply_runtime_settings()

    @staticmethod
    def _safe_int(value: Any, default: int) -> int:
        """Parse integer safely and fallback to default if parsing fails."""
        try:
            parsed = int(value)
            if parsed <= 0:
                return default
            return parsed
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_float(value: Any, default: float) -> float:
        """Parse float safely and fallback to default if parsing fails."""
        try:
            parsed = float(value)
            if parsed < 0:
                return default
            return parsed
        except (TypeError, ValueError):
            return default
    
    def load_config(self):
        """Load stock configuration from JSON file"""
        if not Path(self.config_file).exists():
            raise FileNotFoundError(f"Config file not found: {self.config_file}")
        
        with open(self.config_file, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        # Load stocks
        for stock_data in config_data.get("stocks", []):
            stock = StockConfig(
                symbol=stock_data["symbol"],
                name=stock_data["name"],
                target_price=stock_data["target_price"],
                condition=stock_data.get("condition", ">="),
                enabled=stock_data.get("enabled", True)
            )
            self.stocks.append(stock)
        
        # Load settings
        self.settings = config_data.get("settings", {})

    def _apply_runtime_settings(self):
        """Apply runtime settings with precedence: ENV > config.json > default."""
        config_interval = self.settings.get("check_interval_minutes", 15)
        config_db_path = self.settings.get("database_path", "stock_monitor.db")
        config_fetch_retries = self.settings.get("price_fetch_retries", 3)
        config_retry_backoff = self.settings.get("retry_backoff_seconds", 2.0)
        config_request_delay = self.settings.get("request_delay_seconds", 1.5)
        config_notification_cooldown = self.settings.get("notification_cooldown_minutes", 0)

        selected_interval = self._env_check_interval if self._env_check_interval is not None else config_interval
        selected_db_path = self._env_database_path if self._env_database_path is not None else config_db_path

        self.check_interval_minutes = self._safe_int(selected_interval, 15)
        self.database_path = str(selected_db_path).strip() if str(selected_db_path).strip() else "stock_monitor.db"
        self.price_fetch_retries = self._safe_int(config_fetch_retries, 3)
        self.retry_backoff_seconds = self._safe_float(config_retry_backoff, 2.0)
        self.request_delay_seconds = self._safe_float(config_request_delay, 1.5)
        self.notification_cooldown_minutes = self._safe_int(config_notification_cooldown, 0)
    
    def get_enabled_stocks(self) -> List[StockConfig]:
        """Get list of enabled stocks"""
        return [s for s in self.stocks if s.enabled]
    
    def validate(self) -> bool:
        """Validate all required configurations"""
        if not self.line_channel_token or not self.line_channel_secret or not self.line_user_id:
            raise ValueError("LINE credentials not configured in .env file")
        if not self.stocks:
            raise ValueError("No stocks configured in config.json")
        return True
