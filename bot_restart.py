#!/usr/bin/env python3
"""
Bot Telegram NexoCrypto - Versão com Retry Logic
Versão especial para lidar com conflitos de instância
"""

import logging
import asyncio
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import requests

# Configuração de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configurações
BOT_TOKEN = "8287801389:AAGwcmDKhBLh1bJvGHFvKDiRBpxgnw23Kik"
BACKEND_URL = "https://nexocrypto-backend.onrender.com"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    welcome_message = """
🚀 **Bem-vindo ao NexoCrypto Trading Bot!**

🔗 **Acesse nossa plataforma:** https://nexocrypto.app

📊 **Funcionalidades:**
• Validação de usuários
• Monitoramento de sinais
• Auto Trading (em breve)

💡 **Como usar:**
1. Acesse https://nexocrypto.app
2. Faça login/cadastro
3. Conecte seu Telegram
4. Configure seus grupos de sinais

🆘 **Suporte:** @nexocrypto_support
    """
    
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

async def validate(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    # Dados do usuário
    user_data = {
        'uuid': uuid_code,
        'telegram_id': user.id,
        'username': user.username or '',
        'first_name': user.first_name or '',
        'last_name': user.last_name or ''
    }
    
    try:
        # Envia validação para o backend
        response = requests.post(
            f"{BACKEND_URL}/api/telegram/validate",
            json=user_data,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                await update.message.reply_text(
                    f"✅ **Validação realizada com sucesso!**\n\n"
                    f"👤 **Usuário:** {user.first_name}\n"
                    f"🆔 **UUID:** `{uuid_code}`\n"
                    f"📱 **Telegram:** @{user.username or 'N/A'}\n\n"
                    f"🎉 **Agora você pode usar todas as funcionalidades da plataforma!**",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    f"❌ **Erro na validação:** {data.get('error', 'Erro desconhecido')}"
                )
        else:
            await update.message.reply_text(
                "❌ **Erro de comunicação com o servidor.**\n\n"
                "🔄 **Tente novamente em alguns minutos.**"
            )
            
    except Exception as e:
        logger.error(f"Erro na validação: {e}")
        await update.message.reply_text(
            "❌ **Erro interno do bot.**\n\n"
            "🔄 **Tente novamente em alguns minutos.**"
        )

async def main():
    """Função principal com retry logic"""
    max_retries = 5
    retry_delay = 30  # 30 segundos entre tentativas
    
    for attempt in range(max_retries):
        try:
            logger.info(f"🤖 Tentativa {attempt + 1}/{max_retries} - Iniciando NexoCrypto Bot...")
            logger.info(f"🔗 Backend: {BACKEND_URL}")
            
            # Força limpeza do webhook
            requests.post(f'https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook', 
                         json={'drop_pending_updates': True})
            
            # Aguarda um pouco antes de iniciar
            await asyncio.sleep(5)
            
            # Cria aplicação
            application = Application.builder().token(BOT_TOKEN).build()
            
            # Adiciona handlers
            application.add_handler(CommandHandler("start", start))
            application.add_handler(CommandHandler("validate", validate))
            
            # Inicia o bot
            await application.run_polling(
                drop_pending_updates=True,
                allowed_updates=Update.ALL_TYPES
            )
            
            # Se chegou aqui, o bot rodou com sucesso
            break
            
        except Exception as e:
            logger.error(f"❌ Erro na tentativa {attempt + 1}: {e}")
            
            if attempt < max_retries - 1:
                logger.info(f"⏳ Aguardando {retry_delay} segundos antes da próxima tentativa...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Aumenta o delay exponencialmente
            else:
                logger.error("❌ Todas as tentativas falharam. Bot não pôde ser iniciado.")
                break

if __name__ == '__main__':
    asyncio.run(main())

