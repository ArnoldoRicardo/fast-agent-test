#!/bin/bash
# Script para configurar el entorno del proyecto scrapper-mcp

# Crear directorio de datos si no existe
mkdir -p data

# Crear entorno virtual
python -m venv .venv

# Activar el entorno virtual
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Inicializar la base de datos
python main.py --init-db

echo "Entorno configurado correctamente."
echo "Para activar el entorno virtual, ejecuta: source .venv/bin/activate"
echo "Para iniciar el servidor API: python main.py --mode api"
echo "Para iniciar el servidor MCP: python main.py --mode mcp"
