import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from io import StringIO

def fetch(ticker: str, start: str, end: str) -> pd.DataFrame:
    data = yf.download(ticker, start=start, end=end, auto_adjust=True)
    data.reset_index(inplace=True)
    data.columns = data.columns.get_level_values(0)
    return data
  

def main():
    st.title("Quanta Strategy Analysis")
    
    st.sidebar.header("Enter Your Information")
    ticker = st.sidebar.text_input("Stock Ticker", "NVDA").upper()
    volume_threshold = st.sidebar.number_input(
        "Volume Threshold (X%)", 
        min_value=1.0, 
        value=200.0,
        step=20.0
    )
    price_threshold = st.sidebar.number_input(
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

    start_date = st.sidebar.date_input("Start Date", datetime.today() - timedelta(days=365 - holding_period))
    end_date = st.sidebar.date_input(
      "End Date", datetime.today() - timedelta(days=holding_period),
      max_value=(datetime.today() - timedelta(days=holding_period))
    )
    
    start_date = start_date - timedelta(days=holding_period)
    
    if st.sidebar.button("Generate Report"):
        with st.spinner("Fetching and processing data..."):
            data = fetch(ticker, start_date, end_date + timedelta(days=holding_period))
            data["Profit ($)"] = (data["Close"].shift(-holding_period) - data["Close"]).round(2)
            data = data[data["Date"] <= pd.Timestamp(end_date)]

            data["Avg Vol (Last 20d)"] = data["Volume"].rolling(window=20).mean()
            data["Vol Breakout"] = (data["Volume"] > (data["Avg Vol (Last 20d)"] * (volume_threshold / 100))) & (data["Close"].pct_change() > (price_threshold / 100))
            data = data[data["Vol Breakout"] == True]

            data = data[["Date", "Close", "Volume", "Avg Vol (Last 20d)", "Vol Breakout", "Profit ($)"]]

            st.dataframe(data, use_container_width=True)
            st.download_button("Download CSV", data.to_csv(), ticker + "-report.csv", "text/csv")

if __name__ == "__main__":
    main()
