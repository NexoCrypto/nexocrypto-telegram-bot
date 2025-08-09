import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    
    # Database Configuration
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///nexocrypto.db')
    
    # API Configuration
    API_BASE_URL = os.getenv('API_BASE_URL', 'https://nexocrypto-backend.onrender.com')
    
    # Security
    SECRET_KEY = os.getenv('SECRET_KEY', 'nexocrypto-secret-key-2025')
    
    # Validation
    UUID_EXPIRY_HOURS = 24
    
    # Signal Processing
    SIGNAL_CONFIDENCE_THRESHOLD = 0.7
    MAX_SIGNALS_PER_HOUR = 10
    
    # Supported Signal Formats
    SUPPORTED_GROUPS = [
        'binancekillers',
        'bybitpro', 
        'ravenpro',
        'tasso'
    ]

