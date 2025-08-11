#!/usr/bin/env python3
"""
NexoCrypto Trading Bot - Versão Final Corrigida
Bot Telegram para validação de usuários do sistema NexoCrypto
"""

import os
import logging
import requests
from flask import Flask, request, jsonify
from telegram import Bot, Update
import asyncio
import threading
import json

# Configuração de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configurações
BOT_TOKEN = os.getenv('BOT_TOKEN')
BACKEND_URL = "https://nexocrypto-backend.onrender.com"
WEBHOOK_URL = "https://nexocrypto-telegram-bot.onrender.com/webhook"

# Inicializar Flask
app = Flask(__name__)

# Inicializar Bot
bot = Bot(token=BOT_TOKEN)

# Event loop para asyncio
loop = None
loop_thread = None

def start_event_loop():
    """Inicia event loop em thread separada"""
    global loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_forever()

def run_async(coro):
    """Executa corrotina no event loop"""
    global loop
    if loop is None:
        return
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout=30)

async def start_command(update: Update):
    """Comando /start"""
    try:
        welcome_message = """
🤖 **NexoCrypto Trading Bot**

Bem-vindo ao sistema de validação do NexoCrypto!

**Comandos disponíveis:**
• `/start` - Iniciar o bot
• `/validate [UUID]` - Validar seu UUID

**Como usar:**
1. Acesse https://nexocrypto.app
2. Vá em Auto Trading
3. Copie seu UUID
4. Use: `/validate [seu-uuid]`

🚀 **Pronto para começar!**
        """
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
        logger.info(f"Comando /start executado por {update.effective_user.username}")
    except Exception as e:
        logger.error(f"Erro no comando /start: {e}")
        await update.message.reply_text("❌ Erro interno. Tente novamente.")

async def validate_command(update: Update, uuid_code: str):
    """Comando /validate [UUID]"""
    try:
        if not uuid_code:
            await update.message.reply_text(
                "❌ **Uso incorreto!**\n\n"
                "Use: `/validate [seu-uuid]`\n\n"
                "Exemplo: `/validate e5a81254-af08-484d-b959-e0217f5321c7`",
                parse_mode='Markdown'
            )
            return

        user = update.effective_user
        
        # Salva dados do usuário no backend
        user_data = {
            'user_uuid': uuid_code,  # Campo correto para o backend
            'telegram_id': user.id,
            'username': user.username or '',
            'first_name': user.first_name or '',
            'last_name': user.last_name or ''
        }
        
        # Envia dados para o backend
        try:
            response = requests.post(
                f"{BACKEND_URL}/verify-userbot-code",
                json=user_data,
                timeout=10
            )
            
            if response.status_code == 200:
                await update.message.reply_text(
                    "✅ **Validação realizada com sucesso!**\n\n"
                    "Seu Telegram foi vinculado ao sistema NexoCrypto.\n"
                    "Agora você pode usar todas as funcionalidades do Auto Trading!",
                    parse_mode='Markdown'
                )
                logger.info(f"Validação bem-sucedida para UUID: {uuid_code}")
            else:
                await update.message.reply_text(
                    "❌ **UUID inválido ou expirado**\n\n"
                    "Verifique se:\n"
                    "• O UUID está correto\n"
                    "• Você copiou do site oficial\n"
                    "• Não passou muito tempo desde a geração",
                    parse_mode='Markdown'
                )
                logger.warning(f"Validação falhou para UUID: {uuid_code} - Status: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição para backend: {e}")
            await update.message.reply_text(
                "❌ **Erro de conexão**\n\n"
                "Não foi possível conectar ao servidor.\n"
                "Tente novamente em alguns minutos.",
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Erro no comando /validate: {e}")
        await update.message.reply_text("❌ Erro interno. Tente novamente.")

async def handle_message(update: Update):
    """Manipula mensagens gerais"""
    try:
        await update.message.reply_text(
            "🤖 **Comando não reconhecido**\n\n"
            "Use `/start` para ver os comandos disponíveis.",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Erro ao manipular mensagem: {e}")

def process_update_sync(update_data):
    """Processa updates do Telegram de forma síncrona"""
    try:
        update = Update.de_json(update_data, bot)
        
        if update.message and update.message.text:
            text = update.message.text.strip()
            
            if text.startswith('/start'):
                run_async(start_command(update))
            elif text.startswith('/validate'):
                # Extrair UUID do comando
                parts = text.split()
                uuid_code = parts[1] if len(parts) > 1 else ""
                run_async(validate_command(update, uuid_code))
            else:
                run_async(handle_message(update))
                
    except Exception as e:
        logger.error(f"Erro ao processar update: {e}")

# Rotas Flask
@app.route('/')
def home():
    return jsonify({
        'status': 'online',
        'bot': 'NexoCrypto Trading Bot',
        'version': '1.0.0'
    })

@app.route('/webhook', methods=['POST'])
def webhook():
    """Endpoint do webhook para receber updates do Telegram"""
    try:
        json_data = request.get_json()
        
        if not json_data:
            return jsonify({'error': 'No JSON data'}), 400
            
        # Processar update de forma síncrona
        process_update_sync(json_data)
        
        return jsonify({'status': 'ok'})
        
    except Exception as e:
        logger.error(f"Erro no webhook: {e}")
        return jsonify({'error': str(e)}), 500

def setup_webhook():
    """Configura o webhook do bot"""
    try:
        # Configurar webhook de forma síncrona
        import requests
        
        webhook_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
        data = {'url': WEBHOOK_URL}
        
        response = requests.post(webhook_url, json=data, timeout=10)
        
        if response.status_code == 200:
            logger.info(f"✅ Webhook configurado: {WEBHOOK_URL}")
            return True
        else:
            logger.error(f"❌ Erro ao configurar webhook: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro ao configurar webhook: {e}")
        return False

def main():
    """Função principal"""
    try:
        logger.info("🚀 Iniciando NexoCrypto Bot (Versão Final Corrigida)...")
        
        if not BOT_TOKEN:
            logger.error("❌ BOT_TOKEN não encontrado!")
            return
            
        # Iniciar event loop em thread separada
        global loop_thread
        loop_thread = threading.Thread(target=start_event_loop, daemon=True)
        loop_thread.start()
        
        # Aguardar event loop inicializar
        import time
        time.sleep(1)
        
        # Configurar webhook
        webhook_success = setup_webhook()
        
        if not webhook_success:
            logger.error("❌ Falha ao configurar webhook!")
            return
            
        logger.info("🌐 Iniciando servidor Flask na porta 10000")
        
        # Iniciar servidor Flask
        port = int(os.environ.get('PORT', 10000))
        app.run(host='0.0.0.0', port=port, debug=False)
        
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")

if __name__ == '__main__':
    main()

