#!/usr/bin/env python3
"""
NexoCrypto UserBot API - Interface para comunicação com o userbot
Permite autenticação e gerenciamento via HTTP
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio
import threading
import logging
from userbot import userbot

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Loop de eventos para operações assíncronas
loop = None
loop_thread = None

def start_event_loop():
    """Inicia loop de eventos em thread separada"""
    global loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_forever()

def run_async(coro):
    """Executa corrotina no loop de eventos"""
    global loop
    if loop is None:
        return None
    
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout=30)

@app.route('/api/userbot/start-session', methods=['POST'])
def start_session():
    """Inicia sessão do usuário no Telegram"""
    try:
        data = request.get_json()
        uuid_code = data.get('uuid')
        phone_number = data.get('phone_number')
        
        if not uuid_code or not phone_number:
            return jsonify({
                'success': False,
                'error': 'UUID e número de telefone são obrigatórios'
            }), 400
        
        # Executa operação assíncrona
        result = run_async(userbot.start_session(uuid_code, phone_number))
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Erro ao iniciar sessão: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/userbot/verify-code', methods=['POST'])
def verify_code():
    """Verifica código de autenticação"""
    try:
        data = request.get_json()
        uuid_code = data.get('uuid')
        phone_number = data.get('phone_number')
        code = data.get('code')
        
        if not all([uuid_code, phone_number, code]):
            return jsonify({
                'success': False,
                'error': 'UUID, telefone e código são obrigatórios'
            }), 400
        
        # Executa operação assíncrona
        result = run_async(userbot.verify_code(uuid_code, phone_number, code))
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Erro ao verificar código: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/userbot/user-groups/<uuid_code>', methods=['GET'])
def get_user_groups(uuid_code):
    """Obtém grupos do usuário"""
    try:
        # Busca grupos do banco de dados
        import sqlite3
        conn = sqlite3.connect('nexocrypto_userbot.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT group_id, group_name, group_username, group_type, 
                   is_monitoring, signals_captured, last_signal_at
            FROM monitored_groups 
            WHERE user_uuid = ?
            ORDER BY group_name
        ''', (uuid_code,))
        
        groups = []
        for row in cursor.fetchall():
            groups.append({
                'id': row[0],
                'name': row[1],
                'username': row[2],
                'type': row[3],
                'is_monitored': bool(row[4]),
                'signals_count': row[5] or 0,
                'last_signal': row[6]
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'groups': groups
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter grupos: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/userbot/toggle-group-monitoring', methods=['POST'])
def toggle_group_monitoring():
    """Ativa/desativa monitoramento de grupo"""
    try:
        data = request.get_json()
        uuid_code = data.get('uuid')
        group_id = data.get('group_id')
        is_monitored = data.get('is_monitored')
        
        if not all([uuid_code, group_id is not None, is_monitored is not None]):
            return jsonify({
                'success': False,
                'error': 'UUID, group_id e is_monitored são obrigatórios'
            }), 400
        
        # Executa operação assíncrona
        run_async(userbot.toggle_group_monitoring(uuid_code, group_id, is_monitored))
        
        return jsonify({
            'success': True,
            'message': f"Grupo {'ativado' if is_monitored else 'desativado'} para monitoramento"
        })
        
    except Exception as e:
        logger.error(f"Erro ao alterar monitoramento: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/userbot/captured-signals/<uuid_code>', methods=['GET'])
def get_captured_signals(uuid_code):
    """Obtém sinais capturados do usuário"""
    try:
        limit = request.args.get('limit', 50, type=int)
        
        # Executa operação assíncrona
        signals = run_async(userbot.get_captured_signals(uuid_code, limit))
        
        return jsonify({
            'success': True,
            'signals': signals
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter sinais: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/userbot/status', methods=['GET'])
def get_status():
    """Obtém status do userbot"""
    try:
        import sqlite3
        conn = sqlite3.connect('nexocrypto_userbot.db')
        cursor = conn.cursor()
        
        # Conta sessões ativas
        cursor.execute('SELECT COUNT(*) FROM user_sessions WHERE is_active = TRUE')
        active_sessions = cursor.fetchone()[0]
        
        # Conta grupos monitorados
        cursor.execute('SELECT COUNT(*) FROM monitored_groups WHERE is_monitoring = TRUE')
        monitored_groups = cursor.fetchone()[0]
        
        # Conta sinais capturados hoje
        cursor.execute('''
            SELECT COUNT(*) FROM captured_signals 
            WHERE DATE(captured_at) = DATE('now')
        ''')
        signals_today = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'status': {
                'active_sessions': active_sessions,
                'monitored_groups': monitored_groups,
                'signals_today': signals_today,
                'userbot_running': True
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check da API"""
    return jsonify({
        'status': 'healthy',
        'service': 'nexocrypto-userbot-api'
    })

if __name__ == '__main__':
    # Inicializa banco de dados
    userbot.init_database()
    
    # Inicia loop de eventos em thread separada
    loop_thread = threading.Thread(target=start_event_loop, daemon=True)
    loop_thread.start()
    
    logger.info("🚀 NexoCrypto UserBot API iniciada!")
    logger.info("🔗 Endpoints disponíveis:")
    logger.info("  POST /api/userbot/start-session")
    logger.info("  POST /api/userbot/verify-code")
    logger.info("  GET  /api/userbot/user-groups/<uuid>")
    logger.info("  POST /api/userbot/toggle-group-monitoring")
    logger.info("  GET  /api/userbot/captured-signals/<uuid>")
    logger.info("  GET  /api/userbot/status")
    
    # Inicia servidor Flask
    app.run(host='0.0.0.0', port=5003, debug=False)

