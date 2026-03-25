import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# ==========================================
# 1. PAGE CONFIGURATION & HEADER
# ==========================================
st.set_page_config(page_title="NSE Quant Dashboard", layout="wide")

st.title("📈 NSE Stock Market Analytics & Momentum Strategy")
# 
st.markdown("**Developed by: Paresh Kapoor | Aspiring Data Scientist & Quant**")
st.markdown("---")

# ==========================================
# 2. SIDEBAR CONFIGURATION
# ==========================================
st.sidebar.header("⚙️ Dashboard Parameters")

# Date Range Selector
start_date = st.sidebar.date_input("Start Date", pd.to_datetime("2019-01-01"))
end_date = st.sidebar.date_input("End Date", pd.to_datetime("2024-01-01"))

# Stock Selector
available_stocks = [
    'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS',
    'HINDUNILVR.NS', 'ITC.NS', 'SBIN.NS', 'BHARTIARTL.NS', 'LT.NS'
]
selected_stocks = st.sidebar.multiselect("Select Stocks for Universe", available_stocks, default=available_stocks[:5])

# ==========================================
# 3. DATA LOADING (WITH CACHING)
# ==========================================
@st.cache_data
def load_data(tickers, start, end):
    """Downloads data from yfinance and caches it for speed."""
    if not tickers:
        return pd.DataFrame()
    
    # Always include NIFTY 50 benchmark
    tickers_to_download = tickers + ['^NSEI']
    data = yf.download(tickers_to_download, start=start, end=end)['Close']
    return data.ffill()

# Fetch the data based on sidebar inputs
if selected_stocks:
    df_close = load_data(selected_stocks, start_date, end_date)
    daily_returns = df_close.pct_change().dropna()
    
    # Separate Strategy Universe vs Benchmark
    stock_returns = daily_returns.drop(columns=['^NSEI'])
    nifty_returns = daily_returns['^NSEI']

    # ==========================================
    # 4. TABS SETUP
    # ==========================================
    tab1, tab2, tab3 = st.tabs(["📈 Price Performance", "🛡️ Risk Metrics & Backtest", "🔥 Correlation Heatmap"])

    # --- TAB 1: PRICE PERFORMANCE ---
    with tab1:
        st.subheader("Normalized Price Performance (Base 100)")
        st.markdown("This chart normalizes all selected stocks to a base value of 100 on the start date, allowing for an 'apples-to-apples' growth comparison.")
        
        normalized_df = (df_close.drop(columns=['^NSEI']) / df_close.drop(columns=['^NSEI']).iloc[0]) * 100
        # Streamlit's native interactive line chart
        st.line_chart(normalized_df)

    # --- TAB 2: RISK METRICS & BACKTEST ---
    with tab2:
        st.subheader("Top 3 Cross-Sectional Momentum vs NIFTY 50")
        
        # Recalculate Strategy Dynamically based on selected dates/stocks
        stock_prices = df_close.drop(columns=['^NSEI'])
        momentum_63d = stock_prices.pct_change(63)
        rebalance_dates = stock_prices.resample('BME').last().index
        strategy_returns = pd.Series(0.0, index=daily_returns.index)

        for i in range(3, len(rebalance_dates) - 1):
            decision_date = rebalance_dates[i]
            if decision_date not in momentum_63d.index:
                decision_date = momentum_63d.index[momentum_63d.index <= decision_date][-1]
            
            current_momentum = momentum_63d.loc[decision_date]
            # Pick top 3 (or less if user selected less than 3 stocks)
            top_n = min(3, len(selected_stocks))
            top_stocks = current_momentum.nlargest(top_n).index.tolist()
            
            next_rebalance_date = rebalance_dates[i+1]
            holding_period = (daily_returns.index > decision_date) & (daily_returns.index <= next_rebalance_date)
            
            portfolio_returns = stock_returns.loc[holding_period, top_stocks]
            strategy_returns.loc[holding_period] = portfolio_returns.mean(axis=1)

        # Calculate Growth
        cumulative_strategy = (1 + strategy_returns).cumprod() * 100
        cumulative_nifty = (1 + nifty_returns).cumprod() * 100

        # Plotly/Streamlit native columns for metrics
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Strategy Cumulative Growth**")
            st.line_chart(cumulative_strategy, color="#1f77b4")
        with col2:
            st.markdown("**NIFTY 50 Benchmark Growth**")
            st.line_chart(cumulative_nifty, color="#7f7f7f")

        # Quick Metrics Table
        st.markdown("### 📊 Performance Summary")
        
      def calc_cagr(ret):
            # Safety check: if there is no data, return 0
            if len(ret) == 0: 
                return 0.0
            return ((1 + ret).cumprod().iloc[-1] ** (252 / len(ret))) - 1
            
        def calc_sharpe(ret):
            # Safety check: prevent division by zero if volatility is 0 or data is empty
            if len(ret) == 0 or ret.std() == 0: 
                return 0.0
            return ((ret.mean() * 252) - 0.065) / (ret.std() * np.sqrt(252))sqrt(252))

        metrics_data = {
            "Metric": ["CAGR", "Sharpe Ratio (6.5% Risk Free)"],
            "Momentum Strategy": [f"{calc_cagr(strategy_returns)*100:.2f}%", f"{calc_sharpe(strategy_returns):.2f}"],
            "NIFTY 50 Benchmark": [f"{calc_cagr(nifty_returns)*100:.2f}%", f"{calc_sharpe(nifty_returns):.2f}"]
        }
        st.table(pd.DataFrame(metrics_data).set_index("Metric"))

    # --- TAB 3: CORRELATION HEATMAP ---
    with tab3:
        st.subheader("Daily Returns Correlation Heatmap")
        st.markdown("Darker red means stocks move together. Darker blue means they move oppositely.")
        
        fig, ax = plt.subplots(figsize=(10, 8))
        sns.heatmap(stock_returns.corr(), annot=True, cmap='coolwarm', fmt=".2f", linewidths=0.5, ax=ax)
        st.pyplot(fig)

else:
    st.warning("Please select at least one stock from the sidebar to view the dashboard.")
