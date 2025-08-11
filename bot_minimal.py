#!/usr/bin/env python3
"""
NexoCrypto Telegram Bot - Versão ULTRA SIMPLIFICADA
ZERO conflitos, ZERO polling, WEBHOOK PURO
"""

import os
import logging
import requests
from flask import Flask, request, jsonify
from datetime import datetime
import json

# Configuração de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configurações
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8287801389:AAGwcmDKhBLh1bJvGHFvKDiRBpxgnw23Kik')
BACKEND_URL = os.environ.get('BACKEND_URL', 'https://nexocrypto-backend.onrender.com')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', 'https://nexocrypto-telegram-bot.onrender.com')
PORT = int(os.environ.get('PORT', 10000))

# Flask app
app = Flask(__name__)

# Estado do webhook
webhook_configured = False

def send_telegram_message(chat_id, text, parse_mode='Markdown'):
    """Envia mensagem via API do Telegram"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode
        }
        response = requests.post(url, json=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem: {e}")
        return False

def setup_webhook():
    """Configura webhook do Telegram"""
    global webhook_configured
    try:
        # Remove webhook antigo
        delete_url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook"
        delete_data = {'drop_pending_updates': True}
        requests.post(delete_url, json=delete_data, timeout=10)
        logger.info("🧹 Webhook antigo removido")
        
        # Configura novo webhook
        webhook_endpoint = f"{WEBHOOK_URL}/webhook"
        set_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
        set_data = {
            'url': webhook_endpoint,
            'drop_pending_updates': True,
            'max_connections': 1
        }
        
        response = requests.post(set_url, json=set_data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                logger.info(f"✅ Webhook configurado: {webhook_endpoint}")
                webhook_configured = True
                return True
            else:
                logger.error(f"❌ Erro na resposta: {result}")
                return False
        else:
            logger.error(f"❌ Erro HTTP: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro ao configurar webhook: {e}")
        return False

def handle_start_command(chat_id, user_data):
    """Processa comando /start"""
    first_name = user_data.get('first_name', 'Usuário')
    
    message = f"""🚀 **Bem-vindo ao NexoCrypto Bot!**

Olá {first_name}! 👋

Este bot é usado para validar sua conta no sistema NexoCrypto e conectar seus grupos do Telegram para monitoramento de sinais de trading.

📋 **Comandos disponíveis:**
• `/start` - Mostra esta mensagem
• `/validate [UUID]` - Valida sua conta com o UUID

🔗 **Como usar:**
1. Copie seu UUID do painel NexoCrypto
2. Digite `/validate [seu-uuid]`
3. Compartilhe seu contato quando solicitado
4. Volte ao NexoCrypto e clique em "Verificar Validação"

💡 **Precisa de ajuda?**
Acesse: https://nexocrypto.app

Desenvolvido com ❤️ pela equipe NexoCrypto"""

    return send_telegram_message(chat_id, message)

def handle_validate_command(chat_id, user_data, args):
    """Processa comando /validate"""
    if not args:
        message = """❌ **UUID não fornecido**

Use: `/validate [seu-uuid]`

Copie o UUID do painel NexoCrypto e cole aqui."""
        return send_telegram_message(chat_id, message)
    
    uuid_code = args[0].strip()
    
    # Dados do usuário
    user_payload = {
        'user_uuid': uuid_code,
        'telegram_id': user_data.get('id'),
        'username': user_data.get('username', ''),
        'first_name': user_data.get('first_name', ''),
        'last_name': user_data.get('last_name', '')
    }
    
    # Envia para backend
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/telegram/validate",
            json=user_payload,
            timeout=10
        )
        
        if response.status_code == 200:
            message = """✅ **Validação bem-sucedida!**

📋 **PRÓXIMO PASSO IMPORTANTE:**
🔄 Volte para o NexoCrypto e clique no botão "Verificar Validação" para completar a conexão e carregar seus grupos do Telegram!

⚠️ Sem este passo, seus grupos não aparecerão na plataforma."""
        else:
            message = f"""⚠️ **Erro na validação**

Verifique se o UUID está correto e tente novamente.

Código de erro: {response.status_code}"""
            
    except Exception as e:
        logger.error(f"Erro ao conectar com backend: {e}")
        message = """⚠️ **Erro de conexão**

Não foi possível conectar com o servidor. Tente novamente em alguns minutos."""
    
    return send_telegram_message(chat_id, message)

def handle_contact(chat_id, user_data, contact_data):
    """Processa compartilhamento de contato"""
    if contact_data.get('user_id') != user_data.get('id'):
        message = """❌ **Contato inválido**

Por favor, compartilhe seu próprio contato."""
        return send_telegram_message(chat_id, message)
    
    # Dados do contato
    contact_payload = {
        'telegram_id': user_data.get('id'),
        'phone_number': contact_data.get('phone_number'),
        'first_name': contact_data.get('first_name', ''),
        'last_name': contact_data.get('last_name', '')
    }
    
    # Envia para backend
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/telegram/process-contact",
            json=contact_payload,
            timeout=10
        )
        
        if response.status_code == 200:
            message = """✅ **Contato recebido com sucesso!**

📋 **PRÓXIMO PASSO IMPORTANTE:**
🔄 Volte para o NexoCrypto e clique no botão "Verificar Validação" para completar a conexão e carregar seus grupos do Telegram!

⚠️ Sem este passo, seus grupos não aparecerão na plataforma."""
        else:
            message = """⚠️ **Erro ao processar contato**

Tente novamente ou entre em contato com o suporte."""
            
    except Exception as e:
        logger.error(f"Erro ao enviar contato para backend: {e}")
        message = """⚠️ **Erro de conexão**

Não foi possível processar seu contato. Tente novamente em alguns minutos."""
    
    return send_telegram_message(chat_id, message)

def handle_message(chat_id):
    """Processa mensagens gerais"""
    message = """👋 **Olá!**

Use `/start` para ver os comandos disponíveis.

Para validar sua conta, use:
`/validate [seu-uuid]`"""
    
    return send_telegram_message(chat_id, message)

@app.route('/')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'online',
        'service': 'NexoCrypto Telegram Bot',
        'mode': 'webhook_minimal',
        'webhook_configured': webhook_configured,
        'timestamp': datetime.now().isoformat(),
        'version': '4.0.0'
    })

@app.route('/ping')
def ping():
    """Ping endpoint"""
    return 'pong'

@app.route('/setup-webhook', methods=['POST'])
def setup_webhook_endpoint():
    """Endpoint para configurar webhook"""
    success = setup_webhook()
    return jsonify({
        'success': success,
        'webhook_configured': webhook_configured
    })

@app.route('/webhook', methods=['POST'])
def webhook():
    """Endpoint do webhook - PROCESSAMENTO DIRETO"""
    try:
        update_data = request.get_json()
        
        if not update_data:
            return jsonify({'status': 'no_data'}), 400
        
        # Extrai dados da mensagem
        message = update_data.get('message')
        if not message:
            return jsonify({'status': 'no_message'}), 200
        
        chat_id = message.get('chat', {}).get('id')
        user_data = message.get('from', {})
        text = message.get('text', '')
        contact = message.get('contact')
        
        if not chat_id:
            return jsonify({'status': 'no_chat_id'}), 400
        
        # Processa comandos
        if text.startswith('/start'):
            handle_start_command(chat_id, user_data)
            
        elif text.startswith('/validate'):
            args = text.split()[1:] if len(text.split()) > 1 else []
            handle_validate_command(chat_id, user_data, args)
            
        elif contact:
            handle_contact(chat_id, user_data, contact)
            
        elif text and not text.startswith('/'):
            handle_message(chat_id)
        
        return jsonify({'status': 'processed'})
        
    except Exception as e:
        logger.error(f"Erro no webhook: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    try:
        logger.info("🚀 Iniciando NexoCrypto Bot (MINIMAL WEBHOOK MODE)...")
        
        # Configura webhook na inicialização
        setup_webhook()
        
        logger.info(f"🌐 Iniciando servidor Flask MINIMAL na porta {PORT}")
        
        # Inicia servidor Flask
        app.run(
            host='0.0.0.0',
            port=PORT,
            debug=False,
            use_reloader=False
        )
        
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        exit(1)

