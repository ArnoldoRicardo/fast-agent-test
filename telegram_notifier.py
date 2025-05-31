import os
import requests
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

TOKEN_BOT = os.environ.get("TOKEN_TELEGRAM_BOT")


def send_telegram_message(mensaje, chat_id='None'):
    """Envía un mensaje a un chat de Telegram.

    Args:
        mensaje (str): El mensaje a enviar
        chat_id (str, optional): ID del chat o nombre de usuario. Por defecto '@arlf0'.

    Returns:
        dict: Respuesta de la API de Telegram en formato JSON
    """
    if not TOKEN_BOT:
        print("Error: No se ha configurado TOKEN_TELEGRAM_BOT en las variables de entorno")
        return {"ok": False, "error": "No se ha configurado TOKEN_TELEGRAM_BOT"}

    # Si no se proporciona chat_id, intentar obtenerlo de las variables de entorno
    if not chat_id:
        chat_id = os.environ.get("TELEGRAM_CHAT_ID", "1375768405")
        print(f"Usando chat_id: {chat_id}")

    url = f"https://api.telegram.org/bot{TOKEN_BOT}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": mensaje,
        "parse_mode": "Markdown"  # Permite formato markdown en el mensaje
    }

    try:
        response = requests.post(url, data=data)
        return response.json()
    except Exception as e:
        print(f"Error al enviar mensaje a Telegram: {e}")
        return {"ok": False, "error": str(e)}


if __name__ == "__main__":
    print("Enviando mensaje de prueba a Telegram...")
    result = send_telegram_message("Hola, este es un mensaje de prueba")
    print(result)
