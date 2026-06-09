# Finance Dashboard

A personal finance dashboard built with Streamlit, reading from a local Excel spreadsheet.

## Pages

**Insights**
- Net Worth — account balances over time, allocation breakdown, P&L
- Cash Flow & Pinch Points — monthly spend vs income, upcoming one-off expenses
- Projection vs Actuals — net worth forecast compared to reality
- Goals & Summary — savings goals, pension summary

**Manage Data**
- Manage Investments — add monthly snapshots, add/remove tracked accounts
- Manage Expenses — add, edit, and delete upcoming one-off expenses

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Using your own data

The app reads from `ECONOMIC EVALUATION.xlsx` in the project root. This file is gitignored — your financial data never leaves your machine.

Structure your spreadsheet to match these sheets:
- **Net Worth Input** — account snapshots (Date, Account, Amount columns)
- **Montly Expenses** — recurring income and expense categories
- **Other Expenditure** — one-off expenses (Reason, Category, Date, Amount, Note)
- **Calcs** — monthly cash flow (Date, Monthly Expenditure, Other Expenditure, Income)
- **Projections** — projected vs actual net worth (Date, Projected Worth, Actual Worth)
- **GOALS** — savings goals (Goal, Cost, Timeframe, Monthly Saving)
- **PENSION** — pension balances

The following files are also gitignored (auto-created by the app):
- `manual_snapshots.csv` — monthly investment values added via the app
- `one_off_expenses.csv` — one-off expenses (seeded from Excel, then app-managed)
- `accounts_config.json` — tracked account names

## Running without real data

If no Excel file is present, the app automatically falls back to the sample files in `sample_data/`, which contain placeholder data so you can explore the interface.
