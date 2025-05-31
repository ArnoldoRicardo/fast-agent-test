# how to use

you need to configure the .env file in the client (main folder) and the .env file in the scrapper-mcp folder
you can use the .env.example as template

## how to run client

```bash
python crypto_mini_report.py
```

## how to run scrapper-mcp

```bash
cd scrapper-mcp
python run_mcp_scrapper.py
```

## how to ingest data

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

cronjobs:

- cronjob_execute_coingeko_every_15min.bash
