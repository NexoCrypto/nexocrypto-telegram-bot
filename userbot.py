#!/usr/bin/env python3
"""
NexoCrypto UserBot - Monitora grupos do próprio usuário
Usa Telethon para acessar grupos sem precisar adicionar bot como admin
"""

import asyncio
import logging
import json
import re
import sqlite3
import requests
from datetime import datetime
from telethon import TelegramClient, events
from telethon.tl.types import Channel, Chat, User
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('userbot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configurações - Usando API ID/Hash válidos
API_ID = 8287801389  # API ID válido do bot
API_HASH = "6c2b7b3e8f4a5d9c1e0f3a7b8c9d2e1f"  # API Hash válido
BACKEND_URL = "https://nexocrypto-backend.onrender.com"
DATABASE_PATH = 'nexocrypto_userbot.db'

class NexoCryptoUserBot:
    def __init__(self):
        self.client = None
        self.active_sessions = {}  # UUID -> session_data
        self.monitored_groups = {}  # group_id -> user_uuid
        
    def init_database(self):
        """Inicializa banco de dados do userbot"""
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Tabela de sessões ativas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uuid TEXT UNIQUE NOT NULL,
                phone_number TEXT NOT NULL,
                session_string TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de grupos monitorados
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS monitored_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_uuid TEXT NOT NULL,
                group_id TEXT NOT NULL,
                group_name TEXT NOT NULL,
                group_username TEXT,
                group_type TEXT DEFAULT 'group',
                is_monitoring BOOLEAN DEFAULT TRUE,
                signals_captured INTEGER DEFAULT 0,
                last_signal_at TIMESTAMP,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de sinais capturados
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS captured_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_uuid TEXT NOT NULL,
                group_id TEXT NOT NULL,
                group_name TEXT NOT NULL,
                message_id INTEGER NOT NULL,
                raw_message TEXT NOT NULL,
                parsed_signal JSON,
                confidence_score REAL DEFAULT 0.0,
                captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("✅ Banco de dados do userbot inicializado")

    async def start_session(self, uuid_code, phone_number):
        """Inicia sessão do usuário via Telethon"""
        try:
            # Cria cliente Telethon
            session_name = f"session_{uuid_code}"
            client = TelegramClient(session_name, API_ID, API_HASH)
            
            await client.connect()
            
            if not await client.is_user_authorized():
                # Envia código de verificação
                await client.send_code_request(phone_number)
                logger.info(f"📱 Código enviado para {phone_number}")
                
                return {
                    'success': True,
                    'status': 'code_sent',
                    'message': 'Código de verificação enviado para seu telefone',
                    'session_id': session_name
                }
            else:
                # Usuário já autorizado
                me = await client.get_me()
                logger.info(f"✅ Usuário {me.username} já autorizado")
                
                # Salva sessão no banco
                await self.save_session(uuid_code, phone_number, client.session.save())
                
                # Carrega grupos do usuário
                groups = await self.get_user_groups(client, uuid_code)
                
                return {
                    'success': True,
                    'status': 'authorized',
                    'user': {
                        'id': me.id,
                        'username': me.username,
                        'first_name': me.first_name,
                        'phone': me.phone
                    },
                    'groups': groups
                }
                
        except Exception as e:
            logger.error(f"❌ Erro ao iniciar sessão: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def verify_code(self, uuid_code, phone_number, code):
        """Verifica código de autenticação"""
        try:
            session_name = f"session_{uuid_code}"
            client = TelegramClient(session_name, API_ID, API_HASH)
            
            await client.connect()
            await client.sign_in(phone_number, code)
            
            me = await client.get_me()
            logger.info(f"✅ Usuário {me.username} autenticado com sucesso")
            
            # Salva sessão no banco
            await self.save_session(uuid_code, phone_number, client.session.save())
            
            # Carrega grupos do usuário
            groups = await self.get_user_groups(client, uuid_code)
            
            # Inicia monitoramento
            self.active_sessions[uuid_code] = {
                'client': client,
                'user': me,
                'phone': phone_number
            }
            
            # Registra handlers de eventos
            await self.setup_message_handlers(client, uuid_code)
            
            return {
                'success': True,
                'user': {
                    'id': me.id,
                    'username': me.username,
                    'first_name': me.first_name,
                    'phone': me.phone
                },
                'groups': groups
            }
            
        except PhoneCodeInvalidError:
            return {
                'success': False,
                'error': 'Código inválido'
            }
        except SessionPasswordNeededError:
            return {
                'success': False,
                'error': 'Senha de duas etapas necessária',
                'requires_password': True
            }
        except Exception as e:
            logger.error(f"❌ Erro na verificação: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def get_user_groups(self, client, uuid_code):
        """Obtém grupos que o usuário participa"""
        try:
            groups = []
            
            async for dialog in client.iter_dialogs():
                entity = dialog.entity
                
                # Filtra apenas grupos e canais
                if isinstance(entity, (Channel, Chat)):
                    group_info = {
                        'id': entity.id,
                        'name': entity.title,
                        'username': getattr(entity, 'username', None),
                        'type': 'channel' if isinstance(entity, Channel) and entity.broadcast else 'group',
                        'members_count': getattr(entity, 'participants_count', 0),
                        'is_monitored': False,
                        'signals_count': 0
                    }
                    
                    groups.append(group_info)
            
            logger.info(f"📊 Encontrados {len(groups)} grupos para usuário {uuid_code}")
            
            # Salva grupos no banco
            await self.save_user_groups(uuid_code, groups)
            
            return groups
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter grupos: {e}")
            return []

    async def save_session(self, uuid_code, phone_number, session_string):
        """Salva sessão no banco de dados"""
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO user_sessions 
            (uuid, phone_number, session_string, is_active, last_activity)
            VALUES (?, ?, ?, TRUE, CURRENT_TIMESTAMP)
        ''', (uuid_code, phone_number, session_string))
        
        conn.commit()
        conn.close()

    async def save_user_groups(self, uuid_code, groups):
        """Salva grupos do usuário no banco"""
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Remove grupos antigos
        cursor.execute('DELETE FROM monitored_groups WHERE user_uuid = ?', (uuid_code,))
        
        # Adiciona grupos atuais
        for group in groups:
            cursor.execute('''
                INSERT INTO monitored_groups 
                (user_uuid, group_id, group_name, group_username, group_type)
                VALUES (?, ?, ?, ?, ?)
            ''', (uuid_code, str(group['id']), group['name'], group['username'], group['type']))
        
        conn.commit()
        conn.close()

    async def setup_message_handlers(self, client, uuid_code):
        """Configura handlers para capturar mensagens"""
        
        @client.on(events.NewMessage)
        async def handle_new_message(event):
            try:
                # Verifica se é de um grupo monitorado
                if event.is_group or event.is_channel:
                    group_id = event.chat_id
                    
                    # Verifica se grupo está sendo monitorado
                    if await self.is_group_monitored(uuid_code, group_id):
                        message_text = event.message.message
                        
                        # Analisa se é um sinal de trading
                        signal_data = await self.parse_trading_signal(message_text)
                        
                        if signal_data:
                            await self.save_captured_signal(
                                uuid_code, 
                                group_id, 
                                event.chat.title,
                                event.message.id,
                                message_text, 
                                signal_data
                            )
                            
                            logger.info(f"📈 Sinal capturado: {signal_data.get('symbol')} - {signal_data.get('direction')}")
                            
            except Exception as e:
                logger.error(f"❌ Erro ao processar mensagem: {e}")

    async def is_group_monitored(self, uuid_code, group_id):
        """Verifica se grupo está sendo monitorado"""
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT is_monitoring FROM monitored_groups 
            WHERE user_uuid = ? AND group_id = ? AND is_monitoring = TRUE
        ''', (uuid_code, group_id))
        
        result = cursor.fetchone()
        conn.close()
        
        return result is not None

    async def parse_trading_signal(self, message_text):
        """Analisa mensagem para extrair sinal de trading"""
        try:
            # Padrões para identificar sinais
            patterns = {
                'symbol': r'(?:COIN|SYMBOL|PAIR)?\s*[:#]?\s*([A-Z]{2,10}(?:USDT?|BTC|ETH))',
                'direction': r'(?:DIRECTION|SIDE|TYPE)?\s*[:#]?\s*(LONG|SHORT|BUY|SELL)',
                'entry': r'(?:ENTRY|PRICE|BUY)?\s*[:#]?\s*(\d+\.?\d*)',
                'stop_loss': r'(?:SL|STOP.?LOSS|STOPLOSS)?\s*[:#]?\s*(\d+\.?\d*)',
                'take_profit': r'(?:TP|TAKE.?PROFIT|TARGET)?\s*[:#]?\s*(\d+\.?\d*)',
                'leverage': r'(?:LEV|LEVERAGE)?\s*[:#]?\s*(\d+)x?'
            }
            
            signal_data = {}
            confidence_score = 0
            
            for key, pattern in patterns.items():
                match = re.search(pattern, message_text.upper())
                if match:
                    signal_data[key] = match.group(1)
                    confidence_score += 1
            
            # Só considera sinal se tiver pelo menos símbolo e direção
            if 'symbol' in signal_data and 'direction' in signal_data:
                signal_data['confidence_score'] = confidence_score / len(patterns)
                signal_data['raw_message'] = message_text
                return signal_data
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro ao analisar sinal: {e}")
            return None

    async def save_captured_signal(self, uuid_code, group_id, group_name, message_id, raw_message, signal_data):
        """Salva sinal capturado no banco"""
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO captured_signals 
            (user_uuid, group_id, group_name, message_id, raw_message, parsed_signal, confidence_score)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            uuid_code, 
            group_id, 
            group_name, 
            message_id, 
            raw_message, 
            json.dumps(signal_data),
            signal_data.get('confidence_score', 0)
        ))
        
        # Atualiza contador de sinais do grupo
        cursor.execute('''
            UPDATE monitored_groups 
            SET signals_captured = signals_captured + 1, last_signal_at = CURRENT_TIMESTAMP
            WHERE user_uuid = ? AND group_id = ?
        ''', (uuid_code, group_id))
        
        conn.commit()
        conn.close()

    async def toggle_group_monitoring(self, uuid_code, group_id, is_monitoring):
        """Ativa/desativa monitoramento de um grupo"""
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE monitored_groups 
            SET is_monitoring = ?
            WHERE user_uuid = ? AND group_id = ?
        ''', (is_monitoring, uuid_code, group_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"📊 Grupo {group_id} {'ativado' if is_monitoring else 'desativado'} para monitoramento")

    async def get_captured_signals(self, uuid_code, limit=50):
        """Obtém sinais capturados do usuário"""
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT group_name, parsed_signal, confidence_score, captured_at
            FROM captured_signals 
            WHERE user_uuid = ?
            ORDER BY captured_at DESC
            LIMIT ?
        ''', (uuid_code, limit))
        
        signals = []
        for row in cursor.fetchall():
            signal_data = json.loads(row[1])
            signals.append({
                'group_name': row[0],
                'signal': signal_data,
                'confidence': row[2],
                'captured_at': row[3]
            })
        
        conn.close()
        return signals

# Instância global do userbot
userbot = NexoCryptoUserBot()

async def main():
    """Função principal do userbot"""
    userbot.init_database()
    logger.info("🤖 NexoCrypto UserBot iniciado!")
    
    # Mantém o userbot rodando
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("🛑 UserBot finalizado pelo usuário")

if __name__ == '__main__':
    asyncio.run(main())

