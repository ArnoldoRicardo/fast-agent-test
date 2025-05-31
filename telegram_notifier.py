import os
import requests
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Obtener token del bot desde variables de entorno
TOKEN = os.getenv("TOKEN_TELEGRAM_BOT")
# Obtener chat_id desde variables de entorno (opcional)
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# URL base para la API de Telegram
BASE_URL = f"https://api.telegram.org/bot{TOKEN}/"


def get_updates():
    """Obtiene las actualizaciones recientes del bot.

    Returns:
        dict: Respuesta de la API de Telegram en formato JSON
    """
    if not TOKEN:
        return {"ok": False, "error": "No se ha configurado el token del bot."}

    url = f"{BASE_URL}getUpdates"

    try:
        response = requests.get(url)
        return response.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}


def send_telegram_message(message, chat_id=None):
    """Envía un mensaje a un chat de Telegram.

    Args:
        message (str): Mensaje a enviar.
        chat_id (str, optional): ID del chat o nombre de usuario.

    Returns:
        dict: Respuesta de la API de Telegram en formato JSON
    """
    if not TOKEN:
        return {"ok": False, "error": "No se ha configurado el token del bot."}

    # Usar chat_id proporcionado o el de las variables de entorno
    target_chat_id = chat_id or CHAT_ID
    if not target_chat_id:
        return {"ok": False, "error": "No se ha proporcionado un chat_id."}

    # URL para enviar mensajes
    url = f"{BASE_URL}sendMessage"

    # Parámetros del mensaje
    params = {
        "chat_id": target_chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        response = requests.post(url, json=params)
        return response.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}
