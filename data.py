"""
data.py — loads data from CSV/JSON files.
Personal data files are gitignored; sample_data/ versions are committed
as runnable placeholders for anyone cloning without real data.
"""

import json
import os
import pandas as pd

# Personal data files — gitignored, never committed.
NET_WORTH_SNAPSHOTS_PATH = "net_worth_snapshots.csv"
CASH_FLOW_PATH           = "cash_flow.csv"
MONTHLY_EXPENSES_PATH    = "monthly_expenses.csv"
PROJECTIONS_PATH         = "projections.csv"
MANUAL_SNAPSHOTS_PATH    = "manual_snapshots.csv"
ACCOUNTS_CONFIG_PATH     = "accounts_config.json"
ONE_OFF_EXPENSES_PATH    = "one_off_expenses.csv"
INVESTED_AMOUNTS_PATH    = "invested_amounts.csv"

SAMPLE_NET_WORTH_SNAPSHOTS_PATH = "sample_data/net_worth_snapshots.csv"
SAMPLE_CASH_FLOW_PATH           = "sample_data/cash_flow.csv"
SAMPLE_MONTHLY_EXPENSES_PATH    = "sample_data/monthly_expenses.csv"
SAMPLE_PROJECTIONS_PATH         = "sample_data/projections.csv"
SAMPLE_MANUAL_SNAPSHOTS_PATH    = "sample_data/manual_snapshots.csv"
SAMPLE_ACCOUNTS_CONFIG_PATH     = "sample_data/accounts_config.json"
SAMPLE_ONE_OFF_EXPENSES_PATH    = "sample_data/one_off_expenses.csv"
SAMPLE_INVESTED_AMOUNTS_PATH    = "sample_data/invested_amounts.csv"


def _resolve(real_path, sample_path):
    """Return real path if it exists, otherwise fall back to the sample."""
    return real_path if os.path.exists(real_path) else sample_path


# ---------------------------------------------------------------------------
# NET WORTH SNAPSHOTS
# ---------------------------------------------------------------------------
def _load_net_worth_snapshots():
    path = _resolve(NET_WORTH_SNAPSHOTS_PATH, SAMPLE_NET_WORTH_SNAPSHOTS_PATH)
    df = pd.read_csv(path, parse_dates=["date"])
    return df.sort_values("date").reset_index(drop=True)


# ---------------------------------------------------------------------------
# MONTHLY INCOME — latest income value from cash_flow.csv
# ---------------------------------------------------------------------------
def _load_monthly_income():
    path = _resolve(CASH_FLOW_PATH, SAMPLE_CASH_FLOW_PATH)
    df = pd.read_csv(path)
    if df.empty or "income" not in df.columns:
        return 0
    return float(df["income"].iloc[-1])


# ---------------------------------------------------------------------------
# MONTHLY EXPENSES
# ---------------------------------------------------------------------------
def _load_monthly_expenses():
    path = _resolve(MONTHLY_EXPENSES_PATH, SAMPLE_MONTHLY_EXPENSES_PATH)
    return pd.read_csv(path)


# ---------------------------------------------------------------------------
# ONE-OFF EXPENSES — editable store
# ---------------------------------------------------------------------------
_ONE_OFF_COLUMNS = ["reason", "category", "date", "amount", "note"]


def load_one_off_expenses():
    path = _resolve(ONE_OFF_EXPENSES_PATH, SAMPLE_ONE_OFF_EXPENSES_PATH)
    if os.path.exists(path):
        df = pd.read_csv(path, parse_dates=["date"])
        df["note"] = df["note"].where(df["note"].notna(), None)
        return df[_ONE_OFF_COLUMNS]
    return pd.DataFrame(columns=_ONE_OFF_COLUMNS)


def _save_one_off_expenses(df):
    df = df[_ONE_OFF_COLUMNS].sort_values("date").reset_index(drop=True)
    df.to_csv(ONE_OFF_EXPENSES_PATH, index=False)
    return df


def add_one_off_expense(reason, category, date, amount, note=None):
    df = load_one_off_expenses()
    new_row = pd.DataFrame([{
        "reason": reason, "category": category,
        "date": pd.Timestamp(date), "amount": amount,
        "note": note or None,
    }])
    df = pd.concat([df, new_row], ignore_index=True)
    _save_one_off_expenses(df)


def update_one_off_expense(row_id, reason, category, date, amount, note=None):
    df = load_one_off_expenses()
    if row_id not in df.index:
        return False
    df.loc[row_id] = {
        "reason": reason, "category": category,
        "date": pd.Timestamp(date), "amount": amount,
        "note": note or None,
    }
    _save_one_off_expenses(df)
    return True


def delete_one_off_expense(row_id):
    df = load_one_off_expenses()
    if row_id not in df.index:
        return False
    df = df.drop(index=row_id)
    _save_one_off_expenses(df)
    return True


# ---------------------------------------------------------------------------
# CASH FLOW — recomputed live from monthly expenses + editable one-off store
# ---------------------------------------------------------------------------
def get_cash_flow():
    """
    Cash flow recomputed live: recurring monthly expenses + the editable
    one-off expenses store, so adding/editing one-off expenses immediately
    flows through to the Cash Flow & Pinch Points charts. Historical income
    figures are read from cash_flow.csv; months without a recorded income
    fall back to the latest known monthly income.
    """
    path = _resolve(CASH_FLOW_PATH, SAMPLE_CASH_FLOW_PATH)
    base = pd.read_csv(path, parse_dates=["date"])

    oo = load_one_off_expenses()
    monthly_total = _load_monthly_expenses()["amount"].sum()

    base_periods = base["date"].dt.to_period("M")
    income_lookup = dict(zip(base_periods, base["income"]))
    latest_income = float(base["income"].iloc[-1]) if len(base) else _load_monthly_income()

    oo_periods = oo["date"].dt.to_period("M") if len(oo) else pd.Series([], dtype="period[M]")
    one_off_by_month = oo.groupby(oo_periods)["amount"].sum() if len(oo) else pd.Series(dtype=float)

    months = sorted(set(base_periods) | set(oo_periods))
    rows = []
    for m in months:
        rows.append({
            "date": m.to_timestamp(),
            "monthly_expenses": monthly_total,
            "one_off_expenses": float(one_off_by_month.get(m, 0)),
            "income": income_lookup.get(m, latest_income),
        })
    df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    df["total_expenses"] = df["monthly_expenses"] + df["one_off_expenses"]
    df["remaining"] = df["income"] - df["total_expenses"]
    df["cumulative"] = df["remaining"].cumsum()
    return df


# ---------------------------------------------------------------------------
# PROJECTIONS
# ---------------------------------------------------------------------------
def _load_projections():
    path = _resolve(PROJECTIONS_PATH, SAMPLE_PROJECTIONS_PATH)
    df = pd.read_csv(path, parse_dates=["date"])
    df["actual"] = pd.to_numeric(df["actual"], errors="coerce")
    return df


# Anchor month — projection starts here and is held fixed; everything after
# is recomputed dynamically from income, recurring expenses, and one-off
# expenses for that month.
PROJECTION_ANCHOR_DATE = pd.Timestamp("2025-07-01")


def get_projections():
    """
    Projections from PROJECTION_ANCHOR_DATE onwards are recomputed live:
    each month's projected net worth = previous month's projected net worth
    + (income - recurring expenses - one-off expenses) for that month.
    Months before the anchor keep their original projected values.

    This means adding/editing one-off expenses immediately changes the
    forward projection.
    """
    df = _load_projections().sort_values("date").reset_index(drop=True)

    anchor_rows = df.index[df["date"] == PROJECTION_ANCHOR_DATE]
    if len(anchor_rows) == 0:
        return df

    monthly_total = _load_monthly_expenses()["amount"].sum()

    cf_path = _resolve(CASH_FLOW_PATH, SAMPLE_CASH_FLOW_PATH)
    cf_base = pd.read_csv(cf_path, parse_dates=["date"])
    cf_periods = cf_base["date"].dt.to_period("M")
    income_lookup = dict(zip(cf_periods, cf_base["income"]))
    latest_income = float(cf_base["income"].iloc[-1]) if len(cf_base) else _load_monthly_income()

    oo = load_one_off_expenses()
    oo_periods = oo["date"].dt.to_period("M") if len(oo) else pd.Series([], dtype="period[M]")
    one_off_by_month = oo.groupby(oo_periods)["amount"].sum() if len(oo) else pd.Series(dtype=float)

    cumulative = float(df.at[anchor_rows[0], "projected"])
    for i in range(anchor_rows[0] + 1, len(df)):
        period = df.at[i, "date"].to_period("M")
        income = income_lookup.get(period, latest_income)
        one_off = float(one_off_by_month.get(period, 0))
        remaining = income - monthly_total - one_off
        cumulative += remaining
        df.at[i, "projected"] = cumulative

    return df


# ---------------------------------------------------------------------------
# MANUAL SNAPSHOTS — monthly investment values added via the app
# ---------------------------------------------------------------------------
def load_manual_snapshots():
    path = _resolve(MANUAL_SNAPSHOTS_PATH, SAMPLE_MANUAL_SNAPSHOTS_PATH)
    if os.path.exists(path):
        df = pd.read_csv(path, parse_dates=["date"])
        if not df.empty:
            return df
    return pd.DataFrame(columns=["date", "account", "amount"])


def add_manual_snapshot(date, account_amounts: dict):
    """
    Append a new monthly snapshot. account_amounts: {account_name: amount}
    Returns (ok, message). Rejected if a snapshot already exists for that
    month, to avoid duplicate/conflicting monthly totals.
    """
    date = pd.Timestamp(date)
    period = date.to_period("M")

    existing = get_net_worth_snapshots()
    if period in set(existing["date"].dt.to_period("M")):
        return False, (
            f"A snapshot already exists for {period.strftime('%B %Y')}. "
            "Delete it first if you want to replace it."
        )

    df = load_manual_snapshots()
    new_rows = pd.DataFrame([
        {"date": date, "account": acc, "amount": amt}
        for acc, amt in account_amounts.items()
    ])
    df = pd.concat([df, new_rows], ignore_index=True)
    df.to_csv(MANUAL_SNAPSHOTS_PATH, index=False)

    _sync_projection_actual(date)

    total = sum(account_amounts.values())
    return True, f"Snapshot for {date.strftime('%d %b %Y')} saved — £{total:,.0f} total."


def delete_manual_snapshot(date):
    """Remove a manually-added snapshot for a given date."""
    date = pd.Timestamp(date)
    df = load_manual_snapshots()
    df = df[date != pd.to_datetime(df["date"])]
    df.to_csv(MANUAL_SNAPSHOTS_PATH, index=False)

    _sync_projection_actual(date)


# ---------------------------------------------------------------------------
# PROJECTIONS — sync "actual" net worth from snapshots
# ---------------------------------------------------------------------------
def _sync_projection_actual(snapshot_date):
    """
    A snapshot taken on `snapshot_date` represents the balance as of the end
    of the *previous* calendar month. Recompute and write the 'actual' net
    worth for that previous month into projections.csv. Adds a new row if
    the month isn't in projections.csv yet; clears the value if no snapshot
    exists for that date anymore.
    """
    snapshot_date = pd.Timestamp(snapshot_date)
    target_period = snapshot_date.to_period("M") - 1

    nws = get_net_worth_snapshots()
    same_date_rows = nws[nws["date"] == snapshot_date]
    total = float(same_date_rows["amount"].sum()) if len(same_date_rows) else float("nan")

    path = _resolve(PROJECTIONS_PATH, SAMPLE_PROJECTIONS_PATH)
    df = pd.read_csv(path, parse_dates=["date"])
    df["actual"] = pd.to_numeric(df["actual"], errors="coerce")

    match = df.index[df["date"].dt.to_period("M") == target_period]
    if len(match):
        df.loc[match[0], "actual"] = total
    elif not pd.isna(total):
        new_row = pd.DataFrame([{"date": target_period.to_timestamp(), "projected": float("nan"), "actual": total}])
        df = pd.concat([df, new_row], ignore_index=True)

    df = df.sort_values("date").reset_index(drop=True)
    df.to_csv(PROJECTIONS_PATH, index=False)


# ---------------------------------------------------------------------------
# ACCOUNT CONFIG
# ---------------------------------------------------------------------------
def _seed_account_config():
    accounts = sorted(_load_net_worth_snapshots()["account"].dropna().unique().tolist())
    config = {"active": accounts, "removed": []}
    _save_account_config(config)
    return config


def _save_account_config(config):
    with open(ACCOUNTS_CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def load_account_config():
    path = _resolve(ACCOUNTS_CONFIG_PATH, SAMPLE_ACCOUNTS_CONFIG_PATH)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return _seed_account_config()


def get_active_accounts():
    return load_account_config()["active"]


def add_account(name):
    config = load_account_config()
    name = name.strip()
    if not name:
        return False, "Account name can't be empty."
    if name in config["active"]:
        return False, f'"{name}" is already tracked.'
    if name in config["removed"]:
        config["removed"].remove(name)
    config["active"].append(name)
    _save_account_config(config)
    return True, f'Added "{name}".'


def remove_account(name):
    config = load_account_config()
    if name not in config["active"]:
        return False, f'"{name}" is not currently tracked.'
    config["active"].remove(name)
    config["removed"].append(name)
    _save_account_config(config)
    return True, f'Removed "{name}" from future tracking. Historical data is kept.'


# ---------------------------------------------------------------------------
# INVESTED AMOUNTS — running total contributed to each account
# ---------------------------------------------------------------------------
_INVESTED_COLUMNS = ["account", "invested"]


def load_invested_amounts():
    path = _resolve(INVESTED_AMOUNTS_PATH, SAMPLE_INVESTED_AMOUNTS_PATH)
    if os.path.exists(path):
        df = pd.read_csv(path)
        if not df.empty:
            return df[_INVESTED_COLUMNS]
    return pd.DataFrame(columns=_INVESTED_COLUMNS)


def _save_invested_amounts(df):
    df = df[_INVESTED_COLUMNS].sort_values("account").reset_index(drop=True)
    df.to_csv(INVESTED_AMOUNTS_PATH, index=False)
    return df


def set_invested_amount(account, invested):
    """Set the running total invested for an account (for initial setup/corrections)."""
    df = load_invested_amounts()
    existing = dict(zip(df["account"], df["invested"]))
    existing[account] = float(invested)
    df = pd.DataFrame(existing.items(), columns=_INVESTED_COLUMNS)
    return _save_invested_amounts(df)


def add_contributions(contributions: dict):
    """Add the given amounts to each account's running invested total."""
    df = load_invested_amounts()
    existing = dict(zip(df["account"], df["invested"]))
    for account, amount in contributions.items():
        if amount:
            existing[account] = existing.get(account, 0.0) + float(amount)
    if existing:
        df = pd.DataFrame(existing.items(), columns=_INVESTED_COLUMNS)
        _save_invested_amounts(df)


# ---------------------------------------------------------------------------
# Public exports — these are what app.py uses
# ---------------------------------------------------------------------------
def get_net_worth_snapshots():
    """CSV snapshots merged with any manually-added monthly entries."""
    base_df = _load_net_worth_snapshots()
    manual_df = load_manual_snapshots()
    combined = pd.concat([base_df, manual_df], ignore_index=True)
    combined["date"] = pd.to_datetime(combined["date"])
    return combined.sort_values("date").reset_index(drop=True)


def get_one_off_expenses():
    return load_one_off_expenses()


NET_WORTH_SNAPSHOTS = get_net_worth_snapshots()
MONTHLY_INCOME      = _load_monthly_income()
MONTHLY_EXPENSES    = _load_monthly_expenses()
ONE_OFF_EXPENSES    = get_one_off_expenses()
PROJECTIONS         = _load_projections()
