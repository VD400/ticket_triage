from sqlalchemy import Enum as SQLEnum, Column, ForeignKey, Integer, Numeric, DateTime, Text
from datetime import datetime, timezone
from sqlalchemy.orm import relationship
from .base import Base
import enum

class TransactionStatus(str, enum.Enum):
    FAILED = "failed"
    SUCCESS = "success"

class TransactionType(str, enum.Enum):
    SUBSCRIPTION = "subscription"
    ONE_TIME_PURCHASE = "one_time_purchase"
    UPGRADE = "upgrade"
    OTHER = "other"

class RefundStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    
class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    amount = Column(Numeric(10,2), nullable=False)
    status = Column(SQLEnum(TransactionStatus), nullable=False, default=TransactionStatus.SUCCESS)
    transaction_type = Column(SQLEnum(TransactionType), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    refund_status = Column(SQLEnum(RefundStatus), nullable=True)
    
    customer = relationship("Customer", back_populates="transactions")