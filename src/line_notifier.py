"""
LINE Messaging API notification module
"""

import logging
from linebot import LineBotApi
from linebot.exceptions import LineBotApiError
from linebot.models import TextSendMessage

logger = logging.getLogger(__name__)


class LineNotifier:
    """Handle LINE notifications"""
    
    def __init__(self, channel_token: str, user_id: str):
        self.line_bot_api = LineBotApi(channel_token)
        self.user_id = user_id
    
    def send_notification(self, stock_symbol: str, stock_name: str, 
                         target_price: float, actual_price: float,
                         condition: str) -> bool:
        """
        Send notification to LINE user
        
        Args:
            stock_symbol: Stock ticker symbol
            stock_name: Stock display name
            target_price: Target price that triggered alert
            actual_price: Current actual price
            condition: Price condition (">=", "<=", etc)
        
        Returns:
            bool: True if sent successfully, False otherwise
        """
        try:
            message_text = self._format_message(
                stock_symbol, stock_name, target_price, actual_price, condition
            )
            
            message = TextSendMessage(text=message_text)
            self.line_bot_api.push_message(self.user_id, message)
            
            logger.info(f"✅ LINE notification sent for {stock_symbol}")
            return True
            
        except LineBotApiError as e:
            logger.error(f"❌ LINE API Error: {e.status_code} - {e.error.message}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error sending LINE notification: {str(e)}")
            return False
    
    @staticmethod
    def _format_message(stock_symbol: str, stock_name: str, 
                       target_price: float, actual_price: float,
                       condition: str) -> str:
        """Format notification message"""
        condition_display = {
            ">=": "已达到或超过",
            "<=": "已跌至或低于",
            ">": "已超过",
            "<": "已低于"
        }
        
        message = f"""🚨 股票价格提醒

股票: {stock_name} ({stock_symbol})
目标价格: {target_price:.2f}
现价: {actual_price:.2f}
状态: {condition_display.get(condition, condition)}

触发时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return message
    
    def test_connection(self) -> bool:
        """Test LINE connection with a test message"""
        try:
            message = TextSendMessage(text="📋 股票监控系统已启动")
            self.line_bot_api.push_message(self.user_id, message)
            logger.info("✅ LINE connection test successful")
            return True
        except Exception as e:
            logger.error(f"❌ LINE connection test failed: {str(e)}")
            return False
