"""
Script para iniciar el servidor MCP de finanzas.
"""

from src.mcp.mcp_server import start_server

if __name__ == "__main__":
    print("Iniciando servidor MCP de finanzas...")
    start_server(port=8080)
