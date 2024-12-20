import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import altair as alt
import textwrap

def fetch(ticker: str, start: str, end: str) -> pd.DataFrame:
    data = yf.download(ticker, start=start, end=end, auto_adjust=True)
    data.reset_index(inplace=True)
    data.columns = data.columns.get_level_values(0)
    return data

def process_holding(data: pd.DataFrame, holding_period: int) -> pd.DataFrame:
    data["Sell Date"] = data["Date"] + timedelta(days=holding_period)
    data["Sell Price"] = data["Close"].shift(-holding_period)
    data["Previous Close"] = data["Close"].shift(1)
    
    data["Return %"] = ((data["Close"].shift(-holding_period) - data["Close"]) / data["Close"]) * 100
    data.dropna(subset=["Return %"], inplace=True)

    return data

def calculate_data(data: pd.DataFrame, volume_threshold: int, change_threshold: int) -> pd.DataFrame:
    data["Avg Vol (Last 20d)"] = data["Volume"].rolling(window=20).mean()
    data["Vol Breakout"] = (
        (data["Volume"] > (data["Avg Vol (Last 20d)"] * (volume_threshold / 100))) &
        (data["Close"].pct_change() >= (change_threshold / 100))
    )
    data = data[data["Vol Breakout"] == True]
    data = data.reset_index(drop=True)
    return data

def generate_charts(data: pd.DataFrame, title: str, mean_return: float):
    data['index'] = data.index
    bar_chart = alt.Chart(data).mark_bar().encode(
        x=alt.X(
            "index:O",
            title="Trade (Chronological Order)",
            axis=alt.Axis(labelAngle=360),
        ),
        y=alt.Y(
            "Return %:Q",
            title="Return %",
        ),
        color=alt.condition(
            alt.datum["Return %"] > 0,
            alt.value("green"),
            alt.value("red")
        ),
        tooltip=[
            "Date:T",
            "Close:Q",
            "Sell Date:T",
            "Sell Price:Q",
            "Return %:Q",
        ]
    ).properties(
        title=title,
        height=700
    )

    mean_line = alt.Chart(pd.DataFrame({
        "mean": mean_return,
        "Legend": ["Mean Return %"]
    })).mark_rule(strokeDash=[10,20], strokeWidth=2).encode(
        y=alt.Y("mean:Q"),
        color=alt.Color("Legend:N", scale=alt.Scale(domain=["Mean Return %"], range=["blue"]))
    )
    mean_text = alt.Chart(pd.DataFrame({'mean': [mean_return]})).mark_text(
        align="center",
        baseline="top",
        fontSize=24,
        fill="blue",
        fontWeight="bold"
    ).encode(
        y=alt.value(20),
        text=alt.value(f"Mean Return: {mean_return:.2f}%"),
        tooltip=["mean:Q"]
    )
    st.altair_chart(
        alt.layer(bar_chart, mean_line, mean_text).configure_view(
            stroke="black",
            strokeWidth=2.0
        ), 
    use_container_width=True)
    
def main():
    st.set_page_config(layout="wide")
    st.title("Quanta Strategy Analysis")
    
    st.sidebar.header("Enter Your Information")
    ticker = st.sidebar.text_input("Stock Ticker", "BTC-USD").upper()
    volume_threshold = st.sidebar.number_input(
        "Volume Threshold (X%)", 
        min_value=1.0, 
        value=200.0,
        step=10.0
    )
    change_threshold = st.sidebar.number_input(
        "Change Threshold (Y%)", 
        min_value=0.0,
        value=2.0,
        step=0.5
    )
    holding_period = st.sidebar.number_input(
      "Holding Period (Z)", 
      min_value=1, 
      value=10, 
      step=1
    )

    start_date = st.sidebar.date_input(
        "Start Date", datetime.today() - timedelta(days=(365 * 7) - holding_period),
        max_value=(datetime.today() - timedelta(days=holding_period)))
    end_date = st.sidebar.date_input(
      "End Date", datetime.today() - timedelta(days=holding_period),
      max_value=(datetime.today() - timedelta(days=holding_period))
    )
    
    start_date = start_date - timedelta(days=holding_period)
    
    with st.spinner("Loading..."):
        data = fetch(ticker, start_date, end_date + timedelta(days=holding_period))

        data = process_holding(data, holding_period)
        data = data[data["Date"] <= pd.Timestamp(end_date)]
        data = calculate_data(data, volume_threshold, change_threshold)

        if data.empty: 
            st.error("No trades found.")
            return

        st.dataframe(data, use_container_width=True, height=300)

        mean_return = data['Return %'].mean()
        title = textwrap.dedent(f"""
            {ticker} |
            start_date: {start_date} |
            end_date: {end_date} |
            holding_days: {holding_period} |
            volume_threshold%: {volume_threshold} |
            change_threshold%: {change_threshold} |
            Total Trades: {len(data)} |
            Win Rate: {len(data[data['Return %'] > 0])  / len(data) * 100:.2f}% |
            Mean return: {mean_return:.2f}%
        """)
        generate_charts(data, title, mean_return)
        st.sidebar.download_button("Download CSV", data.to_csv(), ticker + "-report.csv", "text/csv")

if __name__ == "__main__":
    main()
