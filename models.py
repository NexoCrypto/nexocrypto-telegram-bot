from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import uuid

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(String(50), unique=True, nullable=False)
    username = Column(String(100))
    uuid_token = Column(String(100), unique=True)
    is_validated = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)

class TelegramGroup(Base):
    __tablename__ = 'telegram_groups'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    group_id = Column(String(50), nullable=False)
    group_name = Column(String(200))
    group_type = Column(String(50))  # binancekillers, bybitpro, etc
    is_active = Column(Boolean, default=True)
    is_validated = Column(Boolean, default=False)
    added_at = Column(DateTime, default=datetime.utcnow)

class Signal(Base):
    __tablename__ = 'signals'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    group_id = Column(String(50), nullable=False)
    
    # Signal Data
    symbol = Column(String(20), nullable=False)
    direction = Column(String(10), nullable=False)  # LONG/SHORT
    entry_price = Column(Float)
    stop_loss = Column(Float)
    take_profit_1 = Column(Float)
    take_profit_2 = Column(Float)
    take_profit_3 = Column(Float)
    leverage = Column(Integer, default=1)
    
    # Analysis
    confidence_score = Column(Float, default=0.0)
    technical_score = Column(Float, default=0.0)
    risk_score = Column(Float, default=0.0)
    
    # Metadata
    original_message = Column(Text)
    processed_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default='PENDING')  # PENDING, ACTIVE, CLOSED
    
    # Results
    pnl = Column(Float, default=0.0)
    is_profitable = Column(Boolean, default=None)

class ValidationToken(Base):
    __tablename__ = 'validation_tokens'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    token = Column(String(100), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# Database Setup
def create_database(database_url):
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    return engine

def get_session(engine):
    Session = sessionmaker(bind=engine)
    return Session()

def generate_uuid():
    return f"CRP-{str(uuid.uuid4())[:8].upper()}-{str(uuid.uuid4())[9:13].upper()}-{str(uuid.uuid4())[14:18].upper()}"

