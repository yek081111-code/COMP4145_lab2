from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from trading_strategy import (
    calculate_moving_averages,
    get_stock_data,
    identify_golden_cross,
    implement_strategy,
)

st.set_page_config(page_title="Trading Strategy Results", layout="wide")


@st.cache_data(ttl=3600)
def load_results() -> tuple[pd.DataFrame, pd.DataFrame]:
    data = get_stock_data("MSFT")
    if data.empty:
        raise RuntimeError("No stock data was returned for MSFT.")

    data = calculate_moving_averages(data)
    data = identify_golden_cross(data)
    positions = implement_strategy(data)
    return data, positions


def format_date(value: object) -> str:
    if pd.isna(value):
        return "N/A"
    return pd.Timestamp(value).strftime("%Y-%m-%d")


def show_price_chart(data: pd.DataFrame, positions: pd.DataFrame) -> None:
    st.title("MSFT Price & Trading Signals")
    st.caption("Five-year daily closing prices with 50-day and 200-day moving averages.")

    chart = go.Figure()
    chart.add_trace(
        go.Scatter(
            x=data.index,
            y=data["Close"],
            name="Stock price",
            mode="lines",
            line={"color": "#2563eb", "width": 1.8},
        )
    )
    chart.add_trace(
        go.Scatter(
            x=data.index,
            y=data["MA50"],
            name="Short-term MA (50 days)",
            mode="lines",
            line={"color": "#f59e0b", "width": 1.5},
        )
    )
    chart.add_trace(
        go.Scatter(
            x=data.index,
            y=data["MA200"],
            name="Long-term MA (200 days)",
            mode="lines",
            line={"color": "#8b5cf6", "width": 1.5},
        )
    )

    if not positions.empty:
        buys = positions.dropna(subset=["BuyDate", "BuyPrice"])
        sells = positions.dropna(subset=["SellDate", "SellPrice"])
        chart.add_trace(
            go.Scatter(
                x=buys["BuyDate"],
                y=buys["BuyPrice"],
                name="Buy",
                mode="markers",
                marker={"color": "#16a34a", "size": 11, "symbol": "triangle-up"},
            )
        )
        chart.add_trace(
            go.Scatter(
                x=sells["SellDate"],
                y=sells["SellPrice"],
                name="Sell",
                mode="markers",
                marker={"color": "#dc2626", "size": 11, "symbol": "triangle-down"},
            )
        )

    chart.update_layout(
        height=620,
        hovermode="x unified",
        xaxis_title="Date",
        yaxis_title="Price (USD)",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
        margin={"l": 20, "r": 20, "t": 45, "b": 20},
    )
    st.plotly_chart(chart, use_container_width=True)


def show_statistics(positions: pd.DataFrame) -> None:
    st.title("Overall Trade Statistics")

    if positions.empty:
        st.info("No trading signals were detected for this period.")
        return

    completed = positions.dropna(subset=["SellPrice", "ProfitPct"])
    incomplete_count = len(positions) - len(completed)
    wins = completed[completed["ProfitPct"] > 0]
    losses = completed[completed["ProfitPct"] <= 0]
    win_rate = len(wins) / len(completed) * 100 if not completed.empty else 0
    average_profit = completed["ProfitPct"].mean() if not completed.empty else 0
    average_holding = completed["HoldingDays"].mean() if not completed.empty else 0

    first_row = st.columns(4)
    first_row[0].metric("Total trades", len(positions))
    first_row[1].metric("Completed trades", len(completed))
    first_row[2].metric("Win rate", f"{win_rate:.2f}%")
    first_row[3].metric("Average profit", f"{average_profit:.2f}%")

    second_row = st.columns(3)
    second_row[0].metric("Winning trades", len(wins))
    second_row[1].metric("Losing trades", len(losses))
    second_row[2].metric(
        "Average holding period",
        f"{average_holding:.1f} days" if not completed.empty else "N/A",
    )
    if incomplete_count:
        st.caption(
            f"{incomplete_count} trade(s) have no valid sell price yet and are excluded "
            "from completed-trade performance metrics."
        )


def show_trade_details(positions: pd.DataFrame) -> None:
    st.title("Detailed Trades")
    if positions.empty:
        st.info("No trading signals were detected for this period.")
        return

    display = positions.copy()
    display["BuyDate"] = display["BuyDate"].map(format_date)
    display["SellDate"] = display["SellDate"].map(format_date)
    display = display.rename(
        columns={
            "BuyDate": "Buy date",
            "BuyPrice": "Buy price (USD)",
            "SellDate": "Sell date",
            "SellPrice": "Sell price (USD)",
            "HoldingDays": "Holding days",
            "ProfitPct": "Profit (%)",
            "SellReason": "Sell reason",
        }
    )
    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Buy price (USD)": st.column_config.NumberColumn(format="$%.2f"),
            "Sell price (USD)": st.column_config.NumberColumn(format="$%.2f"),
            "Profit (%)": st.column_config.NumberColumn(format="%.2f%%"),
        },
    )


st.sidebar.title("Trading Strategy")
page = st.sidebar.radio(
    "Navigate",
    ["Price chart", "Trade statistics", "Detailed trades"],
)

stock_data, trade_positions = load_results()

if page == "Price chart":
    show_price_chart(stock_data, trade_positions)
elif page == "Trade statistics":
    show_statistics(trade_positions)
else:
    show_trade_details(trade_positions)
