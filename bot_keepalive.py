#!/usr/bin/env python3
"""
NexoCrypto Telegram Bot - Keep-Alive Version
Versão com sistema anti-sleep para plano gratuito do Render
"""

import os
import logging
import asyncio
import requests
import time
import threading
from datetime import datetime
from flask import Flask, jsonify
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Configuração de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configurações
BOT_TOKEN = os.getenv("BOT_TOKEN", "8287801389:AAGwcmDKhBLh1bJvGHFvKDiRBpxgnw23Kik")
BACKEND_URL = os.getenv("BACKEND_URL", "https://nexocrypto-backend.onrender.com")
PORT = int(os.getenv("PORT", 10000))

# Flask app para keep-alive
app = Flask(__name__)

@app.route('/')
def health_check():
    """Endpoint de health check para keep-alive"""
    return jsonify({
        'status': 'alive',
        'service': 'nexocrypto-telegram-bot',
        'timestamp': datetime.now().isoformat(),
        'uptime': time.time() - start_time
    })

@app.route('/ping')
def ping():
    """Endpoint de ping para keep-alive"""
    return jsonify({
        'pong': True,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/status')
def status():
    """Status detalhado do bot"""
    return jsonify({
        'bot_status': 'running',
        'keep_alive': True,
        'last_ping': datetime.now().isoformat(),
        'backend_url': BACKEND_URL,
        'port': PORT
    })

def keep_alive_service():
    """Serviço que mantém o bot ativo fazendo auto-ping"""
    service_url = f"https://nexocrypto-telegram-bot.onrender.com"
    
    while True:
        try:
            # Aguarda 10 minutos (600 segundos) - bem menor que o timeout do Render (15 min)
            time.sleep(600)
            
            # Faz ping para si mesmo
            try:
                response = requests.get(f"{service_url}/ping", timeout=30)
                if response.status_code == 200:
                    logger.info(f"✅ Keep-alive ping successful: {response.json()}")
                else:
                    logger.warning(f"⚠️ Keep-alive ping failed: {response.status_code}")
            except Exception as e:
                logger.warning(f"⚠️ Keep-alive ping error: {e}")
                
            # Ping adicional para o backend para manter ambos ativos
            try:
                response = requests.get(f"{BACKEND_URL}/health", timeout=30)
                logger.info(f"✅ Backend keep-alive: {response.status_code}")
            except Exception as e:
                logger.warning(f"⚠️ Backend ping error: {e}")
                
        except Exception as e:
            logger.error(f"❌ Keep-alive service error: {e}")
            time.sleep(60)  # Aguarda 1 minuto antes de tentar novamente

def force_webhook_cleanup():
    """Força limpeza completa do webhook para eliminar conflitos"""
    try:
        logger.info("🔄 Iniciando force takeover do webhook...")
        
        # Múltiplas tentativas agressivas de limpeza
        for attempt in range(5):
            logger.info(f"🔄 Tentativa {attempt + 1}/5 de force cleanup...")
            
            try:
                # Delete webhook com drop_pending_updates
                response = requests.post(
                    f'https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook',
                    json={'drop_pending_updates': True},
                    timeout=10
                )
                logger.info(f"Delete webhook: {response.json()}")
                
                # Set webhook vazio para forçar reset
                response = requests.post(
                    f'https://api.telegram.org/bot{BOT_TOKEN}/setWebhook',
                    json={'url': ''},
                    timeout=10
                )
                logger.info(f"Set empty webhook: {response.json()}")
                
                # Aguarda entre tentativas
                time.sleep(3)
                
            except Exception as e:
                logger.warning(f"Erro na tentativa {attempt + 1}: {e}")
                continue
        
        # Aguarda estabilização
        logger.info("⏳ Aguardando estabilização...")
        time.sleep(5)
        
        logger.info("🎯 Force takeover concluído!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro no force takeover: {e}")
        return False

def format_brazilian_time():
    """Retorna horário atual no formato brasileiro"""
    return datetime.now().strftime('%d/%m/%Y - %H:%M')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /start"""
    user = update.effective_user
    welcome_message = f"""
🤖 **Bem-vindo ao NexoCrypto Bot!**

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

**🔄 Bot Keep-Alive Ativo - Disponível 24/7**
    """
    
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

async def validate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /validate"""
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
    """Processa contato compartilhado e completa validação"""
    try:
        contact = update.message.contact
        user = update.effective_user
        
        # Verifica se há validação pendente
        if 'pending_validation' not in context.user_data:
            await update.message.reply_text("❌ Nenhuma validação pendente. Use /validate primeiro.")
            return
        
        # Verifica se o contato é do próprio usuário
        if contact.user_id != user.id:
            await update.message.reply_text("❌ Por favor, compartilhe seu próprio contato.")
            return
        
        # Completa dados do usuário
        user_data = context.user_data['pending_validation']
        user_data['phone_number'] = contact.phone_number
        
        # Remove teclado
        await update.message.reply_text(
            "✅ Contato recebido! Processando validação...",
            reply_markup=ReplyKeyboardRemove()
        )
        
        # Envia dados para o backend
        try:
            response = requests.post(f'{BACKEND_URL}/api/telegram/validate', 
                                   json=user_data, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    success_message = f"""
✅ **Validação Bem-Sucedida!**

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

**🔄 Bot Keep-Alive - Disponível 24/7 sem interrupções!**
"""
                    
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
    """Processa mensagens não-comando"""
    await update.message.reply_text(
        "🤖 **Olá!**\n\n"
        "Use /start para ver os comandos disponíveis.\n\n"
        "**🔗 Acesse:** https://nexocrypto.app\n\n"
        "**🔄 Bot Keep-Alive - Sempre Disponível**"
    )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Trata erros do bot"""
    logger.error(f"Erro: {context.error}")

def run_flask():
    """Executa o servidor Flask em thread separada"""
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)

def main():
    """Função principal com keep-alive"""
    global start_time
    start_time = time.time()
    
    try:
        logger.info("🚀 Iniciando NexoCrypto Bot Keep-Alive...")
        logger.info(f"🔗 Backend: {BACKEND_URL}")
        logger.info(f"🌐 Port: {PORT}")
        
        # Inicia servidor Flask em thread separada
        logger.info("🌐 Iniciando servidor Flask para keep-alive...")
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
        
        # Aguarda Flask inicializar
        time.sleep(3)
        
        # Inicia serviço de keep-alive em thread separada
        logger.info("🔄 Iniciando serviço keep-alive...")
        keepalive_thread = threading.Thread(target=keep_alive_service, daemon=True)
        keepalive_thread.start()
        
        # FORÇA LIMPEZA DO WEBHOOK
        logger.info("🔄 Executando force takeover...")
        force_webhook_cleanup()
        
        # Cria aplicação Telegram
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Adiciona handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("validate", validate))
        application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Handler de erros
        application.add_error_handler(error_handler)
        
        logger.info("✅ Bot configurado com keep-alive!")
        logger.info("🔄 Sistema anti-sleep ativo!")
        
        # Inicia o bot
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES,
            poll_interval=1.0,
            timeout=20
        )
        
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        # Auto-restart em caso de erro
        logger.info("🔄 Tentando reiniciar após erro...")
        time.sleep(30)
        main()

if __name__ == '__main__':
    main()

