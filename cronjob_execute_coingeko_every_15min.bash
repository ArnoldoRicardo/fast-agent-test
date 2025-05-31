#!/bin/bash
# cronjob example: */15 * * * * /home/arlf0/dev/pimineto/fast-agent/cronjob_execute_coingeko_every_15min.bash

# Obtener el directorio donde se encuentra este script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Cambiar al directorio del proyecto
cd "${SCRIPT_DIR}/scrapper-mcp"

# Activar el entorno virtual
source .venv/bin/activate

# Ejecutar el script con PYTHONPATH configurado para encontrar los módulos
PYTHONPATH="${SCRIPT_DIR}/scrapper-mcp" python scripts/run_crypto_collector.py
