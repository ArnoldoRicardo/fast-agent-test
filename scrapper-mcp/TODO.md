# Plan de Implementación para scrapper-mcp

## Stack Tecnológico

- **Base de Datos**: SQLite (versión ligera y sin servidor)
- **API**: FastAPI
- **Testing**: pytest
- **Scraping**: Requests, AIOHTTP, BeautifulSoup
- **APIs Financieras**: yfinance, python-binance, requests-cache
- **Programación de Tareas**: APScheduler
- **Servidor MCP**: Implementación basada en el estándar MCP

## Lista de TODOs

### Fase 1: Configuración y Estructura Básica

- [x] Crear estructura de directorios del proyecto
- [x] Configurar entorno virtual
- [x] Crear `requirements.txt` con dependencias iniciales
- [x] Configurar SQLite y esquema de base de datos
- [x] Implementar configuración básica (config.py)
- [x] Configurar logging
- [x] Crear script de inicialización de la base de datos

### Fase 2: Colectores de Datos

- [x] Implementar colector base (base_collector.py)
- [-] Implementar colector de criptomonedas (crypto.py)
  - [x] Integración con CoinGecko API
  - [x] Caché y manejo de límites de tasa
  - [x] Almacenamiento en SQLite
  - [] perfeccionar flujo de injestada de datos y probar (yo: evaluo)
- [ ] Implementar colector de acciones/ETFs (stocks.py)
  - [ ] Integración con yfinance
  - [ ] Manejo de símbolos y datos históricos
  - [ ] Almacenamiento en SQLite
- [ ] Implementar colector de datos macroeconómicos (macro.py)
  - [ ] Inflación US/EU
  - [ ] Tasas de interés bancarias
  - [ ] Almacenamiento en SQLite
- [ ] Implementar colector de rendimientos de tasa fija (fixed_income.py)
  - [ ] Datos de bonos y plazos fijos
  - [ ] Almacenamiento en SQLite

### Fase 3: API y Servidor MCP

- [ ] Implementar servidor FastAPI (api/server.py)
- [ ] Implementar endpoints RESTful básicos
  - [ ] GET /crypto
  - [ ] GET /stocks
  - [ ] GET /macro
  - [ ] GET /fixed-income
- [ ] Implementar interfaz MCP (mcp/server.py)
  - [ ] Definir herramientas MCP
  - [ ] Implementar manejadores de solicitudes
  - [ ] Convertir datos a formato MCP

### Fase 4: Programación de Tareas

- [ ] Configurar APScheduler
- [ ] Implementar tareas programadas para cada colector
- [ ] Configurar frecuencias de actualización
  - [ ] Crypto: cada 15 minutos
  - [ ] Stocks: cada hora (durante horario de mercado)
  - [ ] Macro/Fixed Income: diario

### Fase 5: Testing

- [ ] Configurar pytest
- [ ] Implementar tests para colectores
- [ ] Implementar tests para API
- [ ] Implementar tests para servidor MCP
- [ ] Configurar CI/CD básico (opcional)

### Fase 6: Documentación y Refinamiento

- [ ] Actualizar README.md con instrucciones de instalación y uso
- [ ] Documentar API endpoints
- [ ] Documentar herramientas MCP
- [ ] Crear ejemplos de integración con Fast-Agent

## Priorización Inicial

Para comenzar rápidamente, podemos enfocarnos en:

1. Configuración básica y estructura del proyecto
2. Implementación del colector de criptomonedas (el más sencillo para empezar)
3. Configuración de SQLite para almacenamiento
4. Implementación básica del servidor FastAPI
5. Implementación básica del servidor MCP

## Estimación de Tiempo

- **Fase 1**: 1-2 días
- **Fase 2**: 3-5 días (dependiendo de la complejidad de cada API)
- **Fase 3**: 2-3 días
- **Fase 4**: 1-2 días
- **Fase 5**: 2-3 días
- **Fase 6**: 1-2 días

Tiempo total estimado: 10-17 días para una implementación básica funcional.
