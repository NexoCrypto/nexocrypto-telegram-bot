import re
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime

class SignalParser:
    def __init__(self):
        self.patterns = {
            'symbol': [
                r'([A-Z]{2,10}USDT?)',
                r'#([A-Z]{2,10})',
                r'([A-Z]{2,10})/USDT?',
                r'Coin:\s*([A-Z]{2,10})',
                r'Symbol:\s*([A-Z]{2,10})'
            ],
            'direction': [
                r'(LONG|SHORT|BUY|SELL)',
                r'Direction:\s*(LONG|SHORT|BUY|SELL)',
                r'Side:\s*(LONG|SHORT|BUY|SELL)',
                r'🟢\s*(LONG|BUY)',
                r'🔴\s*(SHORT|SELL)'
            ],
            'entry': [
                r'Entry:\s*([0-9.]+)',
                r'Buy:\s*([0-9.]+)',
                r'Price:\s*([0-9.]+)',
                r'Enter:\s*([0-9.]+)',
                r'@\s*([0-9.]+)'
            ],
            'stop_loss': [
                r'Stop Loss:\s*([0-9.]+)',
                r'SL:\s*([0-9.]+)',
                r'Stop:\s*([0-9.]+)',
                r'❌\s*([0-9.]+)'
            ],
            'take_profit': [
                r'Take Profit:\s*([0-9.]+)',
                r'TP:\s*([0-9.]+)',
                r'Target:\s*([0-9.]+)',
                r'🎯\s*([0-9.]+)',
                r'TP1:\s*([0-9.]+)',
                r'TP2:\s*([0-9.]+)',
                r'TP3:\s*([0-9.]+)'
            ],
            'leverage': [
                r'Leverage:\s*([0-9]+)x',
                r'([0-9]+)x',
                r'Lev:\s*([0-9]+)'
            ]
        }
    
    def parse_signal(self, message: str, group_type: str = 'generic') -> Optional[Dict]:
        """
        Parse a trading signal from Telegram message
        """
        try:
            # Clean message
            message = self._clean_message(message)
            
            # Extract basic info
            signal = {
                'symbol': self._extract_symbol(message),
                'direction': self._extract_direction(message),
                'entry_price': self._extract_entry(message),
                'stop_loss': self._extract_stop_loss(message),
                'take_profits': self._extract_take_profits(message),
                'leverage': self._extract_leverage(message),
                'original_message': message,
                'group_type': group_type,
                'parsed_at': datetime.utcnow().isoformat()
            }
            
            # Validate signal
            if self._validate_signal(signal):
                return signal
            else:
                return None
                
        except Exception as e:
            print(f"Error parsing signal: {e}")
            return None
    
    def _clean_message(self, message: str) -> str:
        """Clean and normalize message"""
        # Remove emojis and special characters
        message = re.sub(r'[^\w\s\.\-\:\#\@\$\/]', ' ', message)
        # Normalize whitespace
        message = re.sub(r'\s+', ' ', message)
        return message.strip().upper()
    
    def _extract_symbol(self, message: str) -> Optional[str]:
        """Extract trading symbol"""
        for pattern in self.patterns['symbol']:
            match = re.search(pattern, message)
            if match:
                symbol = match.group(1)
                # Ensure USDT suffix
                if not symbol.endswith('USDT'):
                    symbol += 'USDT'
                return symbol
        return None
    
    def _extract_direction(self, message: str) -> Optional[str]:
        """Extract trade direction"""
        for pattern in self.patterns['direction']:
            match = re.search(pattern, message)
            if match:
                direction = match.group(1)
                # Normalize direction
                if direction in ['BUY', 'LONG']:
                    return 'LONG'
                elif direction in ['SELL', 'SHORT']:
                    return 'SHORT'
        return None
    
    def _extract_entry(self, message: str) -> Optional[float]:
        """Extract entry price"""
        for pattern in self.patterns['entry']:
            match = re.search(pattern, message)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        return None
    
    def _extract_stop_loss(self, message: str) -> Optional[float]:
        """Extract stop loss price"""
        for pattern in self.patterns['stop_loss']:
            match = re.search(pattern, message)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        return None
    
    def _extract_take_profits(self, message: str) -> List[float]:
        """Extract take profit levels"""
        take_profits = []
        for pattern in self.patterns['take_profit']:
            matches = re.findall(pattern, message)
            for match in matches:
                try:
                    tp = float(match)
                    if tp not in take_profits:
                        take_profits.append(tp)
                except ValueError:
                    continue
        return sorted(take_profits)
    
    def _extract_leverage(self, message: str) -> int:
        """Extract leverage"""
        for pattern in self.patterns['leverage']:
            match = re.search(pattern, message)
            if match:
                try:
                    leverage = int(match.group(1))
                    return min(leverage, 100)  # Cap at 100x
                except ValueError:
                    continue
        return 1  # Default leverage
    
    def _validate_signal(self, signal: Dict) -> bool:
        """Validate parsed signal"""
        required_fields = ['symbol', 'direction', 'entry_price']
        
        for field in required_fields:
            if not signal.get(field):
                return False
        
        # Additional validations
        if signal['entry_price'] <= 0:
            return False
            
        if signal['stop_loss'] and signal['stop_loss'] <= 0:
            return False
            
        return True
    
    def calculate_risk_reward(self, signal: Dict) -> Dict:
        """Calculate risk/reward ratio"""
        if not signal.get('entry_price') or not signal.get('stop_loss'):
            return {'risk_reward': 0, 'risk_percent': 0}
        
        entry = signal['entry_price']
        stop_loss = signal['stop_loss']
        take_profits = signal.get('take_profits', [])
        
        if signal['direction'] == 'LONG':
            risk = entry - stop_loss
            if take_profits:
                reward = take_profits[0] - entry
            else:
                reward = 0
        else:  # SHORT
            risk = stop_loss - entry
            if take_profits:
                reward = entry - take_profits[0]
            else:
                reward = 0
        
        if risk <= 0:
            return {'risk_reward': 0, 'risk_percent': 0}
        
        risk_reward = reward / risk if risk > 0 else 0
        risk_percent = (risk / entry) * 100
        
        return {
            'risk_reward': round(risk_reward, 2),
            'risk_percent': round(risk_percent, 2),
            'reward': round(reward, 4),
            'risk': round(risk, 4)
        }

