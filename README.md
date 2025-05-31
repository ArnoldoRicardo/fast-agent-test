# how to run

```bash
python crypto_mini_report.py
```

# how to run scrapper-mcp

```bash
cd scrapper-mcp
python run_mcp_scrapper.py
```

# how to ingest data

coin_gecko real time

```bash
cd scrapper-mcp
python scripts/run_crypto_collector.py
```

coin_gecko historical

```bash
cd scrapper-mcp
python scripts/run_crypto_collector.py --historical --days 30 --interval daily
```

binance ohlcv

```bash
cd scrapper-mcp
python scripts/run_binance_collector.py
```
