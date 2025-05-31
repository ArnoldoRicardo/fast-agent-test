import asyncio
from datetime import datetime
import json

from mcp_agent.core.fastagent import FastAgent
from telegram_notifier import send_telegram_message, send_crypto_summary

# Create the application
fast = FastAgent("Crypto Mini Report")


@fast.agent(
    name="crypto_mini_report",
    instruction="""Eres un analista de criptomonedas que genera informes concisos pero informativos para la toma de decisiones.
    
    Utiliza el servidor MCP de finanzas para obtener datos de Bitcoin (BTC) y Ethereum (ETH).
    
    Tu informe debe incluir:
    
    1. DATOS DE MERCADO:
       - Precios actuales de BTC, ETH
       - Variación porcentual en 24h, 7d (si está disponible)
       - Volumen de operaciones en 24h
       - Tendencia del mercado general en los últimos 30 días
    
    2. INDICADORES TÉCNICOS (usa la herramienta calculate_indicators):
       - Media Móvil Simple (SMA) y Exponencial (EMA) de 20 períodos
       - Índice de Fuerza Relativa (RSI)
       - MACD (si está disponible)
       - Bandas de Bollinger (si están disponibles)
       - Interpretación de estos indicadores (sobrecompra/sobreventa, tendencia, etc.)
    
    3. ANÁLISIS DE VELAS (usa la herramienta get_ohlcv_data):
       - Patrones de velas recientes (1-3 días) que sean significativos
       - Niveles de soporte y resistencia identificados
    
    4. SEÑALES DE ALERTA:
       - Identifica 1-2 patrones o situaciones que requieran atención especial
       - Posibles divergencias entre precio e indicadores
    
    5. CONCLUSIÓN:
       - Resumen de la tendencia actual basado en datos fundamentales y técnicos
       - Posible dirección a corto plazo (3-4 días) y mediano plazo (2-3 semanas)
       - Recomendación general (observar, comprar, vender, mantener)
    
    El informe debe ser conciso pero completo, no más de 30-35 líneas en total.
    Formatea el informe de manera clara con títulos y viñetas para facilitar la lectura rápida.
    Incluye la fecha actual al inicio.
    
    IMPORTANTE: Para obtener datos OHLCV, usa la herramienta get_ohlcv_data con símbolos como "BTCUSDT" o "ETHUSDT".
    Para calcular indicadores técnicos, usa la herramienta calculate_indicators con los mismos símbolos.
    """,
    servers=["finance"],
)
async def main() -> None:
    async with fast.run() as agent:
        # Generar el informe mini
        today = datetime.now().strftime("%Y-%m-%d")
        print(f"Generando informe técnico de criptomonedas para {today}...")

        # Solicitar el informe al agente
        report = await agent.crypto_mini_report.send("Generar informe técnico de criptomonedas con análisis de indicadores")

        # Separar el JSON del informe markdown

        string_magic = """}
*"""

        if string_magic in report:
            raw_data, reporte_filtered = report.split(string_magic)
        else:
            reporte_filtered = report
            raw_data = ""

        # Nombres de archivos
        report_filename = f"crypto_mini_report_{today}.md"
        raw_data_filename = f"crypto_mini_report_{today}_raw_data.json"

        # Guardar el informe formateado
        with open(report_filename, "w") as f:
            f.write(reporte_filtered)
        print(f"Informe guardado en {report_filename}")

        # Guardar los datos crudos
        with open(raw_data_filename, "w") as f:
            f.write(raw_data)
        print(f"Datos crudos guardados en {raw_data_filename}")

        # Enviar resumen por Telegram
        print("Enviando resumen por Telegram...")
        response = send_telegram_message(report)
        print(response)


if __name__ == "__main__":
    asyncio.run(main())
