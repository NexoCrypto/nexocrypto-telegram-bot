#!/usr/bin/env python3
"""
NexoCrypto Telegram Bot - Force Takeover Version
Versão que força a tomada de controle eliminando instâncias conflitantes
"""

import os
import logging
import asyncio
import requests
import time
from datetime import datetime
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

def force_webhook_cleanup():
    """Força limpeza completa do webhook para eliminar conflitos"""
    try:
        logger.info("🔄 Iniciando force takeover do webhook...")
        
        # Múltiplas tentativas agressivas de limpeza
        for attempt in range(10):
            logger.info(f"🔄 Tentativa {attempt + 1}/10 de force cleanup...")
            
            try:
                # Delete webhook com drop_pending_updates
                response = requests.post(
                    f'https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook',
                    json={'drop_pending_updates': True},
                    timeout=5
                )
                logger.info(f"Delete webhook: {response.json()}")
                
                # Set webhook vazio para forçar reset
                response = requests.post(
                    f'https://api.telegram.org/bot{BOT_TOKEN}/setWebhook',
                    json={'url': ''},
                    timeout=5
                )
                logger.info(f"Set empty webhook: {response.json()}")
                
                # Aguarda entre tentativas
                time.sleep(2)
                
            except Exception as e:
                logger.warning(f"Erro na tentativa {attempt + 1}: {e}")
                continue
        
        # Aguarda estabilização
        logger.info("⏳ Aguardando estabilização...")
        time.sleep(10)
        
        # Verifica status final
        try:
            response = requests.get(
                f'https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo',
                timeout=5
            )
            webhook_info = response.json()
            logger.info(f"✅ Webhook final: {webhook_info}")
            
        except Exception as e:
            logger.warning(f"Erro ao verificar webhook: {e}")
        
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

**🚀 Bot Force Takeover - Versão Definitiva**
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

**🚀 Bot Force Takeover - Funcionando Perfeitamente!**
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
        "**🚀 Bot Force Takeover Ativo**"
    )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Trata erros do bot"""
    logger.error(f"Erro: {context.error}")

def main():
    """Função principal com force takeover"""
    try:
        logger.info("🚀 Iniciando NexoCrypto Bot Force Takeover...")
        logger.info(f"🔗 Backend: {BACKEND_URL}")
        
        # FORÇA LIMPEZA DO WEBHOOK
        logger.info("🔄 Executando force takeover...")
        if not force_webhook_cleanup():
            logger.warning("⚠️ Force takeover falhou, mas continuando...")
        
        # Aguarda estabilização adicional
        logger.info("⏳ Aguardando estabilização final...")
        time.sleep(5)
        
        # Cria aplicação com configurações otimizadas
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Adiciona handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("validate", validate))
        application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Handler de erros
        application.add_error_handler(error_handler)
        
        logger.info("✅ Bot configurado com force takeover!")
        
        # Inicia o bot com configurações agressivas
        logger.info("🎯 Iniciando polling com force takeover...")
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES,
            poll_interval=1.0,
            timeout=20,
            read_timeout=30,
            write_timeout=30,
            connect_timeout=30,
            pool_timeout=30
        )
        
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        # Tenta novamente após erro
        logger.info("🔄 Tentando reiniciar após erro...")
        time.sleep(10)
        main()

if __name__ == '__main__':
    main()

