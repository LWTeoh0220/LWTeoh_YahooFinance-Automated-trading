"""
Main entry point for stock monitoring application
"""

import logging
import sys
import argparse
import os
import time
from pathlib import Path
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from database import Database
from line_notifier import LineNotifier
from stock_monitor import StockMonitor

# Ensure log directory exists in fresh CI runners.
Path("logs").mkdir(parents=True, exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/stock_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class StockMonitoringSystem:
    """Main monitoring system"""
    
    def __init__(self):
        self.config = Config()
        self.db = Database(self.config.database_path)
        self.notifier = LineNotifier(
            self.config.line_channel_token,
            self.config.line_user_id
        )
        self.monitor = StockMonitor()
        self.scheduler = BackgroundScheduler()
        
        # Initialize fallback data source
        alpha_vantage_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        if alpha_vantage_key:
            self.monitor.set_fallback_source(alpha_vantage_key)
    
    def run_check(self):
        """Execute price check for all configured stocks"""
        logger.info("=" * 60)
        logger.info(f"Starting stock monitoring cycle at {datetime.now()}")
        logger.info("=" * 60)
        
        enabled_stocks = self.config.get_enabled_stocks()
        
        if not enabled_stocks:
            logger.warning("No enabled stocks in configuration")
            return
        
        for stock in enabled_stocks:
            try:
                logger.info(f"\nChecking {stock.name} ({stock.symbol})")
                logger.info(f"   Target: {stock.target_price} ({stock.condition})")
                
                triggered, current_price = self.monitor.analyze_stock(
                    stock.symbol,
                    stock.target_price,
                    stock.condition,
                    max_retries=self.config.price_fetch_retries,
                    backoff_seconds=self.config.retry_backoff_seconds,
                )
                
                if current_price is None:
                    logger.warning(f"   Could not fetch price for {stock.symbol}")
                    continue
                
                logger.info(f"   Current Price: {current_price:.2f}")
                
                if triggered:
                    logger.info("   CONDITION MET")
                    
                    # Check cooldown before sending notification
                    if self.db.should_notify(
                        stock.symbol,
                        current_price,
                        stock.target_price,
                        stock.condition,
                        cooldown_minutes=self.config.notification_cooldown_minutes
                    ):
                        # Send LINE notification
                        if self.notifier.send_notification(
                            stock.symbol,
                            stock.name,
                            stock.target_price,
                            current_price,
                            stock.condition
                        ):
                            # Record in database
                            self.db.record_alert(
                                stock.symbol,
                                stock.name,
                                stock.target_price,
                                current_price,
                                stock.condition
                            )
                    else:
                        logger.info("   Cooldown period active, skipping notification")
                else:
                    logger.info("   Condition not met")
                    
            except Exception as e:
                logger.error(f"   Error processing {stock.symbol}: {str(e)}")

            # Small gap between symbols to reduce burst requests.
            if self.config.request_delay_seconds > 0:
                time.sleep(self.config.request_delay_seconds)
        
        logger.info("\n" + "=" * 60)
        logger.info("Monitoring cycle completed")
        logger.info("=" * 60)
    
    def start(self):
        """Start the monitoring system"""
        try:
            # Validate configuration
            self.config.validate()
            logger.info("Configuration validated")
            
            # Test LINE connection
            logger.info("Testing LINE connection...")
            if not self.notifier.test_connection():
                logger.error("Failed to connect to LINE. Check your credentials.")
                sys.exit(1)
            
            # Initial run
            logger.info("Running initial check...")
            self.run_check()
            
            # Schedule periodic checks
            interval_minutes = self.config.check_interval_minutes
            logger.info(f"\nScheduling checks every {interval_minutes} minutes")
            
            self.scheduler.add_job(
                self.run_check,
                'interval',
                minutes=interval_minutes,
                id='stock_check_job'
            )
            
            self.scheduler.start()
            logger.info("Scheduler started")
            
            # Keep running
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("\nShutting down...")
                self.scheduler.shutdown()
                logger.info("Monitoring system stopped")
                
        except ValueError as e:
            logger.error(f"Configuration error: {str(e)}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            sys.exit(1)


def main():
    """Entry point"""
    parser = argparse.ArgumentParser(description="Yahoo Finance stock monitor")
    parser.add_argument(
        "--mode",
        choices=["once", "daemon"],
        default="once" if os.getenv("GITHUB_ACTIONS") == "true" else "daemon",
        help="Run one check and exit (once), or run continuously on an interval (daemon)."
    )
    args = parser.parse_args()

    system = StockMonitoringSystem()

    if args.mode == "once":
        try:
            system.config.validate()
            logger.info("Configuration validated")
            system.run_check()
        except ValueError as e:
            logger.error(f"Configuration error: {str(e)}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            sys.exit(1)
        return

    system.start()


if __name__ == "__main__":
    main()
