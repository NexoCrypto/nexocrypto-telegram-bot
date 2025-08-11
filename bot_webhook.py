#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
import asyncio
import threading
from datetime import datetime
from flask import Flask, request, jsonify
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
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
PORT = int(os.getenv('PORT', 10000))

# Flask app
app = Flask(__name__)

# Bot instance
bot = Bot(token=BOT_TOKEN)

# Função para processar updates de forma síncrona
def process_update_sync(update_data):
    """Processa update de forma síncrona"""
    try:
        update = Update.de_json(update_data, bot)
        
        if update.message:
            message = update.message
            chat_id = message.chat_id
            text = message.text
            
            logger.info(f"📨 Mensagem recebida: {text} de {chat_id}")
            
            # Processar comandos
            if text.startswith('/start'):
                handle_start(chat_id)
            elif text.startswith('/help'):
                handle_help(chat_id)
            elif text.startswith('/validate'):
                handle_validate(chat_id, text)
            elif text.startswith('/status'):
                handle_status(chat_id)
            elif text.startswith('/disconnect'):
                handle_disconnect(chat_id)
            elif text.startswith('/groups'):
                handle_groups(chat_id)
            elif text.startswith('/signals'):
                handle_signals(chat_id)
            elif text.startswith('/stats'):
                handle_stats(chat_id)
            elif message.contact:
                handle_contact(chat_id, message.contact)
            else:
                # Respostas automáticas
                handle_auto_responses(chat_id, text)
                
    except Exception as e:
        logger.error(f"Erro ao processar update: {e}")

def send_message(chat_id, text, parse_mode='HTML'):
    """Envia mensagem de forma síncrona"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode
        }
        response = requests.post(url, json=data, timeout=30)
        return response.json()
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem: {e}")
        return None

def handle_start(chat_id):
    """Comando /start"""
    message = """🚀 <b>Bem-vindo ao NexoCrypto Trading Bot!</b>

🤖 <b>Seu assistente pessoal para trading de criptomoedas</b>

<b>📋 COMANDOS DISPONÍVEIS:</b>
• /help - Ajuda completa
• /validate [UUID] - Validar conta
• /status - Status da conexão
• /groups - Grupos conectados
• /signals - Últimos sinais
• /stats - Estatísticas
• /disconnect - Desconectar

<b>🔗 COMO CONECTAR:</b>
1. Acesse: https://nexocrypto.app
2. Vá em "Auto Trading"
3. Copie seu UUID único
4. Use: /validate [SEU_UUID]

<b>✨ FUNCIONALIDADES:</b>
• 📊 Sinais de trading automáticos
• 🎯 Análise técnica avançada
• 📈 Estatísticas em tempo real
• 🔔 Notificações instantâneas
• 🛡️ Gestão de risco inteligente

<b>💬 SUPORTE:</b>
Para dúvidas, digite "ajuda" ou "suporte"

<i>Desenvolvido pela equipe NexoCrypto 🚀</i>"""
    
    send_message(chat_id, message)

def handle_help(chat_id):
    """Comando /help"""
    message = """📚 <b>AJUDA COMPLETA - NexoCrypto Bot</b>

<b>🤖 COMANDOS PRINCIPAIS:</b>

<b>/start</b> - Iniciar o bot
• Exibe boas-vindas e instruções básicas

<b>/validate [UUID]</b> - Validar sua conta
• Conecta sua conta do NexoCrypto ao bot
• Exemplo: /validate abc123-def456-ghi789

<b>/status</b> - Status da conexão
• Mostra se sua conta está conectada
• Exibe informações da conta ativa

<b>/groups</b> - Grupos conectados
• Lista todos os grupos de sinais conectados
• Mostra status de cada grupo

<b>/signals</b> - Últimos sinais
• Exibe os 5 sinais mais recentes
• Inclui performance e resultados

<b>/stats</b> - Estatísticas completas
• Performance geral da conta
• Lucros/perdas do mês
• Taxa de acerto dos sinais

<b>/disconnect</b> - Desconectar conta
• Remove a conexão com sua conta
• Requer confirmação

<b>🔧 COMANDOS ESPECIAIS:</b>

<b>Enviar contato</b> - Para captura de grupos
• Use o botão "Compartilhar contato"
• Necessário para validação completa

<b>📱 PALAVRAS-CHAVE:</b>
• "ajuda" ou "help" - Esta ajuda
• "suporte" - Contato do suporte
• "status" - Status rápido
• "grupos" - Lista de grupos

<b>🚨 PROBLEMAS COMUNS:</b>

<b>Bot não responde?</b>
• Verifique se digitou o comando corretamente
• Certifique-se que começou com /

<b>Validação falhou?</b>
• Verifique se o UUID está correto
• Copie novamente do site

<b>Não recebe sinais?</b>
• Confirme que sua conta está validada
• Verifique se há grupos conectados

<b>💬 SUPORTE TÉCNICO:</b>
Para problemas técnicos ou dúvidas avançadas, entre em contato com nossa equipe através do site oficial.

<i>NexoCrypto - Sua evolução no trading! 🚀</i>"""
    
    send_message(chat_id, message)

def handle_validate(chat_id, text):
    """Comando /validate"""
    try:
        parts = text.split()
        if len(parts) < 2:
            message = """❌ <b>UUID não fornecido!</b>

<b>📋 COMO USAR:</b>
/validate [SEU_UUID]

<b>🔗 ONDE ENCONTRAR SEU UUID:</b>
1. Acesse: https://nexocrypto.app
2. Vá em "Auto Trading"
3. Copie o UUID exibido
4. Use: /validate [UUID_COPIADO]

<b>💡 EXEMPLO:</b>
/validate abc123-def456-ghi789-klm012

<i>Precisa de ajuda? Digite /help</i>"""
            send_message(chat_id, message)
            return
        
        uuid = parts[1]
        logger.info(f"🔍 Validando UUID: {uuid} para chat {chat_id}")
        
        # Fazer requisição para o backend
        response = requests.post(
            f"{BACKEND_URL}/api/telegram/verify-userbot-code",
            json={"user_uuid": uuid},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('valid'):
                message = f"""✅ <b>VALIDAÇÃO REALIZADA COM SUCESSO!</b>

🎉 <b>Sua conta foi conectada ao bot!</b>

<b>📊 INFORMAÇÕES DA CONTA:</b>
• UUID: <code>{uuid}</code>
• Status: ✅ Ativo
• Data: {datetime.now().strftime('%d/%m/%Y às %H:%M')}

<b>📱 PRÓXIMO PASSO:</b>
Para completar a configuração e capturar seus grupos do Telegram automaticamente, você precisa compartilhar seu contato.

<b>🔗 COMO COMPARTILHAR CONTATO:</b>
1. Clique no botão "📎" (anexar)
2. Selecione "Contato"
3. Escolha "Meu contato"
4. Envie

⚠️ <b>IMPORTANTE:</b> Isso é necessário para capturar seus grupos do Telegram automaticamente, similar ao Cornix.

<b>🚀 APÓS COMPARTILHAR O CONTATO:</b>
• Seus grupos serão capturados automaticamente
• Você receberá sinais em tempo real
• Poderá usar todos os comandos do bot

<i>Digite /help para ver todos os comandos disponíveis!</i>"""
                send_message(chat_id, message)
            else:
                message = f"""❌ <b>UUID INVÁLIDO</b>

<b>🔍 UUID fornecido:</b> <code>{uuid}</code>

<b>❌ POSSÍVEIS PROBLEMAS:</b>
• UUID não existe no sistema
• UUID já foi usado por outro usuário
• Formato incorreto do UUID

<b>✅ SOLUÇÕES:</b>
1. Verifique se copiou o UUID completo
2. Acesse https://nexocrypto.app novamente
3. Gere um novo UUID se necessário
4. Tente novamente com /validate [NOVO_UUID]

<b>💡 FORMATO CORRETO:</b>
O UUID deve ter formato similar a:
<code>abc123-def456-ghi789-klm012</code>

<i>Precisa de ajuda? Digite /help</i>"""
                send_message(chat_id, message)
        else:
            message = """🔧 <b>ERRO DE CONEXÃO</b>

❌ Não foi possível conectar com o servidor no momento.

<b>🔄 TENTE NOVAMENTE:</b>
• Aguarde alguns segundos
• Execute o comando novamente
• Verifique sua conexão com a internet

<b>🆘 SE O PROBLEMA PERSISTIR:</b>
Entre em contato com o suporte através do site oficial.

<i>Obrigado pela paciência!</i>"""
            send_message(chat_id, message)
            
    except Exception as e:
        logger.error(f"Erro na validação: {e}")
        message = """⚠️ <b>ERRO INTERNO</b>

Ocorreu um erro ao processar sua validação.

<b>🔄 TENTE NOVAMENTE:</b>
• Aguarde alguns momentos
• Execute o comando novamente
• Certifique-se que o UUID está correto

<i>Se o problema persistir, contate o suporte.</i>"""
        send_message(chat_id, message)

def handle_contact(chat_id, contact):
    """Processa contato compartilhado"""
    try:
        phone_number = contact.phone_number
        first_name = contact.first_name or "Usuário"
        
        logger.info(f"📞 Contato recebido: {phone_number} de {chat_id}")
        
        # Fazer requisição para iniciar captura
        response = requests.post(
            f"{BACKEND_URL}/api/telegram/start-userbot-session",
            json={
                "user_uuid": "temp_uuid",  # Seria obtido do contexto
                "phone_number": phone_number,
                "telegram_chat_id": str(chat_id)
            },
            timeout=30
        )
        
        if response.status_code == 200:
            message = f"""✅ <b>CONTATO RECEBIDO COM SUCESSO!</b>

👤 <b>Informações:</b>
• Nome: {first_name}
• Telefone: {phone_number}
• Chat ID: {chat_id}

🔄 <b>PROCESSANDO...</b>
Estamos iniciando a captura automática dos seus grupos do Telegram. Este processo pode levar alguns minutos.

<b>📱 O QUE ESTÁ ACONTECENDO:</b>
• Conectando com sua conta do Telegram
• Identificando grupos de sinais
• Configurando recebimento automático
• Sincronizando com sua conta NexoCrypto

⏳ <b>AGUARDE...</b>
Você receberá uma notificação quando o processo for concluído.

<b>🎯 APÓS A CONFIGURAÇÃO:</b>
• Use /groups para ver grupos conectados
• Use /signals para ver últimos sinais
• Use /stats para acompanhar performance

<i>Obrigado por usar o NexoCrypto! 🚀</i>"""
            send_message(chat_id, message)
        else:
            message = """⚠️ <b>ERRO AO PROCESSAR CONTATO</b>

Recebemos seu contato, mas houve um problema na configuração automática.

<b>🔄 PRÓXIMOS PASSOS:</b>
• Nossa equipe foi notificada
• A configuração será feita manualmente
• Você receberá uma confirmação em breve

<b>📞 CONTATO RECEBIDO:</b>
• Telefone: {phone_number}
• Nome: {first_name}

<i>Obrigado pela paciência!</i>"""
            send_message(chat_id, message)
            
    except Exception as e:
        logger.error(f"Erro ao processar contato: {e}")
        message = """❌ <b>ERRO INTERNO</b>

Houve um problema ao processar seu contato.

<b>🔄 TENTE NOVAMENTE:</b>
• Compartilhe seu contato novamente
• Certifique-se que está usando o botão correto

<i>Se o problema persistir, contate o suporte.</i>"""
        send_message(chat_id, message)

def handle_status(chat_id):
    """Comando /status"""
    message = """📊 <b>STATUS DA CONEXÃO</b>

🔗 <b>CONEXÃO COM O BOT:</b>
• Status: ✅ Conectado
• Servidor: 🟢 Online
• Última atualização: Agora

⚠️ <b>VALIDAÇÃO DA CONTA:</b>
• Status: ❌ Não validado
• Para validar: /validate [SEU_UUID]

<b>🔧 FUNCIONALIDADES DISPONÍVEIS:</b>
• ✅ Comandos básicos
• ❌ Recebimento de sinais (requer validação)
• ❌ Estatísticas (requer validação)
• ❌ Grupos conectados (requer validação)

<b>📱 PRÓXIMOS PASSOS:</b>
1. Acesse: https://nexocrypto.app
2. Copie seu UUID
3. Use: /validate [UUID]
4. Compartilhe seu contato

<i>Digite /help para mais informações!</i>"""
    
    send_message(chat_id, message)

def handle_groups(chat_id):
    """Comando /groups"""
    message = """📱 <b>GRUPOS CONECTADOS</b>

⚠️ <b>CONTA NÃO VALIDADA</b>

Para ver seus grupos conectados, você precisa:

<b>1️⃣ VALIDAR SUA CONTA:</b>
• Acesse: https://nexocrypto.app
• Copie seu UUID
• Use: /validate [UUID]

<b>2️⃣ COMPARTILHAR CONTATO:</b>
• Clique em "📎" (anexar)
• Selecione "Contato"
• Envie "Meu contato"

<b>📊 APÓS A VALIDAÇÃO:</b>
Este comando mostrará:
• Lista de grupos conectados
• Status de cada grupo
• Quantidade de sinais recebidos
• Última atividade

<b>🎯 EXEMPLO DO QUE VOCÊ VERÁ:</b>
• 🟢 ByBit Pro Signals (Ativo)
• 🟢 Crypto VIP Club (Ativo)
• 🟡 Binance Futures (Pausado)

<i>Valide sua conta para acessar esta funcionalidade!</i>"""
    
    send_message(chat_id, message)

def handle_signals(chat_id):
    """Comando /signals"""
    message = """📈 <b>ÚLTIMOS SINAIS</b>

⚠️ <b>CONTA NÃO VALIDADA</b>

Para ver os últimos sinais, você precisa:

<b>1️⃣ VALIDAR SUA CONTA:</b>
• Use: /validate [SEU_UUID]

<b>2️⃣ CONECTAR GRUPOS:</b>
• Compartilhe seu contato
• Aguarde configuração automática

<b>📊 APÓS A VALIDAÇÃO:</b>
Este comando mostrará:
• 5 sinais mais recentes
• Par e direção (Long/Short)
• Preço de entrada
• Take Profits e Stop Loss
• Status atual (Ativo/Fechado)
• Resultado (Lucro/Prejuízo)

<b>🎯 EXEMPLO DO QUE VOCÊ VERÁ:</b>
📈 <b>BTC/USDT - LONG</b>
• Entrada: $45,230
• TP1: $46,100 ✅
• TP2: $46,800 ⏳
• SL: $44,500
• Status: 🟢 Ativo
• Resultado: +1.92%

<i>Valide sua conta para receber sinais!</i>"""
    
    send_message(chat_id, message)

def handle_stats(chat_id):
    """Comando /stats"""
    message = """📊 <b>ESTATÍSTICAS DA CONTA</b>

⚠️ <b>CONTA NÃO VALIDADA</b>

Para ver suas estatísticas, você precisa:

<b>1️⃣ VALIDAR SUA CONTA:</b>
• Use: /validate [SEU_UUID]

<b>2️⃣ CONECTAR GRUPOS:</b>
• Compartilhe seu contato
• Aguarde configuração automática

<b>📊 APÓS A VALIDAÇÃO:</b>
Este comando mostrará:

<b>📈 PERFORMANCE GERAL:</b>
• Total de sinais recebidos
• Taxa de acerto
• Lucro/Prejuízo total
• Melhor e pior trade

<b>📅 ESTATÍSTICAS DO MÊS:</b>
• Sinais deste mês
• Performance mensal
• Comparação com mês anterior

<b>🎯 GRUPOS MAIS RENTÁVEIS:</b>
• Ranking por performance
• Taxa de acerto por grupo
• Sinais mais lucrativos

<b>🏆 EXEMPLO DO QUE VOCÊ VERÁ:</b>
• Total de sinais: 127
• Taxa de acerto: 73.2%
• Lucro total: +18.4%
• Melhor trade: +8.7% (ETH/USDT)

<i>Valide sua conta para ver suas estatísticas!</i>"""
    
    send_message(chat_id, message)

def handle_disconnect(chat_id):
    """Comando /disconnect"""
    message = """🔌 <b>DESCONECTAR CONTA</b>

⚠️ <b>CONTA NÃO VALIDADA</b>

Atualmente você não possui uma conta conectada ao bot.

<b>🔗 PARA CONECTAR:</b>
1. Use: /validate [SEU_UUID]
2. Compartilhe seu contato
3. Aguarde configuração automática

<b>📊 APÓS CONECTAR:</b>
Este comando permitirá:
• Desconectar sua conta do bot
• Parar recebimento de sinais
• Limpar dados locais
• Confirmar desconexão

<b>⚠️ IMPORTANTE:</b>
A desconexão é permanente e requer nova validação para reconectar.

<b>🛡️ SEGURANÇA:</b>
• Sempre desconecte se não for mais usar
• Mantenha seu UUID seguro
• Não compartilhe credenciais

<i>Conecte sua conta primeiro para usar esta funcionalidade!</i>"""
    
    send_message(chat_id, message)

def handle_auto_responses(chat_id, text):
    """Respostas automáticas para palavras-chave"""
    text_lower = text.lower()
    
    if any(word in text_lower for word in ['ajuda', 'help', 'socorro']):
        handle_help(chat_id)
    elif any(word in text_lower for word in ['suporte', 'contato', 'problema']):
        message = """🆘 <b>SUPORTE NEXOCRYPTO</b>

<b>📞 CANAIS DE SUPORTE:</b>

<b>🌐 SITE OFICIAL:</b>
https://nexocrypto.app

<b>📧 EMAIL:</b>
suporte@nexocrypto.app

<b>💬 TELEGRAM:</b>
@nexocrypto_suporte

<b>🕐 HORÁRIO DE ATENDIMENTO:</b>
Segunda a Sexta: 9h às 18h (Brasília)
Sábado: 9h às 14h (Brasília)

<b>⚡ SUPORTE RÁPIDO:</b>
• Digite /help para ajuda completa
• Use /status para verificar conexão
• Tente /validate [UUID] para conectar

<b>🚨 EMERGÊNCIAS:</b>
Para problemas críticos ou urgentes, use o chat do site oficial.

<i>Estamos aqui para ajudar! 🚀</i>"""
        send_message(chat_id, message)
    elif any(word in text_lower for word in ['status', 'situacao', 'conexao']):
        handle_status(chat_id)
    elif any(word in text_lower for word in ['grupos', 'group', 'canais']):
        handle_groups(chat_id)
    elif any(word in text_lower for word in ['oi', 'ola', 'olá', 'hello', 'hi']):
        message = """👋 <b>Olá!</b>

Bem-vindo ao NexoCrypto Trading Bot!

<b>🚀 PARA COMEÇAR:</b>
• Digite /start para instruções completas
• Use /help para ver todos os comandos
• Digite /validate [UUID] para conectar sua conta

<b>💡 DICA:</b>
Se é sua primeira vez aqui, comece com /start

<i>Como posso ajudar você hoje?</i>"""
        send_message(chat_id, message)
    else:
        message = """🤖 <b>Comando não reconhecido</b>

<b>📋 COMANDOS DISPONÍVEIS:</b>
• /start - Iniciar o bot
• /help - Ajuda completa
• /validate [UUID] - Conectar conta
• /status - Status da conexão
• /groups - Grupos conectados
• /signals - Últimos sinais
• /stats - Estatísticas
• /disconnect - Desconectar

<b>💬 PALAVRAS-CHAVE:</b>
• "ajuda" - Ajuda completa
• "suporte" - Contato do suporte
• "status" - Status rápido

<i>Digite /help para instruções detalhadas!</i>"""
        send_message(chat_id, message)

@app.route('/webhook', methods=['POST'])
def webhook():
    """Endpoint do webhook"""
    try:
        update_data = request.get_json()
        if update_data:
            # Processar update de forma síncrona
            process_update_sync(update_data)
        return jsonify({'status': 'ok'})
    except Exception as e:
        logger.error(f"Erro no webhook: {e}")
        return jsonify({'status': 'error'}), 500

@app.route('/', methods=['GET'])
def health_check():
    """Health check"""
    return jsonify({
        'status': 'ok',
        'bot': 'NexoCrypto Telegram Bot',
        'version': '2.0.0'
    })

if __name__ == '__main__':
    try:
        logger.info("🚀 Iniciando NexoCrypto Telegram Bot...")
        
        # Configurar webhook
        webhook_url = f"https://nexocrypto-telegram-bot.onrender.com/webhook"
        
        # Configurar webhook usando requests
        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
            json={'url': webhook_url},
            timeout=30
        )
        
        if response.status_code == 200:
            logger.info(f"✅ Webhook configurado: {webhook_url}")
        else:
            logger.error(f"❌ Erro ao configurar webhook: {response.text}")
        
        # Iniciar Flask
        app.run(host='0.0.0.0', port=PORT, debug=False)
        
    except Exception as e:
        logger.error(f"❌ Erro ao iniciar bot: {e}")

