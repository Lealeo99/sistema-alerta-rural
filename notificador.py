import asyncio
from telegram import Bot
from telegram.error import TelegramError
import os

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', 'SEU_TOKEN_AQUI')

async def enviar_telegram(chat_id: str, mensagem: str):
    """Envia mensagem via Telegram"""
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        await bot.send_message(chat_id=chat_id, text=mensagem, parse_mode='Markdown')
        return {'status': 'sucesso', 'chat_id': chat_id}
    except TelegramError as e:
        return {'status': 'erro', 'chat_id': chat_id, 'erro': str(e)}

def formatar_alerta(nome_prop: str, invasor: str, distancia: float, coordenadas: str) -> str:
    """Formata a mensagem de alerta"""
    return f"""
🚨 **ALERTA DE INVASÃO** 🚨

Olá *{nome_prop}*!

⚠️ Invasão detectada a *{distancia}km* da sua propriedade.

**Detalhes:**
• Tipo: {invasor}
• Localização aproximada: `{coordenadas}`

**Ações recomendadas:**
1️⃣ Verifique câmeras de segurança
2️⃣ Acione os vizinhos próximos
3️⃣ Contate a polícia (190)

---
🌾 Sistema de Alerta Rural
    """

async def notificar_vizinhos(vizinhos: list, invasor: str, lat: float, lon: float):
    """Envia notificações para todos vizinhos"""
    resultados = []
    
    for vizinho in vizinhos:
        mensagem = formatar_alerta(
            vizinho['nome'],
            invasor,
            vizinho['distancia_km'],
            f"{lat}, {lon}"
        )
        
        resultado = await enviar_telegram(vizinho['telegram_id'], mensagem)
        resultados.append(resultado)
        
        # Pequena pausa para não sobrecarregar a API
        await asyncio.sleep(0.5)
    
    return resultados