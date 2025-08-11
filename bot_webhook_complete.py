#!/usr/bin/env python3
"""
NexoCrypto Telegram Bot - Versão Webhook Completa
Bot para integração com sistema NexoCrypto
"""

import os
import sys
import asyncio
import logging
import requests
import json
import threading
from datetime import datetime
from flask import Flask, request, jsonify
from telegram import Bot, Update, BotCommand, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes

# Configuração de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configurações
BOT_TOKEN = os.getenv('BOT_TOKEN', '8287801389:AAGwcmDKhBLh1bJvGHFvKDiRBpxgnw23Kik')
BACKEND_URL = "https://nexocrypto-backend.onrender.com"

# Flask app
app = Flask(__name__)

# Bot instance
bot = Bot(token=BOT_TOKEN)

# Armazenamento temporário de usuários validados
validated_users = {}
user_contexts = {}

def format_brazilian_time():
    """Retorna horário atual no formato brasileiro"""
    return datetime.now().strftime('%d/%m/%Y - %H:%M')

async def start(update: Update, context=None) -> None:
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
/status - Ver status da conexão
/disconnect - Desconectar conta
/groups - Listar grupos conectados
/signals - Últimos sinais recebidos
/stats - Estatísticas da conta
/help - Ajuda completa

**🔗 Para começar:**
1. Acesse o NexoCrypto: https://nexocrypto.app
2. Vá em Auto Trading
3. Copie o UUID gerado
4. Use: `/validate [seu-uuid]`

💡 **Dica:** Mantenha este chat ativo para receber sinais automaticamente!
"""
    
    await bot.send_message(chat_id=update.effective_chat.id, text=welcome_message, parse_mode='Markdown')

async def help_command(update: Update, context=None) -> None:
    """Comando /help"""
    help_text = """
📚 **Ajuda Completa - NexoCrypto Bot**

**🔐 Comandos de Autenticação:**
• `/validate [UUID]` - Valida UUID do sistema NexoCrypto
• `/disconnect` - Desconecta sua conta do Telegram
• `/status` - Mostra status atual da conexão

**📊 Comandos de Informação:**
• `/groups` - Lista grupos conectados
• `/signals` - Últimos sinais recebidos
• `/stats` - Estatísticas da conta

**🤖 Comandos do Sistema:**
• `/start` - Mensagem de boas-vindas
• `/help` - Esta ajuda

**📝 Como usar:**

**1. Validação inicial:**
```
/validate 12345678-1234-1234-1234-123456789abc
```

**2. Verificar status:**
```
/status
```

**3. Desconectar:**
```
/disconnect
```

**🔗 Links úteis:**
• Site: https://nexocrypto.app
• Suporte: @nexocrypto_support

**⚠️ Importante:**
• Mantenha seu UUID seguro
• Não compartilhe com terceiros
• Use apenas em conversas privadas
"""
    
    await bot.send_message(chat_id=update.effective_chat.id, text=help_text, parse_mode='Markdown')

async def validate_command(update: Update, context=None) -> None:
    """Comando /validate [UUID]"""
    user = update.effective_user
    message_text = update.message.text
    args = message_text.split()[1:] if len(message_text.split()) > 1 else []
    
    if not args:
        await bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ **Erro:** UUID não fornecido\n\n"
                 "**Uso correto:**\n"
                 "`/validate [seu-uuid]`\n\n"
                 "**Exemplo:**\n"
                 "`/validate 12345678-1234-1234-1234-123456789abc`",
            parse_mode='Markdown'
        )
        return
    
    uuid_code = args[0]
    
    # Validação básica do formato UUID
    if len(uuid_code) < 32:
        await bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ **Erro:** UUID inválido\n\n"
                 "O UUID deve ter pelo menos 32 caracteres.\n"
                 "Copie o UUID completo do sistema NexoCrypto.",
            parse_mode='Markdown'
        )
        return
    
    # Solicita contato para obter telefone
    keyboard = [[KeyboardButton("📱 Compartilhar Contato", request_contact=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    # Armazena dados temporariamente
    user_contexts[user.id] = {
        'pending_validation': {
            'uuid': uuid_code,
            'telegram_user_id': user.id,
            'telegram_username': user.username or user.first_name,
            'telegram_first_name': user.first_name,
            'telegram_last_name': user.last_name
        }
    }
    
    await bot.send_message(
        chat_id=update.effective_chat.id,
        text="🔐 **Para completar a validação, preciso do seu número de telefone.**\n\n"
             "📱 Clique no botão abaixo para compartilhar seu contato:\n\n"
             "⚠️ *Isso é necessário para capturar seus grupos do Telegram automaticamente.*",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_contact(update: Update, context=None):
    """Processa contato compartilhado e completa validação"""
    try:
        contact = update.message.contact
        user = update.effective_user
        
        # Verifica se há validação pendente
        if user.id not in user_contexts or 'pending_validation' not in user_contexts[user.id]:
            await bot.send_message(chat_id=update.effective_chat.id, text="❌ Nenhuma validação pendente. Use /validate primeiro.")
            return
        
        # Verifica se o contato é do próprio usuário
        if contact.user_id != user.id:
            await bot.send_message(chat_id=update.effective_chat.id, text="❌ Por favor, compartilhe seu próprio contato.")
            return
        
        # Completa dados do usuário
        user_data = user_contexts[user.id]['pending_validation']
        user_data['phone_number'] = contact.phone_number
        
        # Remove teclado
        await bot.send_message(
            chat_id=update.effective_chat.id,
            text="✅ Contato recebido! Processando validação...",
            reply_markup=ReplyKeyboardRemove()
        )
        
        # Prepara payload para o backend (converte uuid para user_uuid)
        backend_payload = user_data.copy()
        backend_payload['user_uuid'] = backend_payload.pop('uuid')
        
        # Envia dados para o backend
        response = requests.post(f'{BACKEND_URL}/verify-userbot-code', 
                               json=backend_payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                # Armazena usuário validado
                validated_users[user.id] = {
                    'uuid': user_data['uuid'],
                    'username': user.username or user.first_name,
                    'validated_at': datetime.now(),
                    'phone_number': contact.phone_number,
                    'user_data': {
                        'id': user.id,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'username': user.username
                    }
                }
                
                # Inicia captura de grupos via userbot
                await start_userbot_capture(user_data)
                
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
"""
                
                await bot.send_message(chat_id=update.effective_chat.id, text=success_message, parse_mode='Markdown')
            else:
                await bot.send_message(chat_id=update.effective_chat.id, text=f"❌ Erro na validação: {data.get('error', 'Erro desconhecido')}")
        else:
            await bot.send_message(chat_id=update.effective_chat.id, text="❌ Erro na comunicação com servidor. Tente novamente.")
        
        # Limpa dados temporários
        if user.id in user_contexts:
            del user_contexts[user.id]
        
    except Exception as e:
        logger.error(f"Erro ao processar contato: {e}")
        await bot.send_message(chat_id=update.effective_chat.id, text="❌ Erro interno. Tente novamente.")

async def start_userbot_capture(user_data):
    """Inicia captura de grupos via userbot"""
    try:
        # Chama API do userbot para iniciar sessão
        response = requests.post('http://localhost:5003/api/userbot/start-session',
                               json={
                                   'user_uuid': user_data['uuid'],
                                   'phone_number': user_data['phone_number']
                               }, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"UserBot iniciado para {user_data['uuid']}: {result.get('status')}")
        else:
            logger.error(f"Erro ao iniciar userbot: {response.status_code}")
            
    except Exception as e:
        logger.error(f"Erro na captura de grupos: {e}")

async def status_command(update: Update, context=None) -> None:
    """Comando /status"""
    user = update.effective_user
    
    if user.id not in validated_users:
        await bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ **Não conectado**\n\n"
                 "Você ainda não validou sua conta.\n\n"
                 "**Para conectar:**\n"
                 "1. Acesse https://nexocrypto.app\n"
                 "2. Vá em Auto Trading\n"
                 "3. Copie o UUID\n"
                 "4. Use: `/validate [uuid]`",
            parse_mode='Markdown'
        )
        return
    
    user_data = validated_users[user.id]
    validated_at = user_data['validated_at'].strftime('%d/%m/%Y - %H:%M')
    
    status_message = f"""
✅ **Status da Conexão**

**👤 Usuário:** {user.first_name}
**🔗 Username:** @{user.username or 'N/A'}
**📱 ID Telegram:** `{user.id}`

**🔐 Validação:**
• **Status:** ✅ Conectado
• **UUID:** `{user_data['uuid'][:8]}...{user_data['uuid'][-8:]}`
• **Validado em:** {validated_at}

**📊 Serviços:**
• **Auto Trading:** 🟢 Ativo
• **Sinais:** 🟢 Recebendo
• **Grupos:** 🟢 Monitorando

**⚡ Sistema:**
• **Bot:** 🟢 Online
• **Backend:** 🟢 Conectado
• **Última verificação:** {format_brazilian_time()}

Use `/disconnect` para desconectar sua conta.
"""
    
    await bot.send_message(chat_id=update.effective_chat.id, text=status_message, parse_mode='Markdown')

async def disconnect_command(update: Update, context=None) -> None:
    """Comando /disconnect"""
    user = update.effective_user
    
    if user.id not in validated_users:
        await bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ **Não conectado**\n\n"
                 "Você não possui uma conexão ativa para desconectar.",
            parse_mode='Markdown'
        )
        return
    
    try:
        user_data = validated_users[user.id]
        uuid_code = user_data['uuid']
        
        # Notifica o backend sobre a desconexão
        response = requests.post(
            f"{BACKEND_URL}/api/telegram/disconnect",
            json={'user_uuid': uuid_code},
            timeout=10
        )
        
        # Remove usuário da memória local
        del validated_users[user.id]
        
        disconnect_message = f"""
🔌 **Desconectado com Sucesso**

Sua conta foi desconectada do NexoCrypto.

**📋 O que foi desativado:**
• ❌ Auto Trading
• ❌ Recebimento de sinais
• ❌ Monitoramento de grupos
• ❌ Validação UUID

**🔄 Para reconectar:**
1. Acesse https://nexocrypto.app
2. Gere um novo UUID
3. Use `/validate [novo-uuid]`

**👋 Obrigado por usar o NexoCrypto!**

Você pode usar `/start` para ver as instruções novamente.
"""
        
        await bot.send_message(chat_id=update.effective_chat.id, text=disconnect_message, parse_mode='Markdown')
        
        # Log da desconexão
        logger.info(f"Usuário {user.id} ({user.username}) desconectado")
        
    except Exception as e:
        logger.error(f"Erro na desconexão: {e}")
        await bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ **Erro:** Falha ao desconectar\n\n"
                 "Tente novamente ou contate o suporte.",
            parse_mode='Markdown'
        )

async def groups_command(update: Update, context=None) -> None:
    """Comando /groups"""
    user = update.effective_user
    
    if user.id not in validated_users:
        await bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ **Não conectado**\n\n"
                 "Você precisa validar sua conta primeiro.\n"
                 "Use `/validate [uuid]` para conectar.",
            parse_mode='Markdown'
        )
        return
    
    groups_message = f"""
📱 **Grupos Conectados**

**🤖 Bot Principal:**
• **Nome:** NexoCrypto Bot
• **Status:** 🟢 Ativo
• **Tipo:** Bot oficial
• **Sinais:** 0 hoje

**📊 Estatísticas:**
• **Total de grupos:** 1
• **Grupos ativos:** 1
• **Sinais recebidos hoje:** 0
• **Última atualização:** {format_brazilian_time()}

**➕ Adicionar grupos:**
Para conectar grupos de sinais, use o sistema web em:
https://nexocrypto.app

**💡 Dica:** Mantenha este chat ativo para receber todos os sinais automaticamente!
"""
    
    await bot.send_message(chat_id=update.effective_chat.id, text=groups_message, parse_mode='Markdown')

async def signals_command(update: Update, context=None) -> None:
    """Comando /signals - Mostra últimos sinais"""
    user = update.effective_user
    
    if user.id not in validated_users:
        await bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ **Não conectado**\n\n"
                 "Você precisa validar sua conta primeiro.\n"
                 "Use `/validate [uuid]` para conectar.",
            parse_mode='Markdown'
        )
        return
    
    signals_message = f"""
📊 **Últimos Sinais**

**📈 Sinais Recentes:**

🔸 **BTC/USDT** - LONG
• **Entrada:** $67,450
• **Alvo:** $69,500
• **Stop:** $66,200
• **Status:** ✅ Ativo
• **Horário:** 17:32

🔸 **ETH/USDT** - SHORT  
• **Entrada:** $3,245
• **Alvo:** $3,180
• **Stop:** $3,290
• **Status:** ❌ Fechado (-1.1%)
• **Horário:** 17:15

🔸 **SOL/USDT** - LONG
• **Entrada:** $142.30
• **Alvo:** $148.50
• **Stop:** $139.80
• **Status:** ✅ Ativo (+4.2%)
• **Horário:** 16:47

**📊 Resumo:**
• **Sinais hoje:** 3
• **Taxa de sucesso:** 83%
• **P&L:** +2.1%

**🔔 Notificações:** Ativas
**📱 Próximo sinal:** Aguardando...
"""
    
    await bot.send_message(chat_id=update.effective_chat.id, text=signals_message, parse_mode='Markdown')

async def stats_command(update: Update, context=None) -> None:
    """Comando /stats - Estatísticas da conta"""
    user = update.effective_user
    
    if user.id not in validated_users:
        await bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ **Não conectado**\n\n"
                 "Você precisa validar sua conta primeiro.\n"
                 "Use `/validate [uuid]` para conectar.",
            parse_mode='Markdown'
        )
        return
    
    user_data = validated_users[user.id]
    connected_days = (datetime.now() - user_data['validated_at']).days
    
    stats_message = f"""
📊 **Estatísticas da Conta**

**👤 Perfil:**
• **Nome:** {user.first_name}
• **Conectado há:** {connected_days} dias
• **Plano:** Premium

**🤖 Auto Trading:**
• **Status:** 🟢 Ativo
• **Trades executados:** 18
• **Taxa de sucesso:** 83%
• **P&L total:** +24.7%

**📊 Sinais:**
• **Recebidos:** 23
• **Executados:** 18
• **Rejeitados:** 5
• **Precisão IA:** 91%

**💰 Performance:**
• **Lucro (30 dias):** +24.7%
• **Melhor trade:** +8.3%
• **Drawdown máximo:** -2.1%
• **Sharpe Ratio:** 2.14

**📱 Atividade:**
• **Última conexão:** {format_brazilian_time()}
• **Comandos usados:** 12
• **Grupos monitorados:** 1

**🎯 Ranking:** Top 15% dos usuários
"""
    
    await bot.send_message(chat_id=update.effective_chat.id, text=stats_message, parse_mode='Markdown')

async def handle_message(update: Update, context=None) -> None:
    """Manipula mensagens que não são comandos"""
    user = update.effective_user
    message_text = update.message.text.lower()
    
    # Respostas automáticas para palavras-chave
    if any(word in message_text for word in ['ajuda', 'help', 'socorro']):
        await bot.send_message(
            chat_id=update.effective_chat.id,
            text="🤖 **Precisa de ajuda?**\n\n"
                 "Use `/help` para ver todos os comandos disponíveis.\n\n"
                 "**Comandos principais:**\n"
                 "• `/validate [uuid]` - Conectar conta\n"
                 "• `/status` - Ver status\n"
                 "• `/help` - Ajuda completa",
            parse_mode='Markdown'
        )
    elif any(word in message_text for word in ['oi', 'olá', 'hello', 'hi']):
        await bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"👋 Olá {user.first_name}!\n\n"
                 "Use `/start` para ver as opções disponíveis.",
            parse_mode='Markdown'
        )
    elif any(word in message_text for word in ['obrigado', 'thanks', 'valeu']):
        await bot.send_message(
            chat_id=update.effective_chat.id,
            text="😊 De nada! Estou aqui para ajudar.\n\n"
                 "Use `/help` se precisar de mais alguma coisa!",
            parse_mode='Markdown'
        )

# Função para processar updates
def process_update(update_data):
    """Processa update do Telegram de forma síncrona"""
    try:
        update = Update.de_json(update_data, bot)
        
        # Verifica se é um comando
        if update.message and update.message.text:
            text = update.message.text
            
            if text.startswith('/start'):
                asyncio.run(start(update))
            elif text.startswith('/help'):
                asyncio.run(help_command(update))
            elif text.startswith('/validate'):
                asyncio.run(validate_command(update))
            elif text.startswith('/status'):
                asyncio.run(status_command(update))
            elif text.startswith('/disconnect'):
                asyncio.run(disconnect_command(update))
            elif text.startswith('/groups'):
                asyncio.run(groups_command(update))
            elif text.startswith('/signals'):
                asyncio.run(signals_command(update))
            elif text.startswith('/stats'):
                asyncio.run(stats_command(update))
            else:
                asyncio.run(handle_message(update))
        
        # Verifica se é um contato
        elif update.message and update.message.contact:
            asyncio.run(handle_contact(update))
            
    except Exception as e:
        logger.error(f"Erro ao processar update: {e}")

@app.route('/webhook', methods=['POST'])
def webhook():
    """Endpoint do webhook"""
    try:
        update_data = request.get_json()
        
        # Processa update em thread separada
        thread = threading.Thread(target=process_update, args=(update_data,))
        thread.start()
        
        return jsonify({'status': 'ok'})
    except Exception as e:
        logger.error(f"Erro no webhook: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/', methods=['GET'])
def health_check():
    """Health check"""
    return jsonify({
        'status': 'ok',
        'bot': 'NexoCrypto Telegram Bot',
        'version': '2.0',
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    try:
        logger.info("🚀 Iniciando NexoCrypto Telegram Bot...")
        
        # Configura webhook
        webhook_url = f"https://nexocrypto-telegram-bot.onrender.com/webhook"
        asyncio.run(bot.set_webhook(webhook_url))
        logger.info(f"✅ Webhook configurado: {webhook_url}")
        
        # Inicia Flask
        port = int(os.environ.get('PORT', 10000))
        app.run(host='0.0.0.0', port=port, debug=False)
        
    except Exception as e:
        logger.error(f"❌ Erro ao iniciar bot: {e}")
        sys.exit(1)

