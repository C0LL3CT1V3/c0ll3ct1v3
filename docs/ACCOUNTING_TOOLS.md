# Local accounting tools (tax-oriented)

The `backend/accounting_core` package contains SQLite-based utilities migrated from an internal tax workflow:

- `FINANCE_DB_PATH` — SQLite database file (default: `backend/var/finances.db`).
- `FINANCE_SCHEMA_PATH` — optional override for `schema.sql`.
- Parsers: `BANK_CSV`, `SQUARE_SALES_CSV`, `BANK_CATEGORIZED_CSV`, `PROFIT_LOSS_MD`, `PROFIT_LOSS_OUTPUT`.

## Initialize a local DB

From the `backend` directory with a virtualenv and `PYTHONPATH=.`:

```bash
mkdir -p var
python -c "from accounting_core.finance_db import FinanceDB; FinanceDB().init_db()"
```

## Import and reports

```bash
export FINANCE_DB_PATH=./var/finances.db
python -m accounting_core.import_chase path/to/your-export.csv
python -m accounting_core.generate_reports
```

Real exports stay **outside** this repository.

## Plaid / Square API

Bank linking and webhooks are integrated into the main FastAPI app under `/api/finance/*`. See `docs/finance-compliance/` for runbooks and environment templates.
