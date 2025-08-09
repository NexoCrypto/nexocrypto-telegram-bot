#!/usr/bin/env python3
"""
NexoCrypto Telegram Bot - Versão Atualizada
Bot oficial para captura e processamento de sinais de trading
"""

import os
import re
import json
import logging
import requests
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from signal_parser import SignalParser

# Configuração de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configurações
BOT_TOKEN = "8287801389:AAGwcmDKhBLh1bJvGHFvKDiRBpxgnw23Kik"
API_BASE_URL = "http://localhost:5002/api"

class NexoCryptoBot:
    def __init__(self):
        self.parser = SignalParser()
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Configura handlers do bot"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("validate", self.validate_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("groups", self.groups_command))
        
        # Handler para mensagens em grupos
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_message)
        )
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start"""
        user = update.effective_user
        
        welcome_message = f"""
🤖 **Bem-vindo ao NexoCrypto Trading Bot!**

Olá {user.first_name}! 👋

Este bot captura e processa sinais de trading automaticamente para o sistema NexoCrypto.

**📋 Comandos disponíveis:**
• `/validate UUID` - Validar sua conta
• `/help` - Ajuda completa
• `/status` - Status da conexão
• `/groups` - Grupos conectados

**🔐 Para começar:**
1. Gere seu UUID no painel NexoCrypto
2. Use `/validate SEU_UUID` aqui
3. Adicione este bot aos seus grupos de sinais
4. Pronto! Os sinais serão processados automaticamente

**🚀 Sistema NexoCrypto:** nexocrypto.app
        """
        
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def validate_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /validate UUID"""
        if not context.args:
            await update.message.reply_text(
                "❌ **Uso incorreto!**\n\n"
                "Use: `/validate SEU_UUID`\n\n"
                "Exemplo: `/validate CRP-ABC123DE-F4G5-H6I7`",
                parse_mode='Markdown'
            )
            return
        
        uuid_code = context.args[0]
        user = update.effective_user
        
        # Valida formato do UUID
        if not re.match(r'^CRP-[A-Z0-9]{8}-[A-Z0-9]{4}-[A-Z0-9]{4}$', uuid_code):
            await update.message.reply_text(
                "❌ **UUID inválido!**\n\n"
                "O UUID deve ter o formato: `CRP-XXXXXXXX-XXXX-XXXX`",
                parse_mode='Markdown'
            )
            return
        
        try:
            # Chama API para validar usuário
            response = requests.post(f"{API_BASE_URL}/validate-user", json={
                'uuid': uuid_code,
                'telegram_id': user.id,
                'username': user.username or user.first_name
            })
            
            if response.status_code == 200:
                await update.message.reply_text(
                    f"✅ **Validação realizada com sucesso!**\n\n"
                    f"🔗 **UUID:** `{uuid_code}`\n"
                    f"👤 **Usuário:** {user.first_name}\n"
                    f"🤖 **Bot:** Conectado\n\n"
                    f"Agora você pode adicionar este bot aos seus grupos de sinais!",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    "❌ **Erro na validação!**\n\n"
                    "UUID não encontrado ou já validado.\n"
                    "Gere um novo UUID no painel NexoCrypto.",
                    parse_mode='Markdown'
                )
        except Exception as e:
            logger.error(f"Erro na validação: {e}")
            await update.message.reply_text(
                "❌ **Erro interno!**\n\n"
                "Tente novamente em alguns minutos.",
                parse_mode='Markdown'
            )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /help"""
        help_message = """
🤖 **NexoCrypto Trading Bot - Ajuda**

**📋 Comandos:**
• `/start` - Iniciar bot e instruções
• `/validate UUID` - Validar sua conta
• `/help` - Esta mensagem de ajuda
• `/status` - Status da conexão
• `/groups` - Listar grupos conectados

**🔧 Como usar:**

**1. Validação:**
- Acesse nexocrypto.app
- Vá em Auto Trading → Validação Telegram
- Copie seu UUID
- Use `/validate SEU_UUID` aqui

**2. Adicionar aos grupos:**
- Adicione @nexocrypto_trading_bot aos grupos
- Dê permissão de administrador
- Os sinais serão processados automaticamente

**3. Formatos de sinal suportados:**
- `BTCUSDT LONG Entry: 45000`
- `ETH/USDT SHORT 3500-3520`
- `SOL LONG x10 Entry 150 SL 145 TP 160`

**🚀 Sistema:** nexocrypto.app
**📧 Suporte:** admin@nexocrypto.app
        """
        
        await update.message.reply_text(help_message, parse_mode='Markdown')
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /status"""
        try:
            # Verifica status da API
            response = requests.get(f"{API_BASE_URL.replace('/api', '')}/health")
            api_status = "🟢 ONLINE" if response.status_code == 200 else "🔴 OFFLINE"
        except:
            api_status = "🔴 OFFLINE"
        
        status_message = f"""
📊 **Status do Sistema NexoCrypto**

🤖 **Bot Telegram:** 🟢 ONLINE
⚡ **API Backend:** {api_status}
🌐 **Sistema Web:** nexocrypto.app

**📈 Estatísticas:**
• Grupos monitorados: Em tempo real
• Sinais processados: Automático
• Precisão IA: 91%+

**⏰ Última verificação:** {datetime.now().strftime('%d/%m/%Y %H:%M')}
        """
        
        await update.message.reply_text(status_message, parse_mode='Markdown')
    
    async def groups_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /groups"""
        user = update.effective_user
        
        groups_message = f"""
📱 **Grupos Conectados**

👤 **Usuário:** {user.first_name}
🤖 **Bot:** @nexocrypto_trading_bot

**Para adicionar grupos:**
1. Adicione este bot ao grupo
2. Dê permissão de administrador
3. Os grupos aparecerão automaticamente no painel

**🌐 Painel:** nexocrypto.app → Auto Trading
        """
        
        await update.message.reply_text(groups_message, parse_mode='Markdown')
    
    async def process_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa mensagens em grupos"""
        message = update.message
        
        # Só processa mensagens de grupos
        if message.chat.type not in ['group', 'supergroup']:
            return
        
        text = message.text
        if not text:
            return
        
        # Tenta fazer parse do sinal
        signal = self.parser.parse_signal(text)
        
        if signal:
            logger.info(f"Sinal detectado no grupo {message.chat.title}: {signal['symbol']} {signal['direction']}")
            
            try:
                # Envia sinal para API
                response = requests.post(f"{API_BASE_URL}/process-signal", json={
                    'group_id': message.chat.id,
                    'symbol': signal['symbol'],
                    'direction': signal['direction'],
                    'entry_price': signal.get('entry_price'),
                    'stop_loss': signal.get('stop_loss'),
                    'take_profit_1': signal.get('take_profit_1'),
                    'take_profit_2': signal.get('take_profit_2'),
                    'take_profit_3': signal.get('take_profit_3'),
                    'leverage': signal.get('leverage', 1),
                    'confidence_score': signal.get('confidence_score', 0.75),
                    'raw_message': text
                })
                
                if response.status_code == 200:
                    logger.info(f"Sinal processado com sucesso: {signal['symbol']}")
                else:
                    logger.error(f"Erro ao processar sinal: {response.text}")
                    
            except Exception as e:
                logger.error(f"Erro ao enviar sinal para API: {e}")
    
    def run(self):
        """Inicia o bot"""
        logger.info("🤖 Iniciando NexoCrypto Bot...")
        self.application.run_polling()

if __name__ == '__main__':
    bot = NexoCryptoBot()
    bot.run()

