"""
Database management module using SQLite
"""

from datetime import datetime
from sqlalchemy import create_engine, Column, String, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pathlib import Path

Base = declarative_base()


class PriceAlert(Base):
    """Price alert notification record"""
    __tablename__ = "price_alerts"
    
    id = Column(String, primary_key=True)
    symbol = Column(String, nullable=False, index=True)
    stock_name = Column(String)
    target_price = Column(Float, nullable=False)
    actual_price = Column(Float, nullable=False)
    condition = Column(String)  # ">=", "<=", ">", "<"
    notified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now, index=True)
    notified_at = Column(DateTime)
    
    def __repr__(self):
        return f"<PriceAlert {self.symbol} @ {self.target_price} ({self.created_at})>"


class Database:
    """Database handler"""
    
    def __init__(self, db_path: str = "stock_monitor.db"):
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
    
    def record_alert(self, symbol: str, stock_name: str, target_price: float,
                    actual_price: float, condition: str) -> PriceAlert:
        """Record a price alert"""
        session = self.Session()
        try:
            from uuid import uuid4
            alert_id = str(uuid4())
            
            alert = PriceAlert(
                id=alert_id,
                symbol=symbol,
                stock_name=stock_name,
                target_price=target_price,
                actual_price=actual_price,
                condition=condition,
                notified=True,
                notified_at=datetime.now()
            )
            session.add(alert)
            session.commit()
            return alert
        finally:
            session.close()
    
    def get_last_alert_for_symbol(self, symbol: str) -> PriceAlert:
        """Get last alert for a symbol"""
        session = self.Session()
        try:
            alert = session.query(PriceAlert).filter(
                PriceAlert.symbol == symbol
            ).order_by(PriceAlert.created_at.desc()).first()
            return alert
        finally:
            session.close()
    
    def should_notify(self, symbol: str, current_price: float, target_price: float,
                     condition: str, cooldown_minutes: int = 30) -> bool:
        """
        Check if notification should be sent based on cooldown period
        Default: 30 minutes cooldown to prevent spam
        """
        session = self.Session()
        try:
            from datetime import timedelta
            
            last_alert = session.query(PriceAlert).filter(
                PriceAlert.symbol == symbol,
                PriceAlert.target_price == target_price,
                PriceAlert.condition == condition
            ).order_by(PriceAlert.created_at.desc()).first()
            
            if not last_alert:
                return True
            
            time_since_alert = datetime.now() - last_alert.created_at
            if time_since_alert > timedelta(minutes=cooldown_minutes):
                return True
            
            return False
        finally:
            session.close()
    
    def get_recent_alerts(self, limit: int = 10) -> list:
        """Get recent alerts for logging"""
        session = self.Session()
        try:
            alerts = session.query(PriceAlert).order_by(
                PriceAlert.created_at.desc()
            ).limit(limit).all()
            return alerts
        finally:
            session.close()
