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

PALETTE_NAME = d.get_palette_name()
PALETTE = PALETTES.get(PALETTE_NAME, PALETTES["Pastel"])


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
    st.title("Finance Dashboard")
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
    st.metric("Monthly Expenses", f"£{d.MONTHLY_EXPENSES['amount'].sum():,}")

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
        template="plotly_dark",
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
            showlegend=False, height=320, template="plotly_dark",
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

    show_history = st.toggle("Show historical months", value=False)
    if not show_history:
        current_month = pd.Timestamp.today().to_period("M").to_timestamp()
        cf = cf[cf["date"] >= current_month].copy()

    col1, col2, col3 = st.columns(3)
    col1.metric("Monthly Income", f"£{d.MONTHLY_INCOME:,}")
    col2.metric("Avg Monthly Expenses", f"£{d.MONTHLY_EXPENSES['amount'].sum():,}")
    surplus = d.MONTHLY_INCOME - d.MONTHLY_EXPENSES["amount"].sum()
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
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=cf["date"], y=cf["monthly_expenses"],
        name="Recurring Expenses",
        mode="lines",
        stackgroup="expenses",
        line=dict(width=0.5, color="#4C72B0"),
        fillcolor="#4C72B0",
        hovertemplate="Recurring: £%{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=cf["date"], y=cf["one_off_expenses"],
        name="One-off Expenses",
        mode="lines",
        stackgroup="expenses",
        line=dict(width=0.5, color="#C44E52"),
        fillcolor="#C44E52",
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
        line=dict(color="#51cf66", width=2),
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
        template="plotly_dark",
        margin=dict(t=40, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)

    # One-off expense timeline
    col_hdr, col_btn = st.columns([4, 1])
    col_hdr.subheader("Upcoming One-off Expenses")
    col_btn.button("+ Add / edit", on_click=_go_to, args=("Manage Expenses",), use_container_width=True, type="primary")
    oo = d.get_one_off_expenses().copy()
    oo_monthly = oo.groupby(["date", "category"])["amount"].sum().reset_index()

    fig3 = px.bar(
        oo_monthly, x="date", y="amount", color="category",
        color_discrete_map=color_map(oo_monthly["category"]),
        labels={"amount": "£", "date": "", "category": "Category"},
        title="One-off Expenses by Month",
    )
    fig3.update_traces(width=1000 * 60 * 60 * 24 * 25)  # ~25 days, so bars don't bleed into neighbouring months
    fig3.update_layout(
        template="plotly_dark", height=300,
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
        d.MONTHLY_EXPENSES, values="amount", names="category",
        hole=0.4, title=f"Monthly Spend Breakdown — Total £{d.MONTHLY_EXPENSES['amount'].sum():,}",
    )
    fig4.update_traces(textposition="outside", textinfo="label+percent")
    fig4.update_layout(
        showlegend=False, template="plotly_dark", height=340,
        margin=dict(t=40, b=10, l=10, r=10),
    )
    col_a, col_b = st.columns([1, 1])
    with col_a:
        st.plotly_chart(fig4, use_container_width=True)
    with col_b:
        exp_df = d.MONTHLY_EXPENSES.copy()
        exp_df["amount"] = exp_df["amount"].map(lambda x: f"£{x:,.0f}")
        exp_df.columns = ["Category", "Monthly (£)"]
        st.dataframe(exp_df, use_container_width=True, hide_index=True)


# ============================================================
# PAGE 3 — PROJECTION
# ============================================================
elif page == "Projection":
    st.header("Projection")

    proj = d.get_projections()
    actual_known = proj.dropna(subset=["actual"])
    latest_actual = actual_known.iloc[-1] if len(actual_known) else None

    if latest_actual is not None:
        col1, col2, col3 = st.columns(3)
        col1.metric("Latest Actual Net Worth",    f"£{latest_actual['actual']:,.0f}")
        col2.metric("Projection for Same Month",  f"£{latest_actual['projected']:,.0f}")
        variance = latest_actual["actual"] - latest_actual["projected"]
        col3.metric("Variance", f"£{variance:,.0f}", delta=f"{'above' if variance >= 0 else 'below'} projection")

    st.divider()

    fig = go.Figure()

    # Projection line (full range)
    fig.add_trace(go.Scatter(
        x=proj["date"], y=proj["projected"],
        name="Projected",
        mode="lines",
        line=dict(color="#4C72B0", width=2, dash="dot"),
        hovertemplate="Projected: £%{y:,.0f}<extra></extra>",
    ))

    # Actual line (where we have data)
    fig.add_trace(go.Scatter(
        x=actual_known["date"], y=actual_known["actual"],
        name="Actual",
        mode="lines+markers",
        line=dict(color="#51cf66", width=2.5),
        marker=dict(size=7),
        hovertemplate="Actual: £%{y:,.0f}<extra></extra>",
    ))

    # Variance fill between projected and actual
    merged = proj.dropna(subset=["actual"]).copy()
    fig.add_trace(go.Scatter(
        x=pd.concat([merged["date"], merged["date"][::-1]]),
        y=pd.concat([merged["projected"], merged["actual"][::-1]]),
        fill="toself",
        fillcolor="rgba(200,80,80,0.15)",
        line=dict(color="rgba(0,0,0,0)"),
        name="Gap",
        hoverinfo="skip",
        showlegend=True,
    ))

    # Projection start marker
    if latest_actual is not None:
        fig.add_vline(
            x=latest_actual["date"].timestamp() * 1000,
            line_dash="dash", line_color="white", opacity=0.3,
            annotation_text="→ forecast", annotation_position="top right",
        )

    fig.update_layout(
        title="Net Worth: Projected vs Actual",
        xaxis_title=None,
        yaxis_title="Net Worth (£)",
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.12),
        height=430,
        template="plotly_dark",
        margin=dict(t=40, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Monthly variance table
    st.subheader("Month-by-Month Variance")
    tbl = proj.dropna(subset=["actual"]).copy()
    tbl["variance"] = tbl["actual"] - tbl["projected"]
    tbl["variance_%"] = (tbl["variance"] / tbl["projected"] * 100).round(1)
    tbl["date"] = tbl["date"].dt.strftime("%b %Y")

    def color_var(val):
        try:
            num = float(str(val).replace("£","").replace(",","").replace("%",""))
            return "color: #ff6b6b" if num < 0 else "color: #51cf66"
        except Exception:
            return ""

    styled = (
        tbl.rename(columns={
            "date": "Month", "projected": "Projected", "actual": "Actual",
            "variance": "Variance (£)", "variance_%": "Variance (%)",
        })
        .style
        .format({
            "Projected": "£{:,.0f}", "Actual": "£{:,.0f}",
            "Variance (£)": "£{:,.0f}", "Variance (%)": "{:.1f}%",
        })
        .map(color_var, subset=["Variance (£)", "Variance (%)"])
    )
    st.dataframe(styled, use_container_width=True, hide_index=True)


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

        st.markdown("**Enter the current balance for each account, and any new money paid in this month:**")
        amounts = {}
        contributions = {}
        cols = st.columns(2)
        for i, acc in enumerate(accounts):
            default = float(latest_values.get(acc, 0.0))
            with cols[i % 2]:
                amounts[acc] = st.number_input(
                    f"{acc} — balance", value=default, step=10.0, format="%.2f", key=f"amt_{acc}"
                )
                contributions[acc] = st.number_input(
                    f"{acc} — contribution this month", value=0.0, step=10.0, format="%.2f", key=f"contrib_{acc}"
                )

        submitted = st.form_submit_button("Save Snapshot", type="primary")
        if submitted:
            ok, msg = d.add_manual_snapshot(snapshot_date, amounts)
            (st.success if ok else st.warning)(msg)
            if ok:
                d.add_contributions(contributions)
                st.cache_data.clear()
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

    # --- Set total invested per account ---
    st.subheader("Total Invested per Account")
    st.caption("The running total of money you've put into each account. "
               "Used for the 'Invested vs Current Value' table on the Net Worth page. "
               "It updates automatically from the contributions entered above — "
               "use this form to set or correct the starting total.")
    invested_df = d.load_invested_amounts()
    invested_values = dict(zip(invested_df["account"], invested_df["invested"]))
    with st.form("set_invested_form"):
        cols = st.columns(2)
        new_invested = {}
        for i, acc in enumerate(accounts):
            with cols[i % 2]:
                new_invested[acc] = st.number_input(
                    acc, value=float(invested_values.get(acc, 0.0)), step=10.0, format="%.2f", key=f"invested_{acc}"
                )
        invested_submitted = st.form_submit_button("Save Invested Amounts", type="primary")
        if invested_submitted:
            for acc, val in new_invested.items():
                d.set_invested_amount(acc, val)
            st.success("Invested amounts updated.")
            st.cache_data.clear()
            st.rerun()

    st.divider()

    # --- Manual entries log ---
    st.subheader("Manually Added Snapshots")
    manual = d.load_manual_snapshots()
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


# ============================================================
# PAGE 5 — MANAGE EXPENSES
# ============================================================
elif page == "Manage Expenses":
    st.header("Manage Expenses")
    st.caption("Add, edit, or delete upcoming one-off expenses (holidays, weddings, car costs, house costs, etc.). ")

    oo = d.get_one_off_expenses()
    ONE_OFF_CATEGORIES = sorted(set(d.MONTHLY_EXPENSES["category"]) | set(oo["category"].dropna().unique()))

    # --- Add a new one-off expense ---
    st.subheader("Add a New One-off Expense")
    with st.form("add_one_off_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            new_reason = st.text_input("Reason", placeholder="e.g. Friend's wedding")
            new_category = st.selectbox("Category", options=ONE_OFF_CATEGORIES)
            new_date = st.date_input("Month", value=pd.Timestamp.today())
        with c2:
            new_amount = st.number_input("Amount (£)", min_value=0.0, step=10.0, format="%.2f")
            new_note = st.text_input("Note (optional)")
        add_oo_submitted = st.form_submit_button("Add Expense", type="primary")
        if add_oo_submitted:
            if not new_reason.strip():
                st.warning("Please enter a reason.")
            else:
                d.add_one_off_expense(new_reason.strip(), new_category,
                                      new_date.replace(day=1), new_amount, new_note.strip() or None)
                st.success(f'Added "{new_reason.strip()}" — £{new_amount:,.0f} in {new_date.strftime("%b %Y")}.')
                st.cache_data.clear()
                st.rerun()

    st.divider()

    # --- Edit or delete an existing expense ---
    st.subheader("Edit or Delete an Existing Expense")
    if oo.empty:
        st.info("No one-off expenses yet — add one above.")
    else:
        options = {
            idx: f'{row["reason"]} — £{row["amount"]:,.0f} ({row["date"].strftime("%b %Y")})'
            for idx, row in oo.iterrows()
        }
        selected_id = st.selectbox(
            "Select an expense", options=list(options.keys()),
            format_func=lambda i: options[i], key="edit_oo_select",
        )
        sel = oo.loc[selected_id]

        with st.form("edit_one_off_form"):
            c1, c2 = st.columns(2)
            with c1:
                edit_reason = st.text_input("Reason", value=sel["reason"])
                cat_idx = ONE_OFF_CATEGORIES.index(sel["category"]) if sel["category"] in ONE_OFF_CATEGORIES else 0
                edit_category = st.selectbox("Category", options=ONE_OFF_CATEGORIES, index=cat_idx)
                edit_date = st.date_input("Month", value=sel["date"].to_pydatetime())
            with c2:
                edit_amount = st.number_input("Amount (£)", min_value=0.0, step=10.0,
                                               format="%.2f", value=float(sel["amount"]))
                edit_note = st.text_input("Note (optional)", value=sel["note"] or "")

            bcol1, bcol2 = st.columns(2)
            save_clicked = bcol1.form_submit_button("Save Changes", type="primary")
            delete_clicked = bcol2.form_submit_button("Delete Expense")

            if save_clicked:
                d.update_one_off_expense(selected_id, edit_reason.strip(), edit_category,
                                         edit_date.replace(day=1), edit_amount, edit_note.strip() or None)
                st.success("Expense updated.")
                st.cache_data.clear()
                st.rerun()
            if delete_clicked:
                d.delete_one_off_expense(selected_id)
                st.success(f'Deleted "{sel["reason"]}".')
                st.cache_data.clear()
                st.rerun()

    st.divider()

    # --- Full list ---
    st.subheader("All One-off Expenses")
    display = oo.copy()
    display["date"] = display["date"].dt.strftime("%b %Y")
    display["amount"] = display["amount"].map(lambda x: f"£{x:,.0f}")
    display.columns = ["Reason", "Category", "Month", "Amount", "Note"]
    st.dataframe(display, use_container_width=True, hide_index=True)
