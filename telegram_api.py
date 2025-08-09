#!/usr/bin/env python3
"""
NexoCrypto Telegram API
Sistema de integração entre bot Telegram e frontend
"""

import os
import json
import uuid
import sqlite3
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

# Configurações
BOT_TOKEN = "8287801389:AAGwcmDKhBLh1bJvGHFvKDiRBpxgnw23Kik"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
DATABASE_PATH = "/home/ubuntu/nexocrypto-telegram/nexocrypto.db"

def init_database():
    """Inicializa o banco de dados"""
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
    
    conn.commit()
    conn.close()

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
        
        return jsonify({
            'success': True,
            'uuid': new_uuid,
            'bot_username': '@nexocrypto_trading_bot',
            'validation_command': f'/validate {new_uuid}'
        })
    except Exception as e:
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
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/validate-user', methods=['POST'])
def validate_user():
    """Endpoint para validar usuário via bot"""
    try:
        data = request.get_json()
        uuid_code = data.get('uuid')
        telegram_id = data.get('telegram_id')
        username = data.get('username', '')
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users 
            SET validated = TRUE, telegram_id = ?, username = ?
            WHERE uuid = ?
        ''', (telegram_id, username, uuid_code))
        
        if cursor.rowcount > 0:
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': 'Usuário validado com sucesso'})
        else:
            conn.close()
            return jsonify({'success': False, 'error': 'UUID não encontrado'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/add-group', methods=['POST'])
def add_group():
    """Adiciona grupo para monitoramento"""
    try:
        data = request.get_json()
        uuid_code = data.get('uuid')
        group_id = data.get('group_id')
        group_name = data.get('group_name')
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO telegram_groups (user_uuid, group_id, group_name)
            VALUES (?, ?, ?)
        ''', (uuid_code, group_id, group_name))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Grupo adicionado com sucesso'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/process-signal', methods=['POST'])
def process_signal():
    """Processa sinal recebido do Telegram"""
    try:
        data = request.get_json()
        
        # Salva sinal no banco
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO trading_signals (
                group_id, symbol, direction, entry_price, stop_loss,
                take_profit_1, take_profit_2, take_profit_3,
                leverage, confidence_score, raw_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('group_id'),
            data.get('symbol'),
            data.get('direction'),
            data.get('entry_price'),
            data.get('stop_loss'),
            data.get('take_profit_1'),
            data.get('take_profit_2'),
            data.get('take_profit_3'),
            data.get('leverage', 1),
            data.get('confidence_score', 0.0),
            data.get('raw_message', '')
        ))
        
        # Atualiza contador de sinais do grupo
        cursor.execute('''
            UPDATE telegram_groups 
            SET signals_count = signals_count + 1
            WHERE id = ?
        ''', (data.get('group_id'),))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Sinal processado com sucesso'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'NexoCrypto Telegram API',
        'timestamp': datetime.now(timezone.utc).isoformat()
    })

if __name__ == '__main__':
    # Inicializa banco de dados
    init_database()
    
    # Inicia servidor
    port = int(os.environ.get('PORT', 5002))
    app.run(host='0.0.0.0', port=port, debug=True)

