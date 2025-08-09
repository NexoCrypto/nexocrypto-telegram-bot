#!/usr/bin/env python3
"""
NexoCrypto Telegram Bot - Webhook Ultra Robust Version
Versão ultra-robusta com webhook otimizada para Render
"""

import os
import sys
import time
import signal
import logging
import asyncio
import threading
from datetime import datetime
from flask import Flask, jsonify, request
import requests
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Configuração de logging otimizada
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Configurações
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8287801389:AAGwcmDKhBLh1bJvGHFvKDiRBpxgnw23Kik')
BACKEND_URL = os.environ.get('BACKEND_URL', 'https://nexocrypto-backend.onrender.com')
PORT = int(os.environ.get('PORT', 10000))
WEBHOOK_URL = f"https://nexocrypto-telegram-bot.onrender.com/webhook"

# Flask app
app = Flask(__name__)

# Estado global
telegram_app = None
start_time = time.time()
last_activity = time.time()
shutdown_requested = False

@app.route('/')
def health_check():
    """Health check otimizado"""
    global last_activity
    last_activity = time.time()
    
    uptime = int(time.time() - start_time)
    return jsonify({
        'status': 'healthy',
        'service': 'nexocrypto-telegram-bot-webhook',
        'version': '2.0',
        'uptime_seconds': uptime,
        'uptime_formatted': f"{uptime//3600}h {(uptime%3600)//60}m",
        'webhook_active': True,
        'last_activity': datetime.fromtimestamp(last_activity).isoformat()
    }), 200

@app.route('/ping')
def ping():
    """Ping para keep-alive"""
    global last_activity
    last_activity = time.time()
    return jsonify({'pong': True, 'timestamp': datetime.now().isoformat()}), 200

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook do Telegram"""
    global last_activity, telegram_app
    
    try:
        last_activity = time.time()
        
        if not telegram_app:
            logger.error("❌ Telegram app não inicializada")
            return jsonify({'error': 'Bot not ready'}), 503
        
        # Processa update
        json_data = request.get_json()
        if json_data:
            update = Update.de_json(json_data, telegram_app.bot)
            # Processa de forma assíncrona
            asyncio.create_task(telegram_app.process_update(update))
            
        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        logger.error(f"❌ Erro no webhook: {e}")
        return jsonify({'error': str(e)}), 500

def intelligent_keepalive():
    """Keep-alive inteligente"""
    service_url = "https://nexocrypto-telegram-bot.onrender.com"
    
    while not shutdown_requested:
        try:
            # Aguarda 12 minutos (menor que 15min do Render)
            for _ in range(720):  # 12 * 60 segundos
                if shutdown_requested:
                    return
                time.sleep(1)
            
            # Self-ping
            try:
                response = requests.get(f"{service_url}/ping", timeout=10)
                if response.status_code == 200:
                    logger.info("✅ Keep-alive OK")
                else:
                    logger.warning(f"⚠️ Keep-alive: {response.status_code}")
            except Exception as e:
                logger.warning(f"⚠️ Keep-alive falhou: {e}")
                
        except Exception as e:
            logger.error(f"❌ Erro no keep-alive: {e}")
            time.sleep(60)

async def setup_webhook():
    """Configura webhook de forma robusta"""
    for attempt in range(3):
        try:
            logger.info(f"🔄 Configurando webhook (tentativa {attempt + 1}/3)...")
            
            # Remove webhook existente
            delete_response = requests.post(
                f'https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook',
                json={'drop_pending_updates': True},
                timeout=15
            )
            logger.info(f"Delete webhook: {delete_response.json()}")
            
            await asyncio.sleep(2)
            
            # Configura novo webhook
            webhook_response = requests.post(
                f'https://api.telegram.org/bot{BOT_TOKEN}/setWebhook',
                json={
                    'url': WEBHOOK_URL,
                    'allowed_updates': ['message'],
                    'drop_pending_updates': True
                },
                timeout=15
            )
            
            result = webhook_response.json()
            logger.info(f"Set webhook: {result}")
            
            if result.get('ok'):
                logger.info("✅ Webhook configurado!")
                return True
                
        except Exception as e:
            logger.error(f"❌ Erro webhook (tentativa {attempt + 1}): {e}")
            
        if attempt < 2:
            await asyncio.sleep(5)
    
    return False

# Handlers do Telegram
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    global last_activity
    last_activity = time.time()
    
    user = update.effective_user
    logger.info(f"Comando /start de {user.username or user.first_name}")
    
    welcome_message = f"""🤖 **Bem-vindo ao NexoCrypto Bot!**

Olá {user.first_name}! 👋

Este bot permite conectar sua conta NexoCrypto ao Telegram para:
• ✅ Validar sua identidade
• 📊 Receber sinais de trading
• 🤖 Configurar Auto Trading
• 📱 Gerenciar grupos conectados

**📋 Comandos disponíveis:**
/validate [UUID] - Validar UUID do sistema

**🔗 Acesse nossa plataforma:** https://nexocrypto.app

**🆘 Suporte:** Entre em contato através da plataforma

**⚡ Bot Webhook Ultra-Robusto - Disponível 24/7**"""
    
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

async def validate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /validate"""
    global last_activity
    last_activity = time.time()
    
    if not context.args:
        await update.message.reply_text(
            "❌ **Uso incorreto!**\n\n"
            "✅ **Uso correto:** `/validate SEU_UUID`\n\n"
            "🔗 **Obtenha seu UUID em:** https://nexocrypto.app",
            parse_mode='Markdown'
        )
        return
    
    uuid_code = context.args[0]
    user = update.effective_user
    
    # Armazena dados para validação
    context.user_data['pending_validation'] = {
        'uuid': uuid_code,
        'telegram_id': user.id,
        'username': user.username or '',
        'first_name': user.first_name or '',
        'last_name': user.last_name or ''
    }
    
    # Solicita contato
    keyboard = [[KeyboardButton("📱 Compartilhar Contato", request_contact=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        "🔐 **Para completar a validação, preciso do seu número de telefone.**\n\n"
        "📱 Clique no botão abaixo para compartilhar seu contato:\n\n"
        "⚠️ *Isso é necessário para capturar seus grupos do Telegram automaticamente.*",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa contato compartilhado"""
    global last_activity
    last_activity = time.time()
    
    try:
        contact = update.message.contact
        user = update.effective_user
        
        # Verifica validação pendente
        if 'pending_validation' not in context.user_data:
            await update.message.reply_text("❌ Nenhuma validação pendente. Use /validate primeiro.")
            return
        
        # Verifica se é o próprio contato
        if contact.user_id != user.id:
            await update.message.reply_text("❌ Por favor, compartilhe seu próprio contato.")
            return
        
        # Completa dados
        user_data = context.user_data['pending_validation']
        user_data['phone_number'] = contact.phone_number
        
        # Remove teclado
        await update.message.reply_text(
            "✅ Contato recebido! Processando validação...",
            reply_markup=ReplyKeyboardRemove()
        )
        
        # Envia para backend
        try:
            response = requests.post(
                f'{BACKEND_URL}/api/telegram/validate', 
                json=user_data, 
                timeout=20
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    success_message = f"""✅ **Validação Bem-Sucedida!**

🎉 Sua conta foi conectada com sucesso!

**👤 Dados Confirmados:**
• **Nome:** {user.first_name} {user.last_name or ''}
• **Username:** @{user.username or 'N/A'}
• **Telefone:** {contact.phone_number}
• **UUID:** `{user_data['uuid'][:8]}...{user_data['uuid'][-8:]}`

**🤖 Funcionalidades Ativadas:**
• ✅ Auto Trading
• ✅ Monitoramento de Sinais
• ✅ Captura de Grupos
• ✅ Análise com IA

**🔗 Acesse:** https://nexocrypto.app

**📋 PRÓXIMO PASSO IMPORTANTE:**
🔄 **Volte para o NexoCrypto** e clique no botão **"Verificar Validação"** para completar a conexão e carregar seus grupos do Telegram!

⚠️ *Sem este passo, seus grupos não aparecerão na plataforma.*

**⚡ Bot Webhook Ultra-Robusto - Disponível 24/7 sem interrupções!**"""
                    
                    await update.message.reply_text(success_message, parse_mode='Markdown')
                else:
                    await update.message.reply_text(
                        f"❌ **Erro na validação:** {data.get('error', 'Erro desconhecido')}"
                    )
            else:
                await update.message.reply_text(
                    "❌ **Erro de comunicação com o servidor.**\n\n"
                    "🔄 **Tente novamente em alguns minutos.**"
                )
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição: {e}")
            await update.message.reply_text(
                "❌ **Erro de conexão com o servidor.**\n\n"
                "🔄 **Verifique sua conexão e tente novamente.**"
            )
        
        # Limpa dados temporários
        context.user_data.pop('pending_validation', None)
        
    except Exception as e:
        logger.error(f"Erro no handle_contact: {e}")
        await update.message.reply_text(
            "❌ **Erro interno do bot.**\n\n"
            "🔄 **Tente novamente em alguns minutos.**"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa mensagens gerais"""
    global last_activity
    last_activity = time.time()
    
    await update.message.reply_text(
        "🤖 **Olá!**\n\n"
        "Use /start para ver os comandos disponíveis.\n\n"
        "**🔗 Acesse:** https://nexocrypto.app\n\n"
        "**⚡ Bot Webhook Ultra-Robusto - Sempre Disponível**"
    )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Handler de erros"""
    logger.error(f"Erro do bot: {context.error}")

def signal_handler(signum, frame):
    """Handler de sinais do sistema"""
    global shutdown_requested
    logger.info(f"🛑 Sinal {signum} recebido")
    shutdown_requested = True

def run_flask():
    """Executa Flask"""
    try:
        logger.info("🌐 Iniciando servidor Flask...")
        app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False, threaded=True)
    except Exception as e:
        logger.error(f"❌ Erro no Flask: {e}")

async def main():
    """Função principal"""
    global telegram_app, shutdown_requested
    
    try:
        logger.info("🚀 Iniciando NexoCrypto Bot Webhook Ultra-Robusto...")
        logger.info(f"🔗 Backend: {BACKEND_URL}")
        logger.info(f"🌐 Port: {PORT}")
        logger.info(f"🔗 Webhook: {WEBHOOK_URL}")
        
        # Configura sinais
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        # Inicia Flask
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
        
        # Aguarda Flask
        await asyncio.sleep(3)
        
        # Inicia keep-alive
        keepalive_thread = threading.Thread(target=intelligent_keepalive, daemon=True)
        keepalive_thread.start()
        
        # Cria aplicação Telegram
        telegram_app = Application.builder().token(BOT_TOKEN).build()
        
        # Adiciona handlers
        telegram_app.add_handler(CommandHandler("start", start_command))
        telegram_app.add_handler(CommandHandler("validate", validate_command))
        telegram_app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
        telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        telegram_app.add_error_handler(error_handler)
        
        # Configura webhook
        webhook_success = await setup_webhook()
        if not webhook_success:
            logger.error("❌ Falha crítica na configuração do webhook")
            return
        
        # Inicializa aplicação
        await telegram_app.initialize()
        await telegram_app.start()
        
        logger.info("✅ Bot Webhook Ultra-Robusto iniciado!")
        logger.info("⚡ Sistema webhook + keep-alive ativo!")
        
        # Loop principal
        while not shutdown_requested:
            await asyncio.sleep(1)
        
        logger.info("🛑 Iniciando shutdown...")
        
        # Cleanup
        await telegram_app.stop()
        await telegram_app.shutdown()
        
        logger.info("✅ Shutdown concluído")
        
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        sys.exit(1)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot interrompido")
    except Exception as e:
        logger.error(f"❌ Erro na execução: {e}")
        sys.exit(1)

