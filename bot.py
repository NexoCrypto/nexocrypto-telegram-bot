import os
import asyncio
import logging
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from config import Config
from models import create_database, get_session, User, TelegramGroup, ValidationToken, generate_uuid
from signal_parser import SignalParser
import requests

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class NexoCryptoBot:
    def __init__(self):
        self.config = Config()
        self.parser = SignalParser()
        self.engine = create_database(self.config.DATABASE_URL)
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        chat = update.effective_chat
        
        # Save user to database
        session = get_session(self.engine)
        try:
            db_user = session.query(User).filter_by(telegram_id=str(user.id)).first()
            if not db_user:
                db_user = User(
                    telegram_id=str(user.id),
                    username=user.username or user.first_name,
                    uuid_token=generate_uuid()
                )
                session.add(db_user)
                session.commit()
            
            welcome_message = f"""
🤖 **Bem-vindo ao NexoCrypto Trading Bot!**

Olá {user.first_name}! 👋

**Seu UUID de validação:**
`{db_user.uuid_token}`

**Para conectar seus grupos:**
1. Acesse nexocrypto.app
2. Vá para aba "Auto Trading"
3. Cole seu UUID na validação
4. Adicione este bot aos seus grupos de sinais

**Comandos disponíveis:**
/validate - Validar sua conta
/help - Ajuda completa
/status - Status da conexão
/groups - Grupos conectados

**Grupos suportados:**
• Binance Killers
• ByBit Pro  
• Raven Pro
• Tasso
• E outros grupos de sinais

🔒 **Seguro e Confiável**
Seus dados estão protegidos e apenas você tem acesso aos seus sinais.
            """
            
            await update.message.reply_text(welcome_message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in start_command: {e}")
            await update.message.reply_text("❌ Erro interno. Tente novamente.")
        finally:
            session.close()
    
    async def validate_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /validate command"""
        user = update.effective_user
        
        if not context.args:
            await update.message.reply_text(
                "❌ **Uso correto:**\n`/validate SEU_UUID`\n\n"
                "Obtenha seu UUID em nexocrypto.app na aba Auto Trading.",
                parse_mode='Markdown'
            )
            return
        
        provided_uuid = context.args[0]
        
        session = get_session(self.engine)
        try:
            # Find user by UUID
            db_user = session.query(User).filter_by(uuid_token=provided_uuid).first()
            
            if not db_user:
                await update.message.reply_text("❌ UUID inválido ou não encontrado.")
                return
            
            # Update user validation
            db_user.telegram_id = str(user.id)
            db_user.username = user.username or user.first_name
            db_user.is_validated = True
            db_user.last_activity = datetime.utcnow()
            session.commit()
            
            success_message = f"""
✅ **Validação Concluída!**

Parabéns {user.first_name}! Sua conta foi validada com sucesso.

**Status:** ✅ Validado
**UUID:** `{provided_uuid}`
**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}

**Próximos passos:**
1. Adicione este bot aos seus grupos de sinais
2. Configure o Auto Trading em nexocrypto.app
3. Monitore seus sinais em tempo real

🚀 **Sistema ativo e funcionando!**
            """
            
            await update.message.reply_text(success_message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in validate_command: {e}")
            await update.message.reply_text("❌ Erro na validação. Tente novamente.")
        finally:
            session.close()
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
🤖 **NexoCrypto Trading Bot - Ajuda**

**Comandos Principais:**
• `/start` - Iniciar bot e obter UUID
• `/validate UUID` - Validar sua conta
• `/status` - Ver status da conexão
• `/groups` - Listar grupos conectados
• `/help` - Esta mensagem de ajuda

**Como Usar:**
1. **Obter UUID:** Use /start para receber seu UUID único
2. **Validar:** Acesse nexocrypto.app e valide sua conta
3. **Conectar:** Adicione o bot aos grupos de sinais
4. **Monitorar:** Acompanhe sinais em tempo real

**Grupos Suportados:**
• Binance Killers
• ByBit Pro
• Raven Pro  
• Tasso
• Outros grupos de trading

**Formatos de Sinais Reconhecidos:**
• BTCUSDT LONG Entry: 45000 SL: 44000 TP: 46000
• #ETH BUY @ 3000 Stop: 2900 Target: 3200
• SOLUSDT SHORT 150 SL 155 TP1 145 TP2 140

**Suporte:**
Para dúvidas, acesse nexocrypto.app ou contate o suporte.

🔒 **Seguro • Confiável • Automático**
        """
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        user = update.effective_user
        
        session = get_session(self.engine)
        try:
            db_user = session.query(User).filter_by(telegram_id=str(user.id)).first()
            
            if not db_user:
                await update.message.reply_text("❌ Usuário não encontrado. Use /start primeiro.")
                return
            
            # Count connected groups
            groups_count = session.query(TelegramGroup).filter_by(
                user_id=db_user.id, 
                is_active=True
            ).count()
            
            status_message = f"""
📊 **Status da Conexão**

**Usuário:** {db_user.username}
**Status:** {'✅ Validado' if db_user.is_validated else '❌ Não Validado'}
**UUID:** `{db_user.uuid_token}`
**Grupos Conectados:** {groups_count}
**Última Atividade:** {db_user.last_activity.strftime('%d/%m/%Y %H:%M')}

**Sistema:** 🟢 Online
**API:** 🟢 Funcionando
**Parser:** 🟢 Ativo

{'🚀 Tudo funcionando perfeitamente!' if db_user.is_validated else '⚠️ Complete a validação em nexocrypto.app'}
            """
            
            await update.message.reply_text(status_message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in status_command: {e}")
            await update.message.reply_text("❌ Erro ao verificar status.")
        finally:
            session.close()
    
    async def groups_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /groups command"""
        user = update.effective_user
        
        session = get_session(self.engine)
        try:
            db_user = session.query(User).filter_by(telegram_id=str(user.id)).first()
            
            if not db_user:
                await update.message.reply_text("❌ Usuário não encontrado. Use /start primeiro.")
                return
            
            groups = session.query(TelegramGroup).filter_by(
                user_id=db_user.id,
                is_active=True
            ).all()
            
            if not groups:
                await update.message.reply_text(
                    "📭 **Nenhum grupo conectado**\n\n"
                    "Para conectar grupos:\n"
                    "1. Adicione este bot aos grupos de sinais\n"
                    "2. Configure em nexocrypto.app\n"
                    "3. Valide sua conta"
                )
                return
            
            groups_text = "📱 **Grupos Conectados:**\n\n"
            for group in groups:
                status = "✅" if group.is_validated else "⏳"
                groups_text += f"{status} **{group.group_name}**\n"
                groups_text += f"   Tipo: {group.group_type}\n"
                groups_text += f"   Adicionado: {group.added_at.strftime('%d/%m/%Y')}\n\n"
            
            await update.message.reply_text(groups_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in groups_command: {e}")
            await update.message.reply_text("❌ Erro ao listar grupos.")
        finally:
            session.close()
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages from groups"""
        message = update.message
        chat = update.effective_chat
        
        # Only process group messages
        if chat.type not in ['group', 'supergroup']:
            return
        
        # Try to parse as trading signal
        signal_data = self.parser.parse_signal(message.text, 'generic')
        
        if signal_data:
            # Process valid signal
            await self.process_signal(signal_data, chat, message)
    
    async def process_signal(self, signal_data, chat, message):
        """Process a valid trading signal"""
        try:
            # Send to NexoCrypto API
            api_url = f"{self.config.API_BASE_URL}/api/signals"
            
            payload = {
                'symbol': signal_data['symbol'],
                'direction': signal_data['direction'],
                'entry_price': signal_data['entry_price'],
                'stop_loss': signal_data['stop_loss'],
                'take_profits': signal_data['take_profits'],
                'leverage': signal_data['leverage'],
                'group_id': str(chat.id),
                'group_name': chat.title,
                'original_message': signal_data['original_message'],
                'confidence_score': 0.8,  # Default confidence
                'source': 'telegram_bot'
            }
            
            response = requests.post(api_url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"Signal processed: {signal_data['symbol']} {signal_data['direction']}")
            else:
                logger.error(f"API error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error processing signal: {e}")
    
    def run(self):
        """Run the bot"""
        if not self.config.TELEGRAM_BOT_TOKEN:
            logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
            return
        
        # Create application
        application = Application.builder().token(self.config.TELEGRAM_BOT_TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("validate", self.validate_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("status", self.status_command))
        application.add_handler(CommandHandler("groups", self.groups_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Start bot
        logger.info("NexoCrypto Bot starting...")
        application.run_polling()

if __name__ == '__main__':
    bot = NexoCryptoBot()
    bot.run()

