#!/usr/bin/env python3
"""
NexoCrypto Telegram Bot - ULTRA ROBUST VERSION
Versão ultra robusta com máxima estabilidade para Render
"""

import os
import sys
import time
import signal
import logging
import asyncio
import threading
from datetime import datetime
from flask import Flask, jsonify
import requests
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Configuração de logging ultra robusta
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot_ultra.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

# Configurações
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8287801389:AAGwcmDKhBLh1bJvGHFvKDiRBpxgnw23Kik')
BACKEND_URL = os.environ.get('BACKEND_URL', 'https://nexocrypto-backend.onrender.com')
PORT = int(os.environ.get('PORT', 10000))

# Flask app para keep-alive
app = Flask(__name__)

# Estado global
bot_running = False
application = None

@app.route('/')
def health_check():
    """Health check endpoint"""
    global bot_running
    return jsonify({
        'status': 'healthy' if bot_running else 'starting',
        'bot_running': bot_running,
        'timestamp': datetime.now().isoformat(),
        'service': 'nexocrypto-telegram-bot-ultra'
    })

@app.route('/ping')
def ping():
    """Ping endpoint para keep-alive"""
    return jsonify({'status': 'pong', 'timestamp': datetime.now().isoformat()})

@app.route('/status')
def status():
    """Status detalhado"""
    global bot_running, application
    return jsonify({
        'bot_running': bot_running,
        'application_status': 'running' if application else 'not_initialized',
        'backend_url': BACKEND_URL,
        'timestamp': datetime.now().isoformat(),
        'uptime': time.time()
    })

class UltraRobustBot:
    def __init__(self):
        self.application = None
        self.running = False
        self.restart_count = 0
        self.max_restarts = 10
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start"""
        try:
            user = update.effective_user
            logger.info(f"Comando /start recebido de {user.username or user.first_name}")
            
            welcome_message = f"""🚀 **Bem-vindo ao NexoCrypto Trading Bot!**

Olá {user.first_name}! 👋

🎯 **Para conectar seus grupos do Telegram:**

1️⃣ Acesse: https://nexocrypto.app
2️⃣ Faça login na plataforma
3️⃣ Vá para a aba "Auto Trading"
4️⃣ Clique em "Conectar Grupos Reais"
5️⃣ Use o comando /validate no bot

📊 **Funcionalidades disponíveis:**
✅ Monitoramento de sinais em tempo real
✅ Auto trading automatizado
✅ Análise de performance
✅ Alertas personalizados

🔗 **Links úteis:**
• Website: https://nexocrypto.app
• Suporte: @nexocrypto_support

Digite /validate para começar a validação! 🎉"""

            await update.message.reply_text(welcome_message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Erro no comando /start: {e}")
            await update.message.reply_text("❌ Erro interno. Tente novamente em alguns segundos.")

    async def validate_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /validate"""
        try:
            user = update.effective_user
            logger.info(f"Comando /validate recebido de {user.username or user.first_name}")
            
            # Solicita compartilhamento de contato
            keyboard = [[KeyboardButton("📱 Compartilhar Contato", request_contact=True)]]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            
            validate_message = """🔐 **Validação de Conta NexoCrypto**

Para conectar seus grupos do Telegram ao NexoCrypto, precisamos validar sua identidade.

👆 **Clique no botão abaixo** para compartilhar seu contato e validar sua conta:"""

            await update.message.reply_text(validate_message, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Erro no comando /validate: {e}")
            await update.message.reply_text("❌ Erro na validação. Tente novamente.")

    async def handle_contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa compartilhamento de contato"""
        try:
            user = update.effective_user
            contact = update.message.contact
            
            if contact.user_id != user.id:
                await update.message.reply_text("❌ Por favor, compartilhe seu próprio contato.")
                return
            
            logger.info(f"Contato recebido de {user.username or user.first_name}: {contact.phone_number}")
            
            # Envia dados para o backend
            try:
                response = requests.post(f"{BACKEND_URL}/api/telegram/validate-user", 
                    json={
                        'user_id': user.id,
                        'username': user.username,
                        'first_name': user.first_name,
                        'phone_number': contact.phone_number
                    }, 
                    timeout=10
                )
                
                if response.status_code == 200:
                    success_message = """✅ **Validação Concluída com Sucesso!**

📋 **PRÓXIMO PASSO IMPORTANTE:**
🔄 Volte para o NexoCrypto e clique no botão "Verificar Validação" 
para completar a conexão e carregar seus grupos do Telegram!

⚠️ Sem este passo, seus grupos não aparecerão na plataforma.

🌐 Acesse: https://nexocrypto.app"""
                    
                    await update.message.reply_text(success_message, parse_mode='Markdown')
                else:
                    await update.message.reply_text("⚠️ Erro na validação. Tente novamente mais tarde.")
                    
            except requests.RequestException as e:
                logger.error(f"Erro ao enviar dados para backend: {e}")
                await update.message.reply_text("⚠️ Erro de conexão. Tente novamente em alguns minutos.")
                
        except Exception as e:
            logger.error(f"Erro ao processar contato: {e}")
            await update.message.reply_text("❌ Erro ao processar contato. Tente novamente.")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa mensagens gerais"""
        try:
            user = update.effective_user
            text = update.message.text
            
            logger.info(f"Mensagem recebida de {user.username or user.first_name}: {text}")
            
            help_message = """🤖 **NexoCrypto Trading Bot**

📋 **Comandos disponíveis:**
• /start - Iniciar bot e ver instruções
• /validate - Validar conta para conectar grupos

🔗 **Para usar o sistema completo:**
1. Acesse https://nexocrypto.app
2. Use /validate aqui no bot
3. Complete a validação na plataforma

💡 **Precisa de ajuda?** Entre em contato com @nexocrypto_support"""

            await update.message.reply_text(help_message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {e}")

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Manipulador de erros global"""
        logger.error(f"Erro no bot: {context.error}")
        
        if update and hasattr(update, 'message') and update.message:
            try:
                await update.message.reply_text("❌ Erro interno. Tente novamente em alguns segundos.")
            except:
                pass

    async def setup_application(self):
        """Configura a aplicação do bot"""
        try:
            # Cria aplicação
            self.application = Application.builder().token(BOT_TOKEN).build()
            
            # Adiciona handlers
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(CommandHandler("validate", self.validate_command))
            self.application.add_handler(MessageHandler(filters.CONTACT, self.handle_contact))
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
            
            # Handler de erro
            self.application.add_error_handler(self.error_handler)
            
            logger.info("✅ Aplicação do bot configurada com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao configurar aplicação: {e}")
            return False

    async def start_bot(self):
        """Inicia o bot com máxima robustez"""
        global bot_running, application
        
        while self.restart_count < self.max_restarts:
            try:
                logger.info(f"🚀 Iniciando bot (tentativa {self.restart_count + 1}/{self.max_restarts})")
                
                # Configura aplicação
                if not await self.setup_application():
                    raise Exception("Falha na configuração da aplicação")
                
                application = self.application
                
                # Inicia polling
                await self.application.initialize()
                await self.application.start()
                
                bot_running = True
                self.running = True
                
                logger.info("✅ NexoCrypto Bot iniciado com sucesso!")
                logger.info(f"🔗 Backend: {BACKEND_URL}")
                
                # Polling loop ultra robusto
                while self.running:
                    try:
                        await self.application.updater.start_polling(
                            poll_interval=1.0,
                            timeout=30,
                            read_timeout=30,
                            write_timeout=30,
                            connect_timeout=30,
                            pool_timeout=30
                        )
                        
                        # Mantém o bot rodando
                        while self.running:
                            await asyncio.sleep(1)
                            
                    except Exception as e:
                        logger.error(f"❌ Erro no polling: {e}")
                        await asyncio.sleep(5)
                        continue
                        
            except Exception as e:
                logger.error(f"❌ Erro crítico no bot: {e}")
                self.restart_count += 1
                bot_running = False
                
                if self.restart_count < self.max_restarts:
                    wait_time = min(30, 5 * self.restart_count)
                    logger.info(f"🔄 Reiniciando em {wait_time} segundos...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("❌ Máximo de reinicializações atingido")
                    break
                    
            finally:
                if self.application:
                    try:
                        await self.application.stop()
                        await self.application.shutdown()
                    except:
                        pass

    def stop_bot(self):
        """Para o bot graciosamente"""
        logger.info("🛑 Parando bot...")
        self.running = False

def keep_alive_service():
    """Serviço keep-alive em thread separada"""
    def ping_self():
        while True:
            try:
                time.sleep(600)  # 10 minutos
                requests.get(f"http://localhost:{PORT}/ping", timeout=5)
                logger.info("🔄 Self-ping realizado")
            except Exception as e:
                logger.error(f"❌ Erro no self-ping: {e}")
    
    ping_thread = threading.Thread(target=ping_self, daemon=True)
    ping_thread.start()
    logger.info("✅ Serviço keep-alive iniciado")

def signal_handler(signum, frame):
    """Manipulador de sinais do sistema"""
    logger.info(f"🛑 Sinal {signum} recebido, parando bot...")
    if 'bot' in globals():
        bot.stop_bot()
    sys.exit(0)

def run_flask():
    """Executa Flask em thread separada"""
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)

async def main():
    """Função principal ultra robusta"""
    global bot
    
    logger.info("🚀 Iniciando NexoCrypto Bot Ultra Robust...")
    
    # Configura manipuladores de sinal
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Inicia Flask em thread separada
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info(f"✅ Servidor Flask iniciado na porta {PORT}")
    
    # Inicia serviço keep-alive
    keep_alive_service()
    
    # Aguarda Flask inicializar
    await asyncio.sleep(2)
    
    # Cria e inicia bot
    bot = UltraRobustBot()
    await bot.start_bot()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot interrompido pelo usuário")
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        sys.exit(1)

