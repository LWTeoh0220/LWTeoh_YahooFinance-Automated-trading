"""
Stock price monitoring module
"""

import logging
import time
from typing import Optional, Tuple

try:
    from fallback_data_source import AlphaVantageSource, TaiwanExchangeSource
except ImportError:  # pragma: no cover - supports package-style imports
    from src.fallback_data_source import AlphaVantageSource, TaiwanExchangeSource

logger = logging.getLogger(__name__)


class StockMonitor:
    """Handle stock price monitoring"""
    
    def __init__(self):
        self.failed_symbols = set()
        self.primary_source = None
        self.secondary_source = None
        self.twse_source = TaiwanExchangeSource()

    def set_fallback_source(self, api_key: Optional[str]):
        """Configure Alpha Vantage as the primary source."""
        if api_key:
            self.primary_source = AlphaVantageSource(api_key)
            logger.info("Primary data source (Alpha Vantage) configured")
        else:
            self.primary_source = None

    @staticmethod
    def _normalize_price(value) -> Optional[float]:
        """Normalize and validate a numeric price value."""
        if value is None:
            return None
        try:
            price = float(value)
            return price if price > 0 else None
        except (TypeError, ValueError):
            return None
    
    def get_current_price(
        self,
        symbol: str,
        timeout: int = 10,
        max_retries: int = 1,
        backoff_seconds: float = 1.5,
    ) -> Optional[float]:
        """
        Fetch current stock price with Alpha Vantage first.
        
        Args:
            symbol: Stock ticker symbol (e.g., "2330.TW" for TSMC)
            timeout: Request timeout in seconds
        
        Returns:
            float: Current price, None if failed
        """
        attempts = max(1, int(max_retries) + 1)
        symbol_is_tw = symbol.upper().endswith(".TW") or symbol.upper().endswith(".TWO")

        for attempt in range(1, attempts + 1):
            try:
                # 1) Alpha Vantage first
                if self.primary_source is not None:
                    price = self.primary_source.get_current_price(symbol)
                    if price is not None:
                        return price

                # 2) TWSE for Taiwan stocks
                if symbol_is_tw:
                    price = self.twse_source.get_current_price(symbol)
                    if price is not None:
                        return price

                if attempt < attempts:
                    sleep_seconds = backoff_seconds * attempt
                    logger.info(
                        f"No price for {symbol} on attempt {attempt}/{attempts}. "
                        f"Retrying in {sleep_seconds:.1f}s"
                    )
                    time.sleep(sleep_seconds)
                    continue

                logger.warning(f"No price data available for {symbol} from Alpha Vantage/TWSE")
                return None

            except Exception as e:
                error_text = str(e)
                if attempt < attempts:
                    sleep_seconds = backoff_seconds * attempt
                    logger.warning(
                        f"Error fetching {symbol} (attempt {attempt}/{attempts}): {error_text}. "
                        f"Retrying in {sleep_seconds:.1f}s"
                    )
                    time.sleep(sleep_seconds)
                    continue

                logger.error(f"Error fetching {symbol} from Alpha Vantage/TWSE: {error_text}")
                self.failed_symbols.add(symbol)
                return None
    
    def check_condition(self, current_price: float, target_price: float,
                       condition: str) -> bool:
        """
        Check if current price meets the condition
        
        Args:
            current_price: Current stock price
            target_price: Target price to compare against
            condition: Comparison operator (">=", "<=", ">", "<")
        
        Returns:
            bool: True if condition is met
        """
        try:
            if condition == ">=":
                return current_price >= target_price
            elif condition == "<=":
                return current_price <= target_price
            elif condition == ">":
                return current_price > target_price
            elif condition == "<":
                return current_price < target_price
            else:
                logger.error(f"Unknown condition: {condition}")
                return False
        except Exception as e:
            logger.error(f"Error checking condition: {str(e)}")
            return False
    
    def analyze_stock(self, symbol: str, target_price: float,
                     condition: str = ">=", max_retries: int = 3,
                     backoff_seconds: float = 2.0) -> Tuple[bool, Optional[float]]:
        """
        Analyze if a stock triggers the alert condition
        
        Args:
            symbol: Stock ticker symbol
            target_price: Target price threshold
            condition: Comparison condition
        
        Returns:
            Tuple: (triggered: bool, current_price: float or None)
        """
        current_price = self.get_current_price(
            symbol,
            max_retries=max_retries,
            backoff_seconds=backoff_seconds,
        )
        
        if current_price is None:
            return False, None
        
        triggered = self.check_condition(current_price, target_price, condition)
        return triggered, current_price
