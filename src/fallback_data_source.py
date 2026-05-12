"""
Fallback data source modules.

For Taiwan stocks, use TWSE public quote API first.
For non-Taiwan symbols, Alpha Vantage can be used as a secondary fallback.
"""

import logging
import re
import requests
import time
from typing import Optional

logger = logging.getLogger(__name__)


class TaiwanExchangeSource:
    """Fetch Taiwan stock prices from TWSE public quote API."""

    BASE_URL = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Referer": "https://www.twse.com.tw/",
            "Accept": "application/json, text/javascript, */*; q=0.01",
        })

    @staticmethod
    def _normalize_taiwan_symbol(symbol: str) -> tuple[str, str]:
        """Convert Yahoo-style Taiwan symbols into TWSE ex_ch codes."""
        base = symbol.split(".")[0].strip()
        market = "tse"
        if symbol.upper().endswith(".TWO"):
            market = "otc"
        return market, base

    @staticmethod
    def _parse_price(value) -> Optional[float]:
        if value is None:
            return None
        text = str(value).strip()
        if not text or text in {"-", "--", "null"}:
            return None
        try:
            price = float(text)
            return price if price > 0 else None
        except ValueError:
            return None

    def get_current_price(self, symbol: str) -> Optional[float]:
        """Fetch current price for Taiwan stocks from TWSE."""
        try:
            market, code = self._normalize_taiwan_symbol(symbol)
            ex_ch = f"{market}_{code}.tw"
            params = {
                "ex_ch": ex_ch,
                "json": "1",
                "delay": "0",
            }

            response = self.session.get(self.BASE_URL, params=params, timeout=10)
            if response.status_code != 200:
                logger.warning(f"TWSE returned {response.status_code} for {symbol}")
                return None

            data = response.json()
            msg_array = data.get("msgArray", [])
            if not msg_array:
                logger.warning(f"No TWSE quote data for {symbol}")
                return None

            quote = msg_array[0]
            price = self._parse_price(quote.get("z"))
            if price is None:
                price = self._parse_price(quote.get("y"))

            if price is not None:
                logger.info(f"Got {symbol}: {price} from TWSE")
                return price

            logger.warning(f"No valid TWSE price for {symbol}")
            return None

        except Exception as e:
            logger.warning(f"TWSE request error for {symbol}: {str(e)}")
            return None


class AlphaVantageSource:
    """Fetch stock prices from Alpha Vantage API (free tier available)"""
    
    # Alpha Vantage free tier has 5 requests per minute limit
    MIN_REQUEST_INTERVAL = 12  # seconds between requests
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"
        self.last_request_time = 0
    
    def _wait_for_rate_limit(self):
        """Respect rate limit (5 requests per minute)"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.MIN_REQUEST_INTERVAL:
            sleep_time = self.MIN_REQUEST_INTERVAL - elapsed
            logger.debug(f"Alpha Vantage rate limit: waiting {sleep_time:.1f}s")
            time.sleep(sleep_time)
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Fetch current price from Alpha Vantage
        
        Args:
            symbol: Stock symbol (e.g., "2330.TW" for TSMC)
        
        Returns:
            float: Current price, or None if failed
        """
        if not self.api_key:
            logger.warning("Alpha Vantage API key not configured")
            return None
        
        try:
            self._wait_for_rate_limit()
            
            # Normalize symbol (Alpha Vantage is more reliable for US symbols)
            normalized_symbol = self._normalize_symbol(symbol)

            # Alpha Vantage free tier may not provide Taiwan quotes reliably.
            # Keep it for non-TW symbols only.
            if normalized_symbol.upper().endswith(".TW") or normalized_symbol.upper().endswith(".TWO"):
                logger.debug(f"Skipping Alpha Vantage for Taiwan symbol {symbol}")
                return None
            
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": normalized_symbol,
                "apikey": self.api_key,
            }
            
            logger.debug(f"Fetching {symbol} from Alpha Vantage...")
            response = requests.get(self.base_url, params=params, timeout=10)
            self.last_request_time = time.time()
            
            if response.status_code != 200:
                logger.warning(f"Alpha Vantage returned {response.status_code} for {symbol}")
                return None
            
            data = response.json()
            
            # Check for error responses
            if "Error Message" in data:
                logger.warning(f"Alpha Vantage error: {data['Error Message']}")
                return None
            
            if "Note" in data:
                logger.warning(f"Alpha Vantage rate limit: {data['Note']}")
                return None
            
            # Extract price from response
            quote = data.get("Global Quote", {})
            if not quote:
                logger.warning(f"No quote data from Alpha Vantage for {symbol}")
                return None
            
            price_str = quote.get("05. price")
            if not price_str:
                logger.warning(f"No price field in Alpha Vantage response for {symbol}")
                return None
            
            try:
                price = float(price_str)
                if price > 0:
                    logger.info(f"Got {symbol}: ${price} from Alpha Vantage")
                    return price
            except ValueError:
                logger.warning(f"Invalid price from Alpha Vantage: {price_str}")
            
            return None
            
        except requests.exceptions.Timeout:
            logger.warning(f"Alpha Vantage timeout for {symbol}")
            return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"Alpha Vantage request error for {symbol}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error from Alpha Vantage: {str(e)}")
            return None
    
    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        """
        Convert Yahoo Finance symbols to Alpha Vantage format
        
        Examples:
            2330.TW -> 2330.TW (no change needed)
            AAPL -> AAPL
        """
        # Alpha Vantage generally accepts the same format as Yahoo for stocks
        # but some Taiwan stocks might need adjustment
        return symbol
