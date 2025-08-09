#!/usr/bin/env python3
"""
NexoCrypto Telegram API - Versão Otimizada
Sistema de integração entre bot Telegram e frontend
"""

import os
import sys
import json
import uuid
import sqlite3
import signal
import logging
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/ubuntu/nexocrypto-telegram/api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configurações
BOT_TOKEN = "8287801389:AAGwcmDKhBLh1bJvGHFvKDiRBpxgnw23Kik"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
DATABASE_PATH = "/home/ubuntu/nexocrypto-telegram/nexocrypto.db"

def signal_handler(signum, frame):
    """Handler para sinais de término"""
    logger.info(f"Recebido sinal {signum}, encerrando API...")
    sys.exit(0)

# Registra handlers de sinal
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

def init_database():
    """Inicializa o banco de dados"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Tabela de usuários
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uuid TEXT UNIQUE NOT NULL,
                telegram_id INTEGER,
                username TEXT,
                validated BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de grupos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS telegram_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_uuid TEXT NOT NULL,
                group_id INTEGER NOT NULL,
                group_name TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                signals_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_uuid) REFERENCES users (uuid)
            )
        ''')
        
        # Tabela de sinais
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trading_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL,
                entry_price REAL,
                stop_loss REAL,
                take_profit_1 REAL,
                take_profit_2 REAL,
                take_profit_3 REAL,
                leverage INTEGER DEFAULT 1,
                confidence_score REAL DEFAULT 0.0,
                raw_message TEXT,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (group_id) REFERENCES telegram_groups (id)
            )
        ''')
        
        # Criar índices para performance
        indices = [
            "CREATE INDEX IF NOT EXISTS idx_users_uuid ON users(uuid)",
            "CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id)",
            "CREATE INDEX IF NOT EXISTS idx_groups_user_uuid ON telegram_groups(user_uuid)",
            "CREATE INDEX IF NOT EXISTS idx_groups_status ON telegram_groups(status)",
            "CREATE INDEX IF NOT EXISTS idx_signals_group_id ON trading_signals(group_id)",
            "CREATE INDEX IF NOT EXISTS idx_signals_processed_at ON trading_signals(processed_at)"
        ]
        
        for index_sql in indices:
            try:
                cursor.execute(index_sql)
            except sqlite3.OperationalError:
                pass  # Índice já existe
        
        conn.commit()
        conn.close()
        logger.info("Banco de dados inicializado com sucesso")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao inicializar banco: {e}")
        return False

@app.route('/health', methods=['GET'])
def health_check():
    """Health check da API"""
    try:
        # Testa conexão com banco
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        
        return jsonify({
            'service': 'NexoCrypto Telegram API',
            'status': 'healthy',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'database': 'connected'
        })
    except Exception as e:
        logger.error(f"Health check falhou: {e}")
        return jsonify({
            'service': 'NexoCrypto Telegram API',
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 500

@app.route('/api/generate-uuid', methods=['POST'])
def generate_uuid():
    """Gera um novo UUID para validação"""
    try:
        new_uuid = f"CRP-{uuid.uuid4().hex[:8].upper()}-{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[:4].upper()}"
        
        # Salva no banco
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (uuid) VALUES (?)', (new_uuid,))
        conn.commit()
        conn.close()
        
        logger.info(f"UUID gerado: {new_uuid}")
        
        return jsonify({
            'success': True,
            'uuid': new_uuid,
            'bot_username': '@nexocrypto_trading_bot',
            'validation_command': f'/validate {new_uuid}'
        })
    except Exception as e:
        logger.error(f"Erro ao gerar UUID: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/check-validation/<uuid_code>', methods=['GET'])
def check_validation(uuid_code):
    """Verifica se UUID foi validado"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT validated, telegram_id, username FROM users WHERE uuid = ?', (uuid_code,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            validated, telegram_id, username = result
            return jsonify({
                'success': True,
                'validated': bool(validated),
                'telegram_id': telegram_id,
                'username': username
            })
        else:
            return jsonify({'success': False, 'error': 'UUID não encontrado'}), 404
    except Exception as e:
        logger.error(f"Erro ao verificar validação: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/user-groups/<uuid_code>', methods=['GET'])
def get_user_groups(uuid_code):
    """Retorna grupos conectados do usuário"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT g.group_id, g.group_name, g.status, g.signals_count, g.created_at
            FROM telegram_groups g
            WHERE g.user_uuid = ? AND g.status = 'active'
            ORDER BY g.created_at DESC
        ''', (uuid_code,))
        
        groups = []
        for row in cursor.fetchall():
            groups.append({
                'group_id': row[0],
                'group_name': row[1],
                'status': row[2],
                'signals_count': row[3],
                'created_at': row[4]
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'groups': groups
        })
    except Exception as e:
        logger.error(f"Erro ao buscar grupos: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/signals/<uuid_code>', methods=['GET'])
def get_user_signals(uuid_code):
    """Retorna sinais do usuário"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT s.symbol, s.direction, s.entry_price, s.stop_loss, 
                   s.take_profit_1, s.take_profit_2, s.take_profit_3,
                   s.leverage, s.confidence_score, s.processed_at, g.group_name
            FROM trading_signals s
            JOIN telegram_groups g ON s.group_id = g.id
            WHERE g.user_uuid = ?
            ORDER BY s.processed_at DESC
            LIMIT 50
        ''', (uuid_code,))
        
        signals = []
        for row in cursor.fetchall():
            signals.append({
                'symbol': row[0],
                'direction': row[1],
                'entry_price': row[2],
                'stop_loss': row[3],
                'take_profit_1': row[4],
                'take_profit_2': row[5],
                'take_profit_3': row[6],
                'leverage': row[7],
                'confidence_score': row[8],
                'processed_at': row[9],
                'source': row[10]
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'signals': signals
        })
    except Exception as e:
        logger.error(f"Erro ao buscar sinais: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/validate-user', methods=['POST'])
def validate_user():
    """Endpoint para validar usuário via bot"""
    try:
        data = request.get_json()
        uuid_code = data.get('uuid')
        telegram_id = data.get('telegram_id')
        username = data.get('username')
        
        if not uuid_code or not telegram_id:
            return jsonify({'success': False, 'error': 'UUID e telegram_id são obrigatórios'}), 400
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users 
            SET validated = 1, telegram_id = ?, username = ?
            WHERE uuid = ?
        ''', (telegram_id, username, uuid_code))
        
        if cursor.rowcount > 0:
            conn.commit()
            conn.close()
            logger.info(f"Usuário validado: {uuid_code} - {username}")
            return jsonify({'success': True, 'message': 'Usuário validado com sucesso'})
        else:
            conn.close()
            return jsonify({'success': False, 'error': 'UUID não encontrado'}), 404
            
    except Exception as e:
        logger.error(f"Erro ao validar usuário: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/add-group', methods=['POST'])
def add_group():
    """Adiciona grupo Telegram"""
    try:
        data = request.get_json()
        user_uuid = data.get('user_uuid')
        group_id = data.get('group_id')
        group_name = data.get('group_name')
        
        if not all([user_uuid, group_id, group_name]):
            return jsonify({'success': False, 'error': 'Dados incompletos'}), 400
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO telegram_groups (user_uuid, group_id, group_name)
            VALUES (?, ?, ?)
        ''', (user_uuid, group_id, group_name))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Grupo adicionado: {group_name} para {user_uuid}")
        
        return jsonify({'success': True, 'message': 'Grupo adicionado com sucesso'})
        
    except Exception as e:
        logger.error(f"Erro ao adicionar grupo: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/process-signal', methods=['POST'])
def process_signal():
    """Processa sinal de trading"""
    try:
        data = request.get_json()
        group_id = data.get('group_id')
        raw_message = data.get('message')
        
        if not group_id or not raw_message:
            return jsonify({'success': False, 'error': 'Dados incompletos'}), 400
        
        # Aqui seria implementado o parser de sinais
        # Por enquanto, salva como está
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO trading_signals (group_id, symbol, direction, raw_message)
            VALUES (?, ?, ?, ?)
        ''', (group_id, 'UNKNOWN', 'UNKNOWN', raw_message))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Sinal processado para grupo {group_id}")
        
        return jsonify({'success': True, 'message': 'Sinal processado'})
        
    except Exception as e:
        logger.error(f"Erro ao processar sinal: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint não encontrado'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Erro interno do servidor'}), 500

if __name__ == '__main__':
    logger.info("Iniciando NexoCrypto Telegram API...")
    
    # Inicializa banco de dados
    if not init_database():
        logger.error("Falha ao inicializar banco de dados")
        sys.exit(1)
    
    # Inicia servidor
    try:
        app.run(
            host='0.0.0.0',
            port=5002,
            debug=False,  # Desabilita debug em produção
            threaded=True,
            use_reloader=False
        )
    except Exception as e:
        logger.error(f"Erro ao iniciar servidor: {e}")
        sys.exit(1)

