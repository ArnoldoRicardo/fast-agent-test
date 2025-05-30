# Modelos de Datos y Estrategias de Análisis

Este documento describe los modelos de datos disponibles en el sistema y las posibles estrategias de análisis que se pueden implementar utilizando estos datos.

## Datos de Criptomonedas

### Estructura de Datos

#### Modelo: CryptoCurrency

Información básica sobre una criptomoneda.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | Integer | Identificador único |
| symbol | String | Símbolo de la criptomoneda (ej. BTC, ETH) |
| name | String | Nombre completo (ej. Bitcoin, Ethereum) |
| slug | String | Slug para identificación en APIs (ej. bitcoin, ethereum) |
| last_updated | DateTime | Última actualización de la información |

#### Modelo: CryptoPrice

Precios históricos de criptomonedas.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | Integer | Identificador único |
| cryptocurrency_id | Integer | Referencia a la criptomoneda (FK) |
| timestamp | DateTime | Marca de tiempo de la medición |
| price_usd | Float | Precio en USD |
| market_cap_usd | Float | Capitalización de mercado en USD |
| volume_24h_usd | Float | Volumen de operaciones en 24h en USD |
| percent_change_24h | Float | Cambio porcentual en 24h |

### Formato de Respuesta API

La API devuelve los datos de criptomonedas en el siguiente formato:

```json
{
  "BTC": {
    "name": "Bitcoin",
    "symbol": "BTC",
    "price_usd": 50000.0,
    "market_cap_usd": 950000000000,
    "volume_24h_usd": 30000000000,
    "percent_change_24h": 2.5,
    "timestamp": "2025-05-30T15:00:00Z"
  },
  "ETH": {
    "name": "Ethereum",
    "symbol": "ETH",
    "price_usd": 3000.0,
    "market_cap_usd": 350000000000,
    "volume_24h_usd": 15000000000,
    "percent_change_24h": 1.8,
    "timestamp": "2025-05-30T15:00:00Z"
  },
  // ... otros símbolos
}
```

### Endpoints Disponibles

- `GET /crypto` - Obtiene los precios actuales de todas las criptomonedas
- `GET /crypto?symbols=BTC,ETH` - Filtra por símbolos específicos
- `GET /crypto/collect` - Fuerza una actualización de datos

### Estrategias de Análisis

#### 1. Análisis de Tendencias

Utilizando los datos históricos de precios, se pueden identificar tendencias a corto, medio y largo plazo:

- **Tendencia a corto plazo**: Análisis de movimientos de precio en períodos de 1-7 días
- **Tendencia a medio plazo**: Análisis de movimientos de precio en períodos de 1-4 semanas
- **Tendencia a largo plazo**: Análisis de movimientos de precio en períodos de 1+ meses

Implementación:
```python
# Ejemplo conceptual de análisis de tendencias
def analyze_trend(symbol, timeframe_days=7):
    # Obtener datos históricos
    prices = get_historical_prices(symbol, days=timeframe_days)
    
    # Calcular media móvil simple
    sma = calculate_simple_moving_average(prices, window=5)
    
    # Determinar tendencia
    current_price = prices[-1]
    if current_price > sma[-1]:
        return "BULLISH"  # Alcista
    elif current_price < sma[-1]:
        return "BEARISH"  # Bajista
    else:
        return "NEUTRAL"  # Neutral
```

#### 2. Análisis de Volatilidad

La volatilidad es una medida importante para evaluar el riesgo de una criptomoneda:

- **Desviación estándar**: Mide la dispersión de los precios
- **True Range**: Mide la volatilidad basada en rangos de precios
- **ATR (Average True Range)**: Media móvil del True Range

Implementación:
```python
# Ejemplo conceptual de análisis de volatilidad
def calculate_volatility(symbol, timeframe_days=30):
    # Obtener datos históricos
    prices = get_historical_prices(symbol, days=timeframe_days)
    
    # Calcular desviación estándar
    std_dev = numpy.std(prices)
    
    # Calcular coeficiente de variación (CV)
    mean_price = numpy.mean(prices)
    cv = std_dev / mean_price
    
    return {
        "std_deviation": std_dev,
        "coefficient_variation": cv,
        "volatility_level": categorize_volatility(cv)
    }
```

#### 3. Análisis de Correlación

Examinar cómo se correlacionan los movimientos de precios entre diferentes criptomonedas:

- **Matriz de correlación**: Correlación entre múltiples criptomonedas
- **Correlación con Bitcoin**: Medir la dependencia de otras criptomonedas con BTC
- **Correlación con mercados tradicionales**: Relación con índices como S&P 500, oro, etc.

Implementación:
```python
# Ejemplo conceptual de análisis de correlación
def calculate_correlation_matrix(symbols, timeframe_days=30):
    # Diccionario para almacenar precios de cada símbolo
    all_prices = {}
    
    # Obtener datos históricos para cada símbolo
    for symbol in symbols:
        all_prices[symbol] = get_historical_prices(symbol, days=timeframe_days)
    
    # Crear DataFrame con pandas
    df = pandas.DataFrame(all_prices)
    
    # Calcular matriz de correlación
    correlation_matrix = df.corr()
    
    return correlation_matrix
```

#### 4. Análisis de Volumen

El volumen de operaciones puede proporcionar información sobre la fuerza de un movimiento de precios:

- **Relación precio-volumen**: Identificar si los movimientos de precios están respaldados por volumen
- **Anomalías de volumen**: Detectar picos inusuales que podrían indicar eventos importantes
- **Tendencias de volumen**: Analizar si el interés en una criptomoneda está aumentando o disminuyendo

Implementación:
```python
# Ejemplo conceptual de análisis de volumen
def analyze_volume_price_relationship(symbol, timeframe_days=14):
    # Obtener datos históricos
    data = get_historical_data(symbol, days=timeframe_days)
    
    # Calcular cambio diario en precio y volumen
    price_changes = calculate_daily_changes(data['prices'])
    volume_changes = calculate_daily_changes(data['volumes'])
    
    # Calcular coeficiente de correlación precio-volumen
    correlation = numpy.corrcoef(price_changes, volume_changes)[0, 1]
    
    # Identificar días con divergencia precio-volumen
    divergences = identify_price_volume_divergences(price_changes, volume_changes)
    
    return {
        "price_volume_correlation": correlation,
        "divergences": divergences
    }
```

#### 5. Indicadores Técnicos

Se pueden implementar varios indicadores técnicos utilizando los datos de precios:

- **Medias Móviles**: SMA, EMA, VWMA
- **Osciladores**: RSI, MACD, Estocástico
- **Bandas de Volatilidad**: Bollinger Bands, Keltner Channels
- **Soportes y Resistencias**: Niveles de Fibonacci, Pivotes

Implementación:
```python
# Ejemplo conceptual de cálculo de RSI
def calculate_rsi(symbol, timeframe_days=14, period=14):
    # Obtener datos históricos
    prices = get_historical_prices(symbol, days=timeframe_days)
    
    # Calcular cambios diarios
    daily_changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    
    # Separar ganancias y pérdidas
    gains = [change if change > 0 else 0 for change in daily_changes]
    losses = [abs(change) if change < 0 else 0 for change in daily_changes]
    
    # Calcular promedio de ganancias y pérdidas
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    # Calcular RS (Relative Strength)
    rs = avg_gain / avg_loss if avg_loss > 0 else float('inf')
    
    # Calcular RSI
    rsi = 100 - (100 / (1 + rs))
    
    return rsi
```

---

## Modelos Adicionales (Pendientes)

### Acciones y ETFs (Pendiente)
...

### Indicadores Macroeconómicos (Pendiente)
...

### Instrumentos de Renta Fija (Pendiente)
...
