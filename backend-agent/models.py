from sqlalchemy import Boolean, Column, String, DateTime
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"

    email = Column(String, primary_key=True, index=True)
    is_active = Column(Boolean, default=False)
    stripe_customer_id = Column(String, nullable=True)
    subscription_status = Column(String, default="inactive") # active, past_due, canceled, inactive
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
