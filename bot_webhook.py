#!/usr/bin/env python3
"""
NexoCrypto Trading Bot - Versão Simplificada
Bot Telegram para validação de usuários do sistema NexoCrypto
"""

import os
import logging
import requests
from flask import Flask, request, jsonify
from telegram import Bot, Update
from telegram.ext import CommandHandler, MessageHandler, filters, ContextTypes
import asyncio
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

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

async def validate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /validate [UUID]"""
    try:
        if not context.args:
            await update.message.reply_text(
                "❌ **Uso incorreto!**\n\n"
                "Use: `/validate [seu-uuid]`\n\n"
                "Exemplo: `/validate e5a81254-af08-484d-b959-e0217f5321c7`",
                parse_mode='Markdown'
            )
            return

        uuid_code = context.args[0].strip()
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

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manipula mensagens gerais"""
    try:
        await update.message.reply_text(
            "🤖 **Comando não reconhecido**\n\n"
            "Use `/start` para ver os comandos disponíveis.",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Erro ao manipular mensagem: {e}")

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
            
        # Processar update do Telegram
        update = Update.de_json(json_data, bot)
        
        # Executar handlers de forma assíncrona
        asyncio.create_task(process_update(update))
        
        return jsonify({'status': 'ok'})
        
    except Exception as e:
        logger.error(f"Erro no webhook: {e}")
        return jsonify({'error': str(e)}), 500

async def process_update(update: Update):
    """Processa updates do Telegram"""
    try:
        if update.message:
            if update.message.text:
                text = update.message.text.strip()
                
                if text.startswith('/start'):
                    await start_command(update, None)
                elif text.startswith('/validate'):
                    # Extrair argumentos do comando
                    parts = text.split()
                    if len(parts) > 1:
                        # Simular context.args
                        class MockContext:
                            def __init__(self, args):
                                self.args = args
                        
                        context = MockContext(parts[1:])
                        await validate_command(update, context)
                    else:
                        await validate_command(update, MockContext([]))
                else:
                    await handle_message(update, None)
                    
    except Exception as e:
        logger.error(f"Erro ao processar update: {e}")

async def setup_webhook():
    """Configura o webhook do bot"""
    try:
        # Configurar webhook
        await bot.set_webhook(url=WEBHOOK_URL)
        logger.info(f"✅ Webhook configurado: {WEBHOOK_URL}")
        return True
    except Exception as e:
        logger.error(f"❌ Erro ao configurar webhook: {e}")
        return False

def main():
    """Função principal"""
    try:
        logger.info("🚀 Iniciando NexoCrypto Bot (Versão Simplificada)...")
        
        if not BOT_TOKEN:
            logger.error("❌ BOT_TOKEN não encontrado!")
            return
            
        # Configurar webhook de forma assíncrona
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        webhook_success = loop.run_until_complete(setup_webhook())
        
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

