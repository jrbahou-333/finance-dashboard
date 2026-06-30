import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

import data as d

st.set_page_config(
    page_title="Finance Dashboard",
    page_icon="💷",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Styling ---
st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 1.6rem; }
    .block-container { padding-top: 1.5rem; }
</style>
""", unsafe_allow_html=True)

PALETTES = {
    "Seaborn": [
        "#4C72B0", "#55A868", "#C44E52", "#8172B2", "#F5A623",
        "#64B5CD", "#CCB974", "#DD8452", "#937860", "#DA8BC3",
    ],
    "Cool": [
        "#2C5F8A", "#4A90A4", "#7FB3B0", "#A8C5D6", "#5B7FA6",
        "#3D8B7D", "#8BA888", "#6C7B8B", "#B8A88A", "#7A6F9B",
    ],
    "Vibrant": [
        "#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A",
        "#19D3F3", "#FF6692", "#B6E880", "#FF97FF", "#FECB52",
    ],
    "Earthy": [
        "#3F6F4F", "#7A8B4A", "#C9A227", "#A65E2E", "#6E5849",
        "#94B49F", "#D4B483", "#5C8374", "#B0735C", "#8C9B6E",
    ],
    "Pastel": [
        "#A8DADC", "#F4A261", "#E9C46A", "#CDB4DB", "#B5C99A",
        "#FFB4A2", "#9DB4C0", "#E5989B", "#C9CBA3", "#A3C4BC",
    ],
}

with open("content/how_it_works.md") as f:
    HOW_IT_WORKS = f.read()

PALETTE_NAME = d.get_palette_name()
PALETTE = PALETTES.get(PALETTE_NAME, PALETTES["Pastel"])

PLOTLY_TEMPLATE = "plotly_dark"


def color_map(values):
    """Assign a stable colour from the shared palette to each unique value."""
    return {v: PALETTE[i % len(PALETTE)] for i, v in enumerate(sorted(set(values)))}


def _go_to(page_value):
    st.session_state["nav_section"] = "Manage Data"
    st.session_state["nav_page_manage"] = page_value


# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    title_col, info_col = st.columns([5, 1])
    with title_col:
        st.title("Finance Dashboard")
    with info_col:
        with st.popover("", icon=":material/menu_book:", help="How this dashboard works"):
            st.markdown(HOW_IT_WORKS)
    st.caption("Jack's personal finance analytics")
    ANALYTICS_PAGES = ["Net Worth", "Cash Flow", "Projection"]
    MANAGE_PAGES = ["Manage Investments", "Manage Expenses"]

    section = st.radio("Section", ["Insights", "Manage Data"], label_visibility="collapsed", horizontal=True, key="nav_section")
    if section == "Insights":
        page = st.radio("Navigate", ANALYTICS_PAGES, label_visibility="collapsed", key="nav_page_insights")
    else:
        page = st.radio("Navigate", MANAGE_PAGES, label_visibility="collapsed", key="nav_page_manage")
    st.divider()

    # Quick stats
    nws = d.get_net_worth_snapshots()
    latest_date = nws["date"].max()
    latest = nws[nws["date"] == latest_date]
    total_nw = latest["amount"].sum()

    prev_dates = nws[nws["date"] < latest_date]["date"].unique()
    if len(prev_dates):
        prev_date = max(prev_dates)
        prev_total = nws[nws["date"] == prev_date]["amount"].sum()
        delta = total_nw - prev_total
    else:
        delta = None

    st.metric("Total Net Worth", f"£{total_nw:,.0f}", delta=f"£{delta:,.0f}" if delta else None)
    st.caption(f"As of {latest_date.strftime('%d %b %Y')}")
    st.metric("Monthly Income", f"£{d.MONTHLY_INCOME:,}")
    st.metric("Monthly Expenses", f"£{d.get_monthly_expenses()['amount'].sum():,}")

    st.divider()

    # Chart colour palette
    palette_options = list(PALETTES.keys())
    selected_palette = st.selectbox(
        "Chart colour palette", options=palette_options,
        index=palette_options.index(PALETTE_NAME) if PALETTE_NAME in palette_options else 0,
    )
    if selected_palette != PALETTE_NAME:
        d.set_palette_name(selected_palette)
        st.rerun()


# ============================================================
# PAGE 1 — NET WORTH
# ============================================================
if page == "Net Worth":
    st.header("Net Worth")

    df = nws.copy()
    pivot = df.pivot_table(index="date", columns="account", values="amount", aggfunc="sum").fillna(0)
    pivot["Total"] = pivot.sum(axis=1)
    pivot = pivot.sort_index()

    # Stacked area chart
    fig = go.Figure()
    accounts = [c for c in pivot.columns if c != "Total"]
    account_colors = color_map(accounts)
    for acc in accounts:
        color = account_colors[acc]
        fig.add_trace(go.Scatter(
            x=pivot.index, y=pivot[acc],
            name=acc,
            stackgroup="one",
            mode="lines",
            line=dict(width=0.5, color=color),
            fillcolor=color,
            hovertemplate=f"<b>{acc}</b><br>£%{{y:,.0f}}<extra></extra>",
        ))
    fig.add_trace(go.Scatter(
        x=pivot.index, y=pivot["Total"],
        name="Total",
        mode="lines+markers",
        line=dict(color="white", width=2, dash="dot"),
        marker=dict(size=6),
        hovertemplate="<b>Total</b><br>£%{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        title="Net Worth by Account Over Time",
        xaxis_title=None,
        yaxis_title="Value (£)",
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.15),
        height=420,
        template=PLOTLY_TEMPLATE,
        margin=dict(t=40, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Latest breakdown
    col1, col2 = st.columns([1, 1])
    with col1:
        sub_hdr, sub_btn = st.columns([2, 1])
        sub_hdr.subheader("Latest Snapshot")
        sub_btn.button("+ Update balances", on_click=_go_to, args=("Manage Investments",), use_container_width=True, type="primary")
        latest_df = (
            nws[nws["date"] == latest_date]
            .set_index("account")[["amount"]]
            .sort_values("amount", ascending=False)
        )
        latest_df.columns = ["Balance (£)"]
        latest_df["Balance (£)"] = latest_df["Balance (£)"].map(lambda x: f"£{x:,.0f}")
        st.dataframe(latest_df, use_container_width=True)

    with col2:
        st.subheader("Allocation")
        pos = latest[latest["amount"] > 0]
        fig2 = px.pie(
            pos, values="amount", names="account",
            color="account", color_discrete_map=account_colors,
            hole=0.45,
        )
        fig2.update_traces(textposition="outside", textinfo="label+percent")
        fig2.update_layout(
            showlegend=False, height=320, template=PLOTLY_TEMPLATE,
            margin=dict(t=10, b=10, l=10, r=10),
        )
        st.plotly_chart(fig2, use_container_width=True)

    # P&L table — invested vs current
    st.subheader("Invested vs Current Value")
    invested = d.load_invested_amounts()
    current = latest[["account", "amount"]].rename(columns={"amount": "current"})
    pl = invested.merge(current, on="account", how="outer").fillna(0)
    pl["P&L (£)"] = pl["current"] - pl["invested"]
    pl["P&L (%)"] = (pl["P&L (£)"] / pl["invested"].replace(0, float("nan")) * 100).round(1)
    pl = pl.sort_values("current", ascending=False).reset_index(drop=True)

    def color_pl(val):
        if isinstance(val, float) and val < 0:
            return "color: #ff6b6b"
        elif isinstance(val, float) and val > 0:
            return "color: #51cf66"
        return ""

    styled = (
        pl.rename(columns={"account": "Account", "invested": "Invested (£)", "current": "Current (£)"})
        .style
        .format({"Invested (£)": "£{:,.0f}", "Current (£)": "£{:,.0f}",
                 "P&L (£)": "£{:,.0f}", "P&L (%)": "{:.1f}%"})
        .map(color_pl, subset=["P&L (£)", "P&L (%)"])
    )
    st.dataframe(styled, use_container_width=True, hide_index=True)


# ============================================================
# PAGE 2 — CASH FLOW
# ============================================================
elif page == "Cash Flow":
    st.header("Cash Flow")

    cf = d.get_cash_flow()
    monthly_expenses = d.get_monthly_expenses()

    show_history = st.toggle("Show historical months", value=False)
    if not show_history:
        current_month = pd.Timestamp.today().to_period("M").to_timestamp()
        cf = cf[cf["date"] >= current_month].copy()

    col1, col2, col3 = st.columns(3)
    col1.metric("Monthly Income", f"£{d.MONTHLY_INCOME:,}")
    col2.metric("Avg Monthly Expenses", f"£{monthly_expenses['amount'].sum():,}")
    surplus = d.MONTHLY_INCOME - monthly_expenses["amount"].sum()
    col3.metric("Typical Monthly Surplus", f"£{surplus:,}")

    st.divider()

    # Build rich hover text for one-off bar (itemised per month)
    oo_all = d.get_one_off_expenses()
    oo_hover_texts = []
    for _, row in cf.iterrows():
        month = row["date"].to_period("M")
        items = oo_all[oo_all["date"].dt.to_period("M") == month]
        if items.empty or row["one_off_expenses"] == 0:
            oo_hover_texts.append("  None")
        else:
            oo_hover_texts.append(
                "<br>".join(f"  {r['reason']}: £{r['amount']:,.0f}" for _, r in items.iterrows())
            )

    # Filled-area expenses (recurring + one-off stacked), income as a line
    cf_colors = color_map(["Recurring Expenses", "One-off Expenses", "Income"])
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=cf["date"], y=cf["monthly_expenses"],
        name="Recurring Expenses",
        mode="lines",
        stackgroup="expenses",
        line=dict(width=0.5, color=cf_colors["Recurring Expenses"]),
        fillcolor=cf_colors["Recurring Expenses"],
        hovertemplate="Recurring: £%{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=cf["date"], y=cf["one_off_expenses"],
        name="One-off Expenses",
        mode="lines",
        stackgroup="expenses",
        line=dict(width=0.5, color=cf_colors["One-off Expenses"]),
        fillcolor=cf_colors["One-off Expenses"],
        customdata=oo_hover_texts,
        hovertemplate=(
            "<b>One-off Expenses</b><br>%{customdata}"
            "<br><b>Total: £%{y:,.0f}</b><extra></extra>"
        ),
    ))
    fig.add_trace(go.Scatter(
        x=cf["date"], y=cf["income"],
        name="Income",
        mode="lines+markers",
        line=dict(color=cf_colors["Income"], width=2),
        marker=dict(size=6),
        hovertemplate="Income: £%{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        title="Monthly Spend vs Income",
        xaxis_title=None,
        yaxis_title="£",
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.15),
        height=380,
        template=PLOTLY_TEMPLATE,
        margin=dict(t=40, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)

    # One-off expense timeline
    col_hdr, col_btn = st.columns([4, 1])
    col_hdr.subheader("Upcoming One-off Expenses")
    col_btn.button("+ Add / edit", on_click=_go_to, args=("Manage Expenses",), use_container_width=True, type="primary")
    oo = d.get_one_off_expenses().copy()
    oo_monthly = oo.groupby(["date", "category"])["amount"].sum().reset_index()

    category_colors = color_map(set(oo_monthly["category"]) | set(monthly_expenses["category"]))

    fig3 = px.bar(
        oo_monthly, x="date", y="amount", color="category",
        color_discrete_map=category_colors,
        labels={"amount": "£", "date": "", "category": "Category"},
        title="One-off Expenses by Month",
    )
    fig3.update_traces(width=1000 * 60 * 60 * 24 * 25)  # ~25 days, so bars don't bleed into neighbouring months
    fig3.update_layout(
        template=PLOTLY_TEMPLATE, height=300,
        legend=dict(orientation="h", y=-0.2),
        margin=dict(t=40, b=10),
        barmode="stack",
    )
    st.plotly_chart(fig3, use_container_width=True)

    # Expense table (read-only — manage entries via "Manage Data → Manage Expenses")
    with st.expander("Full one-off expense list", expanded=False):
        display = oo.copy()
        display["date"] = display["date"].dt.strftime("%b %Y")
        display["amount"] = display["amount"].map(lambda x: f"£{x:,.0f}")
        display.columns = ["Reason", "Category", "Month", "Amount", "Note"]
        st.dataframe(display, use_container_width=True, hide_index=True)
        st.caption('To add, edit, or delete one-off expenses, head to **Manage Data → Manage Expenses** in the sidebar.')

    # Monthly expense breakdown
    st.subheader("Recurring Monthly Expenses")
    fig4 = px.pie(
        monthly_expenses, values="amount", names="category",
        color="category", color_discrete_map=category_colors,
        hole=0.4, title=f"Monthly Spend Breakdown — Total £{monthly_expenses['amount'].sum():,}",
    )
    fig4.update_traces(textposition="outside", textinfo="label+percent")
    fig4.update_layout(
        showlegend=False, template=PLOTLY_TEMPLATE, height=340,
        margin=dict(t=40, b=10, l=10, r=10),
    )
    col_a, col_b = st.columns([1, 1])
    with col_a:
        st.plotly_chart(fig4, use_container_width=True)
    with col_b:
        exp_df = monthly_expenses.copy()
        exp_df["amount"] = exp_df["amount"].map(lambda x: f"£{x:,.0f}")
        exp_df.columns = ["Category", "Monthly (£)"]
        st.dataframe(exp_df, use_container_width=True, hide_index=True)


# ============================================================
# PAGE 3 — PROJECTION
# ============================================================
elif page == "Projection":
    st.header("Projection")

    proj = d.get_projections()
    proj_known  = proj.dropna(subset=["projected"])

    # Actuals: total net worth per snapshot date, direct from snapshots
    nws_totals = (
        d.NET_WORTH_SNAPSHOTS
        .groupby("date", as_index=False)["amount"]
        .sum()
        .rename(columns={"amount": "actual"})
        .sort_values("date")
    )

    # Anchor = start of projected line (latest snapshot)
    anchor_row   = proj_known.iloc[0]  if len(proj_known)  else None
    proj_12m_row = proj_known.iloc[12] if len(proj_known) > 12 else proj_known.iloc[-1] if len(proj_known) else None
    proj_24m_row = proj_known.iloc[24] if len(proj_known) > 24 else proj_known.iloc[-1] if len(proj_known) else None

    if anchor_row is not None:
        col1, col2, col3 = st.columns(3)
        col1.metric("Current Net Worth",   f"£{anchor_row['projected']:,.0f}")
        col2.metric("Projected in 12 mo",  f"£{proj_12m_row['projected']:,.0f}",
                    delta=f"£{proj_12m_row['projected'] - anchor_row['projected']:+,.0f}")
        col3.metric("Projected in 24 mo",  f"£{proj_24m_row['projected']:,.0f}",
                    delta=f"£{proj_24m_row['projected'] - anchor_row['projected']:+,.0f}")

    st.divider()

    fig = go.Figure()

    # Historical actuals (total net worth per snapshot)
    fig.add_trace(go.Scatter(
        x=nws_totals["date"], y=nws_totals["actual"],
        name="Actual",
        mode="lines+markers",
        line=dict(color="#51cf66", width=2.5),
        marker=dict(size=7),
        hovertemplate="Actual: £%{y:,.0f}<extra></extra>",
    ))

    # Forward projection (starts at latest snapshot)
    fig.add_trace(go.Scatter(
        x=proj_known["date"], y=proj_known["projected"],
        name="Projected",
        mode="lines",
        line=dict(color="#4C72B0", width=2, dash="dot"),
        hovertemplate="Projected: £%{y:,.0f}<extra></extra>",
    ))

    # Vertical line at projection start
    if anchor_row is not None:
        fig.add_vline(
            x=anchor_row["date"].timestamp() * 1000,
            line_dash="dash", line_color="white", opacity=0.3,
            annotation_text="→ forecast", annotation_position="top right",
        )

    fig.update_layout(
        title="Net Worth: Historical & Projected",
        xaxis_title=None,
        yaxis_title="Net Worth (£)",
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.12),
        height=430,
        template=PLOTLY_TEMPLATE,
        margin=dict(t=40, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Forward projection table
    st.subheader("Forward Projection")
    fwd = proj_known[["date", "projected"]].copy()
    fwd["month_label"] = fwd["date"].dt.strftime("%b %Y")

    def color_proj(val):
        try:
            num = float(str(val).replace("£", "").replace(",", ""))
            return "color: #51cf66" if num >= 0 else "color: #ff6b6b"
        except Exception:
            return ""

    fwd_styled = (
        fwd[["month_label", "projected"]]
        .rename(columns={"month_label": "Month", "projected": "Projected Net Worth"})
        .style
        .format({"Projected Net Worth": "£{:,.0f}"})
    )
    st.dataframe(fwd_styled, use_container_width=True, hide_index=True)


# ============================================================
# PAGE 4 — MANAGE INVESTMENTS
# ============================================================
elif page == "Manage Investments":
    st.header("Manage Investments")
    st.caption("Add this month's balances, and add or remove tracked accounts. "
               "Entries are saved alongside the app and merged with your Excel history — "
               "your spreadsheet is never modified.")

    accounts = d.get_active_accounts()
    nws = d.get_net_worth_snapshots()
    latest_date = nws["date"].max()
    latest_values = nws[nws["date"] == latest_date].set_index("account")["amount"].to_dict()

    # --- Add a monthly snapshot ---
    st.subheader("Add a Monthly Snapshot")
    with st.form("add_snapshot_form"):
        snapshot_date = st.date_input("Snapshot date", value=pd.Timestamp.today())

        st.markdown("**Enter the current balance for each account:**")
        amounts = {}
        cols = st.columns(2)
        for i, acc in enumerate(accounts):
            default = float(latest_values.get(acc, 0.0))
            with cols[i % 2]:
                amounts[acc] = st.number_input(
                    f"{acc} — balance", value=default, step=10.0, format="%.2f", key=f"amt_{acc}"
                )

        submitted = st.form_submit_button("Save Snapshot", type="primary")
        if submitted:
            ok, msg = d.add_manual_snapshot(snapshot_date, amounts)
            (st.success if ok else st.warning)(msg)
            if ok:
                st.cache_data.clear()
                st.rerun()

    # --- Manual entries log (collapsed by default) ---
    manual = d.load_manual_snapshots()
    with st.expander(f"Manually Added Snapshots ({len(manual['date'].unique()) if not manual.empty else 0})", expanded=False):
        if manual.empty:
            st.info("No manual snapshots added yet — use the form above to add your first one.")
        else:
            manual_pivot = manual.pivot_table(index="date", columns="account", values="amount", aggfunc="sum")
            manual_pivot.index = manual_pivot.index.strftime("%d %b %Y")
            st.dataframe(manual_pivot.style.format("£{:,.0f}"), use_container_width=True)

            dates_available = sorted(manual["date"].dt.strftime("%Y-%m-%d").unique(), reverse=True)
            with st.form("delete_snapshot_form"):
                del_date = st.selectbox("Delete a manual snapshot by date", options=dates_available)
                del_submitted = st.form_submit_button("Delete Snapshot", type="secondary")
                if del_submitted:
                    d.delete_manual_snapshot(del_date)
                    st.success(f"Deleted manual snapshot for {del_date}.")
                    st.rerun()

    st.divider()

    # --- Add / remove tracked accounts ---
    st.subheader("Tracked Accounts")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Add a new account**")
        with st.form("add_account_form", clear_on_submit=True):
            new_account = st.text_input("Account name", placeholder="e.g. Trading 212")
            add_submitted = st.form_submit_button("Add Account")
            if add_submitted:
                ok, msg = d.add_account(new_account)
                (st.success if ok else st.warning)(msg)
                if ok:
                    st.rerun()

    with col2:
        st.markdown("**Remove an account**")
        with st.form("remove_account_form"):
            to_remove = st.selectbox("Select account", options=accounts)
            remove_submitted = st.form_submit_button("Remove Account")
            if remove_submitted:
                ok, msg = d.remove_account(to_remove)
                (st.success if ok else st.warning)(msg)
                if ok:
                    st.rerun()

    st.caption("Removing an account stops it appearing in future snapshot forms — "
               "historical data for it is preserved in your charts.")

    st.divider()

    # --- Total invested per account ---
    st.subheader("Total Invested per Account")
    st.caption("Running total contributed to each account — used for the Invested vs Current Value table.")
    invested_df = d.load_invested_amounts()
    # Ensure all active accounts appear
    existing_invested = dict(zip(invested_df["account"], invested_df["invested"]))
    invested_display = pd.DataFrame([
        {"account": acc, "invested": float(existing_invested.get(acc, 0.0))}
        for acc in accounts
    ])
    edited_invested = st.data_editor(
        invested_display,
        column_config={
            "account":  st.column_config.TextColumn("Account", disabled=True),
            "invested": st.column_config.NumberColumn("Total Invested (£)", min_value=0.0, step=10.0, format="£%.2f"),
        },
        use_container_width=True,
        hide_index=True,
        key="invested_editor",
    )
    if st.button("Save Invested Amounts", type="primary"):
        d.set_all_invested_amounts(edited_invested)
        st.success("Invested amounts updated.")
        st.cache_data.clear()
        st.rerun()


# ============================================================
# PAGE 5 — MANAGE EXPENSES
# ============================================================
elif page == "Manage Expenses":
    st.header("Manage Expenses")

    monthly_expenses = d.get_monthly_expenses()

    # --- One-off expenses ---
    st.subheader("One-off Expenses")
    st.caption("Add, edit, or delete rows inline, then hit Save.")

    oo = d.get_one_off_expenses()
    ONE_OFF_CATEGORIES = sorted(set(monthly_expenses["category"]) | set(oo["category"].dropna().unique()))

    edited_oo = st.data_editor(
        oo,
        column_config={
            "reason":   st.column_config.TextColumn("Reason", required=True),
            "category": st.column_config.SelectboxColumn("Category", options=ONE_OFF_CATEGORIES, required=True),
            "date":     st.column_config.DateColumn("Date", required=True),
            "amount":   st.column_config.NumberColumn("Amount (£)", min_value=0.0, step=10.0, format="£%.2f", required=True),
            "note":     st.column_config.TextColumn("Note"),
        },
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="one_off_editor",
    )
    if st.button("Save One-off Expenses", type="primary"):
        d.set_one_off_expenses(edited_oo)
        st.success("One-off expenses saved.")
        st.cache_data.clear()
        st.rerun()

    st.divider()

    # --- Recurring monthly expenses ---
    st.subheader("Recurring Monthly Expenses")
    st.caption("Edit names and amounts in-line, add or remove rows, then hit Save. "
               "Updates immediately flow through to the Cash Flow and Projection charts.")

    edited_monthly_expenses = st.data_editor(
        monthly_expenses,
        column_config={
            "category": st.column_config.TextColumn("Name", required=True),
            "amount": st.column_config.NumberColumn("Amount (£)", min_value=0.0, step=10.0, format="£%.2f", required=True),
        },
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="monthly_expenses_editor",
    )
    if st.button("Save Recurring Expenses", type="primary"):
        ok, msg = d.set_monthly_expenses(edited_monthly_expenses)
        (st.success if ok else st.warning)(msg)
        if ok:
            st.cache_data.clear()
            st.rerun()
