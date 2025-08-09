#!/usr/bin/env python3
"""
NexoCrypto Telegram Bot - Versão Webhook CORRIGIDA
Elimina conflitos de múltiplas instâncias e garante webhook puro
"""

import os
import logging
import requests
from flask import Flask, request, jsonify
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio
import threading
from datetime import datetime

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

# Flask app para webhook
app = Flask(__name__)

class NexoCryptoBot:
    def __init__(self):
        self.bot = Bot(token=BOT_TOKEN)
        self.application = None
        self.webhook_configured = False
        
    async def clear_webhook_and_setup(self):
        """Remove webhook antigo e configura novo"""
        try:
            # Remove webhook existente primeiro
            await self.bot.delete_webhook(drop_pending_updates=True)
            logger.info("🧹 Webhook antigo removido")
            
            # Aguarda um pouco
            await asyncio.sleep(2)
            
            # Configura novo webhook
            webhook_url = f"{WEBHOOK_URL}/webhook"
            success = await self.bot.set_webhook(
                url=webhook_url,
                drop_pending_updates=True,
                max_connections=1  # Limita a 1 conexão para evitar conflitos
            )
            
            if success:
                logger.info(f"✅ Webhook configurado com sucesso: {webhook_url}")
                self.webhook_configured = True
                return True
            else:
                logger.error("❌ Falha ao configurar webhook")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erro ao configurar webhook: {e}")
            return False
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start"""
        try:
            user = update.effective_user
            welcome_message = f"""🚀 **Bem-vindo ao NexoCrypto Bot!**

Olá {user.first_name}! 👋

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

            await update.message.reply_text(welcome_message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Erro no comando start: {e}")
            await update.message.reply_text("❌ Erro interno. Tente novamente.")

    async def validate_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /validate"""
        try:
            if not context.args:
                await update.message.reply_text(
                    "❌ **UUID não fornecido**\n\n"
                    "Use: `/validate [seu-uuid]`\n\n"
                    "Copie o UUID do painel NexoCrypto e cole aqui.",
                    parse_mode='Markdown'
                )
                return

            uuid_code = context.args[0].strip()
            user = update.effective_user
            
            # Salva dados do usuário no backend
            user_data = {
                'uuid': uuid_code,
                'telegram_id': user.id,
                'username': user.username or '',
                'first_name': user.first_name or '',
                'last_name': user.last_name or ''
            }
            
            # Envia dados para o backend
            try:
                response = requests.post(
                    f"{BACKEND_URL}/api/telegram/validate",
                    json=user_data,
                    timeout=10
                )
                
                if response.status_code == 200:
                    await update.message.reply_text(
                        "✅ **Validação bem-sucedida!**\n\n"
                        "📋 **PRÓXIMO PASSO IMPORTANTE:**\n"
                        "🔄 Volte para o NexoCrypto e clique no botão \"Verificar Validação\" "
                        "para completar a conexão e carregar seus grupos do Telegram!\n\n"
                        "⚠️ Sem este passo, seus grupos não aparecerão na plataforma.",
                        parse_mode='Markdown'
                    )
                else:
                    await update.message.reply_text(
                        "⚠️ **Erro na validação**\n\n"
                        "Verifique se o UUID está correto e tente novamente.\n\n"
                        f"Código de erro: {response.status_code}",
                        parse_mode='Markdown'
                    )
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Erro ao conectar com backend: {e}")
                await update.message.reply_text(
                    "⚠️ **Erro de conexão**\n\n"
                    "Não foi possível conectar com o servidor. "
                    "Tente novamente em alguns minutos.",
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"Erro no comando validate: {e}")
            await update.message.reply_text("❌ Erro interno. Tente novamente.")

    async def handle_contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa compartilhamento de contato"""
        try:
            contact = update.message.contact
            user = update.effective_user
            
            if contact.user_id != user.id:
                await update.message.reply_text(
                    "❌ **Contato inválido**\n\n"
                    "Por favor, compartilhe seu próprio contato.",
                    parse_mode='Markdown'
                )
                return
            
            # Processa contato no backend
            contact_data = {
                'telegram_id': user.id,
                'phone_number': contact.phone_number,
                'first_name': contact.first_name or '',
                'last_name': contact.last_name or ''
            }
            
            try:
                response = requests.post(
                    f"{BACKEND_URL}/api/telegram/process-contact",
                    json=contact_data,
                    timeout=10
                )
                
                if response.status_code == 200:
                    await update.message.reply_text(
                        "✅ **Contato recebido com sucesso!**\n\n"
                        "📋 **PRÓXIMO PASSO IMPORTANTE:**\n"
                        "🔄 Volte para o NexoCrypto e clique no botão \"Verificar Validação\" "
                        "para completar a conexão e carregar seus grupos do Telegram!\n\n"
                        "⚠️ Sem este passo, seus grupos não aparecerão na plataforma.",
                        parse_mode='Markdown'
                    )
                else:
                    await update.message.reply_text(
                        "⚠️ **Erro ao processar contato**\n\n"
                        "Tente novamente ou entre em contato com o suporte.",
                        parse_mode='Markdown'
                    )
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Erro ao enviar contato para backend: {e}")
                await update.message.reply_text(
                    "⚠️ **Erro de conexão**\n\n"
                    "Não foi possível processar seu contato. "
                    "Tente novamente em alguns minutos.",
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"Erro ao processar contato: {e}")
            await update.message.reply_text("❌ Erro interno. Tente novamente.")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa mensagens gerais"""
        try:
            await update.message.reply_text(
                "👋 **Olá!**\n\n"
                "Use `/start` para ver os comandos disponíveis.\n\n"
                "Para validar sua conta, use:\n"
                "`/validate [seu-uuid]`",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {e}")

    async def setup_application(self):
        """Configura a aplicação do bot SEM POLLING"""
        try:
            # Cria aplicação SEM inicializar polling
            self.application = Application.builder().token(BOT_TOKEN).build()
            
            # Adiciona handlers
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(CommandHandler("validate", self.validate_command))
            self.application.add_handler(MessageHandler(filters.CONTACT, self.handle_contact))
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
            
            # IMPORTANTE: Só inicializa, NÃO inicia polling
            await self.application.initialize()
            
            logger.info("✅ Aplicação do bot configurada (WEBHOOK MODE)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao configurar aplicação: {e}")
            return False

# Instância global do bot
nexocrypto_bot = NexoCryptoBot()

@app.route('/')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'online',
        'service': 'NexoCrypto Telegram Bot',
        'mode': 'webhook_only',
        'webhook_configured': nexocrypto_bot.webhook_configured,
        'timestamp': datetime.now().isoformat(),
        'version': '3.0.0'
    })

@app.route('/ping')
def ping():
    """Ping endpoint"""
    return 'pong'

@app.route('/webhook', methods=['POST'])
def webhook():
    """Endpoint do webhook - ÚNICO PONTO DE ENTRADA"""
    try:
        if not nexocrypto_bot.application:
            logger.error("Bot não inicializado")
            return jsonify({'error': 'Bot não inicializado'}), 500
            
        # Processa update do Telegram
        update_data = request.get_json()
        if update_data:
            update = Update.de_json(update_data, nexocrypto_bot.bot)
            
            # Processa update de forma assíncrona
            asyncio.create_task(nexocrypto_bot.application.process_update(update))
            
        return jsonify({'status': 'ok'})
        
    except Exception as e:
        logger.error(f"Erro no webhook: {e}")
        return jsonify({'error': str(e)}), 500

async def setup_bot():
    """Configura o bot APENAS com webhook"""
    try:
        logger.info("🚀 Iniciando NexoCrypto Bot (WEBHOOK ONLY MODE)...")
        
        # Configura aplicação SEM polling
        if not await nexocrypto_bot.setup_application():
            return False
            
        # Remove webhooks antigos e configura novo
        if not await nexocrypto_bot.clear_webhook_and_setup():
            return False
            
        logger.info("✅ Bot configurado com webhook exclusivo!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao configurar bot: {e}")
        return False

def run_bot_setup():
    """Executa setup do bot em thread separada"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(setup_bot())

if __name__ == '__main__':
    try:
        # Configura bot em thread separada
        bot_thread = threading.Thread(target=run_bot_setup)
        bot_thread.daemon = True
        bot_thread.start()
        
        # Aguarda configuração
        import time
        time.sleep(5)
        
        logger.info(f"🌐 Iniciando servidor Flask WEBHOOK ONLY na porta {PORT}")
        
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

