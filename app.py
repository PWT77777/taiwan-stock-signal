import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import json
import os
from datetime import datetime, timedelta

# 設定 yfinance 快取目錄至 /tmp，避免 Streamlit Cloud 因權限問題崩潰
try:
    yf.set_tz_cache_location("/tmp")
except Exception:
    pass

# Set page configuration - Responsive & Dark Mode styling
st.set_page_config(
    page_title="台股紅綠燈綜合量化看盤系統",
    page_icon="🟢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Premium CSS Injection
st.markdown("""
<style>
    /* Dark Theme Background & Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Noto+Sans+TC:wght@300;400;700&display=swap');
    
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #0f172a;
        color: #e2e8f0;
        font-family: 'Outfit', 'Noto Sans TC', sans-serif;
    }
    
    [data-testid="stSidebar"] {
        background-color: #1e293b;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    /* Neon Status Indicator Cards */
    .neon-card {
        border-radius: 16px;
        padding: 24px;
        text-align: center;
        border: 1px solid;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        margin-bottom: 24px;
    }
    .neon-green {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(16, 185, 129, 0.03) 100%);
        border-color: rgba(16, 185, 129, 0.45);
        box-shadow: 0 0 30px rgba(16, 185, 129, 0.25);
    }
    .neon-red {
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(239, 68, 68, 0.03) 100%);
        border-color: rgba(239, 68, 68, 0.45);
        box-shadow: 0 0 30px rgba(239, 68, 68, 0.25);
    }
    .neon-yellow {
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.15) 0%, rgba(245, 158, 11, 0.03) 100%);
        border-color: rgba(245, 158, 11, 0.45);
        box-shadow: 0 0 30px rgba(245, 158, 11, 0.25);
    }
    
    .neon-title {
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: 2px;
        margin-bottom: 8px;
        text-shadow: 0 0 10px rgba(255, 255, 255, 0.2);
    }
    
    .neon-subtitle {
        font-size: 1.1rem;
        color: #94a3b8;
        font-weight: 400;
    }
    
    /* Performance Stats Cards */
    .metric-container {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 16px;
        margin-bottom: 20px;
    }
    
    .metric-card {
        background-color: #1e293b;
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #f8fafc;
        margin-bottom: 4px;
    }
    
    .metric-label {
        font-size: 0.85rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Colorful tables */
    .factor-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 10px;
        font-size: 0.95rem;
    }
    
    .factor-table th {
        background-color: #1e293b;
        color: #94a3b8;
        text-align: left;
        padding: 12px;
        font-weight: 600;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    .factor-table td {
        padding: 12px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    .score-badge {
        padding: 4px 10px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 0.85rem;
        display: inline-block;
        text-align: center;
    }
    
    .badge-pos {
        background-color: rgba(16, 185, 129, 0.15);
        color: #10b981;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    
    .badge-neg {
        background-color: rgba(239, 68, 68, 0.15);
        color: #ef4444;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }
    
    .badge-zero {
        background-color: rgba(148, 163, 184, 0.15);
        color: #94a3b8;
        border: 1px solid rgba(148, 163, 184, 0.3);
    }
    
    /* Footer & details */
    .info-footer {
        color: #64748b;
        font-size: 0.8rem;
        text-align: center;
        margin-top: 40px;
        padding-top: 20px;
        border-top: 1px solid rgba(255, 255, 255, 0.05);
    }
</style>
""", unsafe_allow_html=True)


# --- 1. Load Local Stock List快取 ---
@st.cache_data
def load_stock_list():
    """Loads Taiwan stock codes and names scraped from TWSE/TPEx ISIN pages."""
    json_path = os.path.join(os.path.dirname(__file__), "taiwan_stocks.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    
    # Fallback popular stocks if cache file missing
    return [
        {"code": "2330", "name": "台積電", "market": "TSE", "symbol": "2330.TW"},
        {"code": "2317", "name": "鴻海", "market": "TSE", "symbol": "2317.TW"},
        {"code": "2454", "name": "聯發科", "market": "TSE", "symbol": "2454.TW"},
        {"code": "2308", "name": "台達電", "market": "TSE", "symbol": "2308.TW"},
        {"code": "2881", "name": "富邦金", "market": "TSE", "symbol": "2881.TW"},
        {"code": "8069", "name": "元太", "market": "OTC", "symbol": "8069.TWO"}
    ]

def fetch_stock_price_from_finmind(stock_code, start_date, end_date):
    """Fallback price engine using FinMind API when yfinance is cloud-rate-limited."""
    try:
        url = "https://api.finmindtrade.com/api/v4/data"
        params = {
            "dataset": "TaiwanStockPrice",
            "data_id": stock_code,
            "start_date": start_date,
            "end_date": end_date
        }
        res = requests.get(url, params=params, timeout=15)
        if res.status_code == 200:
            data = res.json().get("data", [])
            if data:
                df = pd.DataFrame(data)
                # Rename columns to match yfinance schema
                df = df.rename(columns={
                    "date": "Date",
                    "open": "Open",
                    "max": "High",
                    "min": "Low",
                    "close": "Close",
                    "Trading_Volume": "Volume"
                })
                # Format Date index
                df['Date'] = pd.to_datetime(df['Date'])
                df.set_index('Date', inplace=True)
                # Ensure correct numeric types
                for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                return df
    except Exception:
        pass
    return pd.DataFrame()

# --- 2. Data Fetching Modules (yfinance & FinMind) ---
@st.cache_data(ttl=3600)  # Cache for 1 hour to respect rate limits
def fetch_stock_price(symbol, start_date, end_date):
    """Fetches historical price data from yfinance with automated fallback to FinMind to solve cloud rate-limits."""
    # Extract numeric stock code (e.g., "2330.TW" -> "2330")
    stock_code = symbol.split(".")[0]
    
    # Engine 1: Try yfinance natively (without session to avoid curl_cffi conflict)
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date, end=end_date, interval="1d")
        if not df.empty and 'Close' in df.columns and len(df) > 5:
            df.index = pd.to_datetime(df.index)
            return df
    except Exception:
        pass
        
    # Engine 2: Fallback to FinMind (100% rate-limit free for Taiwan stocks!)
    try:
        df_fm = fetch_stock_price_from_finmind(stock_code, start_date, end_date)
        if not df_fm.empty:
            st.info("💡 **資料庫自動備援**：yfinance 雲端連線忙碌中，已為您自動切換至備用 FinMind 高速台股資料庫載入數據！")
            return df_fm
    except Exception as e:
        st.error(f"價量數據下載失敗：{str(e)}")
        
    return pd.DataFrame()

@st.cache_data(ttl=3600)  # Cache for 1 hour to respect free rate limits (300 requests/hr)
def fetch_chip_data(stock_id, start_date, end_date):
    """Fetches Big Three Institutional Investors trades from FinMind API."""
    url = "https://api.finmindtrade.com/api/v4/data"
    parameter = {
        "dataset": "TaiwanStockInstitutionalInvestorsBuySell",
        "data_id": stock_id,
        "start_date": start_date,
        "end_date": end_date,
    }
    try:
        response = requests.get(url, params=parameter, timeout=10)
        if response.status_code == 200:
            res_json = response.json()
            if res_json.get("status") == 200 and "data" in res_json:
                df = pd.DataFrame(res_json["data"])
                if not df.empty:
                    return df
        return pd.DataFrame()
    except Exception:
        # Silently fail, main logic will gracefully handle empty chip data
        return pd.DataFrame()

# --- 3. Five-Dimensional Quantitative Score Calculations ---
def calculate_quant_scores(df_price, df_chip):
    """Calculates all 5 quantitative factors on the dataframe using vectorized operations."""
    df = df_price.copy()
    df['date_str'] = df.index.strftime('%Y-%m-%d')
    
    # --- Technical Indicators ---
    # 20-day Simple Moving Average (MA20 / Bollinger Mid)
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA20_slope'] = df['MA20'] - df['MA20'].shift(1)
    
    # 5-day average volume for Force factor
    df['Vol_MA5'] = df['Volume'].rolling(window=5).mean()
    
    # Bollinger Bands
    df['Std'] = df['Close'].rolling(window=20).std()
    df['Upper'] = df['MA20'] + 2 * df['Std']
    df['Lower'] = df['MA20'] - 2 * df['Std']
    
    # MACD
    df['EMA12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA26'] = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['OSC'] = df['MACD'] - df['Signal']
    
    # --- Align Chip Data ---
    if not df_chip.empty and 'name' in df_chip.columns:
        # Sum buy/sell for Foreign Investors and Investment Trusts
        target_investors = ['Foreign_Investor', 'Investment_Trust']
        df_chip_filtered = df_chip[df_chip['name'].isin(target_investors)].copy()
        df_chip_filtered['net'] = df_chip_filtered['buy'] - df_chip_filtered['sell']
        df_chip_daily = df_chip_filtered.groupby('date')['net'].sum().reset_index()
        df_chip_daily.rename(columns={'net': 'chip_net', 'date': 'date_str'}, inplace=True)
        df_chip_daily['date_str'] = pd.to_datetime(df_chip_daily['date_str']).dt.strftime('%Y-%m-%d')
        
        # Left join to price dataframe
        df = pd.merge(df, df_chip_daily, on='date_str', how='left')
        df['chip_net'] = df['chip_net'].fillna(0)
    else:
        df['chip_net'] = 0.0
        
    # --- 1. Trend (均線) Score ---
    df['score_trend'] = 0
    df.loc[(df['Close'] > df['MA20']) & (df['MA20_slope'] > 0), 'score_trend'] = 1
    df.loc[(df['Close'] < df['MA20']) & (df['MA20_slope'] < 0), 'score_trend'] = -1
    
    # --- 2. Space (布林通道) Score ---
    df['score_space'] = 0
    # Buy: Break mid-band upwards or consolidates at lower-band with low volume on a red K
    break_mid_up = (df['Close'] > df['MA20']) & (df['Close'].shift(1) <= df['MA20'].shift(1))
    lower_threshold = df['Lower'] + 0.15 * (df['MA20'] - df['Lower'])
    near_lower = df['Close'] <= lower_threshold
    low_vol = df['Volume'] < df['Vol_MA5']
    red_k = df['Close'] >= df['Open']
    bottoming = near_lower & low_vol & red_k
    df.loc[break_mid_up | bottoming, 'score_space'] = 1
    
    # Sell: Break mid-band downwards or weakens at upper-band on a black K
    break_mid_down = (df['Close'] < df['MA20']) & (df['Close'].shift(1) >= df['MA20'].shift(1))
    upper_threshold = df['Upper'] - 0.15 * (df['Upper'] - df['MA20'])
    near_upper = df['Close'] >= upper_threshold
    black_k = df['Close'] < df['Open']
    weakening = near_upper & black_k
    df.loc[break_mid_down | weakening, 'score_space'] = -1
    
    # --- 3. Momentum (MACD) Score ---
    df['score_momentum'] = 0
    osc_up = (df['OSC'] > 0) & (df['OSC'] > df['OSC'].shift(1))
    osc_down = (df['OSC'] < 0) & (df['OSC'] < df['OSC'].shift(1))
    df.loc[osc_up, 'score_momentum'] = 1
    df.loc[osc_down, 'score_momentum'] = -1
    
    # --- 4. Force (量能) Score ---
    df['score_force'] = 0
    force_buy = (df['Volume'] > 1.5 * df['Vol_MA5']) & (df['Close'] >= df['Open'])
    force_sell = (df['Volume'] > 1.5 * df['Vol_MA5']) & (df['Close'] < df['Open'])
    df.loc[force_buy, 'score_force'] = 1
    df.loc[force_sell, 'score_force'] = -1
    
    # --- 5. Chip (籌碼) Score ---
    df['score_chip'] = 0
    chip_net_buying = df['chip_net'] > 0
    chip_net_selling = df['chip_net'] < 0
    df.loc[chip_net_buying & chip_net_buying.shift(1) & chip_net_buying.shift(2), 'score_chip'] = 1
    df.loc[chip_net_selling & chip_net_selling.shift(1) & chip_net_selling.shift(2), 'score_chip'] = -1
    
    return df

# --- 4. Backtester Engine (Numpy Vectorized Trades + NAV Calculation) ---
def run_backtest(df_data, w_trend, w_space, w_momentum, w_force, w_chip, friction_rate=0.004,
                confirm_days=2, min_hold_days=5, filter_squeeze=True):
    """
    Simulates trading strategy based on weighted scores and returns performance stats and NAV curve.
    
    Noise Filters (Low-Frequency / Office Worker Mode):
    - confirm_days: Number of consecutive days signal must persist before executing trade (default 2)
    - min_hold_days: Minimum holding days before sell is allowed (default 5 = ~1 trading week)
    - filter_squeeze: If True, suppresses buy signals during Bollinger Band squeeze (default True)
    """
    df = df_data.copy()
    
    # Calculate daily weighted total score
    df['total_score'] = (
        w_trend * df['score_trend'] +
        w_space * df['score_space'] +
        w_momentum * df['score_momentum'] +
        w_force * df['score_force'] +
        w_chip * df['score_chip']
    )
    
    # Define raw signals
    df['signal_raw'] = 0
    df.loc[df['total_score'] >= 3.0, 'signal_raw'] = 1    # Buy Green
    df.loc[df['total_score'] <= -3.0, 'signal_raw'] = -1  # Sell Red
    
    # ── FILTER 1: Bollinger Squeeze Suppression ──────────────────────────────
    # When band-width is extremely narrow (<30th percentile of last 100 bars),
    # stock is in a low-volatility sideways chop → suppress buy signals
    if filter_squeeze and 'Std' in df.columns and 'MA20' in df.columns:
        # Bollinger Bandwidth = (Upper - Lower) / MA20 = 4*Std / MA20
        df['bb_width'] = (4 * df['Std']) / df['MA20'].replace(0, np.nan)
        # Rolling 100-bar 30th percentile (minimum 30 bars)
        df['bb_squeeze_threshold'] = df['bb_width'].rolling(100, min_periods=30).quantile(0.30)
        # Mark squeeze days: width below threshold → sideways chop zone
        df['is_squeeze'] = (df['bb_width'] <= df['bb_squeeze_threshold']) & df['bb_width'].notna()
        # Suppress buy signals during squeeze
        df.loc[df['is_squeeze'] == True, 'signal_raw'] = df.loc[df['is_squeeze'] == True, 'signal_raw'].clip(upper=0)
    else:
        df['is_squeeze'] = False
    
    # ── FILTER 2: Signal Confirmation Days ───────────────────────────────────
    # Only trigger a buy/sell if the signal has persisted for `confirm_days` consecutive days
    if confirm_days > 1:
        buy_confirmed = (df['signal_raw'] == 1).rolling(confirm_days, min_periods=confirm_days).min().fillna(0) == 1
        sell_confirmed = (df['signal_raw'] == -1).rolling(confirm_days, min_periods=confirm_days).min().fillna(0) == 1
        df['signal'] = 0
        df.loc[buy_confirmed, 'signal'] = 1
        df.loc[sell_confirmed, 'signal'] = -1
    else:
        df['signal'] = df['signal_raw']
    
    # ── FILTER 3: Minimum Holding Period + State Machine ─────────────────────
    positions = []
    current_pos = 0
    buy_price = 0
    buy_date = None
    days_held = 0
    trades = []
    actions = ['Hold'] * len(df)
    
    for i, (idx, row) in enumerate(df.iterrows()):
        sig = row['signal']
        close = row['Close']
        date = row['date_str']
        
        if current_pos == 0 and sig == 1:
            # Enter new position
            current_pos = 1
            buy_price = close
            buy_date = date
            days_held = 0
            actions[i] = 'Buy'
        elif current_pos == 1:
            days_held += 1
            # Only allow sell if minimum holding period satisfied
            if sig == -1 and days_held >= min_hold_days:
                current_pos = 0
                sell_price = close
                ret = (sell_price / buy_price) * (1 - friction_rate) - 1
                trades.append({
                    'buy_date': buy_date,
                    'sell_date': date,
                    'buy_price': buy_price,
                    'sell_price': sell_price,
                    'return': ret,
                    'hold_days': days_held
                })
                actions[i] = 'Sell'
                days_held = 0
            
        positions.append(current_pos)
        
    # Handle final open position at the end of the period
    if current_pos == 1:
        sell_price = df['Close'].iloc[-1]
        date = df['date_str'].iloc[-1]
        ret = (sell_price / buy_price) * (1 - friction_rate) - 1
        trades.append({
            'buy_date': buy_date,
            'sell_date': date,
            'buy_price': buy_price,
            'sell_price': sell_price,
            'return': ret,
            'hold_days': days_held
        })
        actions[-1] = 'Sell'
        
    df['position'] = positions
    df['action'] = actions
    
    # --- NAV Curve Calculation ---
    # We break down costs into entry (0.1425%) and exit (0.1425% fee + 0.3% tax = 0.4425%)
    buy_cost = 0.001425
    sell_cost = 0.001425 + 0.003
    
    nav = [1.0]
    for i in range(1, len(df)):
        pos_prev = df.loc[i-1, 'position']
        pos_curr = df.loc[i, 'position']
        close_prev = df.loc[i-1, 'Close']
        close_curr = df.loc[i, 'Close']
        
        daily_ret = close_curr / close_prev
        
        if pos_prev == 1:
            if pos_curr == 1:
                val = nav[-1] * daily_ret
            else:
                # Exit position today
                val = nav[-1] * daily_ret * (1 - sell_cost)
        else:
            if pos_curr == 1:
                # Enter position today
                val = nav[-1] * (1 - buy_cost) * daily_ret
            else:
                val = nav[-1]
        nav.append(val)
        
    df['strategy_nav'] = nav
    df['bh_nav'] = df['Close'] / df['Close'].iloc[0]
    
    # --- Calculate Performance Metrics ---
    total_trades = len(trades)
    winning_trades = sum(1 for t in trades if t['return'] > 0)
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
    
    strategy_return = (df['strategy_nav'].iloc[-1] - 1) * 100
    bh_return = (df['bh_nav'].iloc[-1] - 1) * 100
    
    # Maximum Drawdown (MDD)
    strategy_peaks = df['strategy_nav'].cummax()
    strategy_dd = (df['strategy_nav'] - strategy_peaks) / strategy_peaks
    mdd = strategy_dd.min() * 100
    
    bh_peaks = df['bh_nav'].cummax()
    bh_dd = (df['bh_nav'] - bh_peaks) / bh_peaks
    bh_mdd = bh_dd.min() * 100
    
    metrics = {
        'win_rate': win_rate,
        'strategy_return': strategy_return,
        'bh_return': bh_return,
        'mdd': mdd,
        'bh_mdd': bh_mdd,
        'trade_count': total_trades,
        'trades': trades
    }
    
    return df, metrics


def optimize_weights_hill_climbing(df_data, friction_rate, num_restarts=15,
                                   confirm_days=2, min_hold_days=5, filter_squeeze=True):
    """Finds the optimal weight configuration that maximizes (Strategy Return - Buy & Hold Return).
    Respects low-frequency filter settings so optimized weights work with the same filter configuration.
    """
    import random
    best_score = -999999.0
    best_weights = (1.0, 1.0, 1.0, 1.0, 1.0)
    
    # Grid steps of 0.5 for weights in range [0.0, 5.0]
    possible_values = [round(x * 0.5, 1) for x in range(11)]
    
    for _ in range(num_restarts):
        # Random start point
        w = [random.choice(possible_values) for _ in range(5)]
        if sum(w) == 0:
            w = [1.0, 1.0, 1.0, 1.0, 1.0]
            
        _, metrics = run_backtest(df_data, w[0], w[1], w[2], w[3], w[4], friction_rate,
                                  confirm_days=confirm_days, min_hold_days=min_hold_days, filter_squeeze=filter_squeeze)
        current_score = metrics['strategy_return'] - metrics['bh_return']
        
        # Hill climbing local search
        improved = True
        while improved:
            improved = False
            for i in range(5):
                for delta in [-1.0, -0.5, 0.5, 1.0]:
                    new_w = list(w)
                    new_w[i] = round(new_w[i] + delta, 1)
                    if 0.0 <= new_w[i] <= 5.0 and sum(new_w) > 0:
                        _, m = run_backtest(df_data, new_w[0], new_w[1], new_w[2], new_w[3], new_w[4], friction_rate,
                                           confirm_days=confirm_days, min_hold_days=min_hold_days, filter_squeeze=filter_squeeze)
                        score = m['strategy_return'] - m['bh_return']
                        if score > current_score:
                            current_score = score
                            w = new_w
                            improved = True
                            
        if current_score > best_score:
            best_score = current_score
            best_weights = tuple(w)
            
    return best_weights, best_score


def run_optimization_callback():
    """Streamlit callback to safely optimize weights before widget instantiation."""
    if "df_past_year" in st.session_state and "friction" in st.session_state:
        df_data = st.session_state.df_past_year
        fric = st.session_state.friction
        # Pass current filter settings to optimizer for consistent simulation
        lf_on = st.session_state.get("lf_mode_on", True)
        cd = st.session_state.get("confirm_days", 2) if lf_on else 1
        mhd = st.session_state.get("min_hold_days", 5) if lf_on else 1
        fsq = st.session_state.get("filter_squeeze", True) if lf_on else False
        best_w, best_score = optimize_weights_hill_climbing(df_data, fric,
                                                            confirm_days=cd,
                                                            min_hold_days=mhd,
                                                            filter_squeeze=fsq)
        st.session_state.w_trend = best_w[0]
        st.session_state.w_space = best_w[1]
        st.session_state.w_momentum = best_w[2]
        st.session_state.w_force = best_w[3]
        st.session_state.w_chip = best_w[4]
        st.session_state.opt_success_msg = f"🎯 最佳化完成！超額報酬達 {best_score:+.1f}%"


# ==============================================================================
# MAIN PAGE LAYOUT & SIDEBAR CONTROL
# ==============================================================================

# Title Header
st.markdown("<h1 style='text-align: center; margin-bottom: 2px;'>🟢🔴🟡 台股紅綠燈量化買賣看盤系統</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #64748b; font-size: 0.95rem; margin-bottom: 30px;'>簡單、好懂的台股多空評分與回測工具，看紅綠燈輕鬆掌握買賣訊號與勝率</p>", unsafe_allow_html=True)

# --- Sidebar Inputs ---
st.sidebar.markdown("<h2 style='color: #38bdf8; font-weight: 700; margin-bottom: 20px; font-size: 1.3rem;'>⚙️ 策略因子比重設定</h2>", unsafe_allow_html=True)

# 1. Trend
st.sidebar.markdown("""
<div style='margin-top: 10px; margin-bottom: 2px;'>
    <b style='color: #f1f5f9; font-size: 0.95rem;'>1. 趨勢均線權重</b>
    <span style='color: #cbd5e1; font-size: 0.8rem; display: block; line-height: 1.3;'>（買在漲勢中！判斷股價是漲是跌？看股價有沒有站在20天平均線上）</span>
</div>
""", unsafe_allow_html=True)
w_trend = st.sidebar.slider("1. 均線趨勢權重", min_value=0.0, max_value=5.0, value=1.0, step=0.1, key="w_trend", label_visibility="collapsed")

# 2. Space
st.sidebar.markdown("""
<div style='margin-top: 10px; margin-bottom: 2px;'>
    <b style='color: #f1f5f9; font-size: 0.95rem;'>2. 布林通道便宜/貴權重</b>
    <span style='color: #cbd5e1; font-size: 0.8rem; display: block; line-height: 1.3;'>（買在便宜處！看股價現在是便宜下軌，還是太貴上軌）</span>
</div>
""", unsafe_allow_html=True)
w_space = st.sidebar.slider("2. 布林空間權重", min_value=0.0, max_value=5.0, value=1.0, step=0.1, key="w_space", label_visibility="collapsed")

# 3. Momentum
st.sidebar.markdown("""
<div style='margin-top: 10px; margin-bottom: 2px;'>
    <b style='color: #f1f5f9; font-size: 0.95rem;'>3. MACD多空能量權重</b>
    <span style='color: #cbd5e1; font-size: 0.8rem; display: block; line-height: 1.3;'>（買在強勢點！股價上漲力道強不強？看紅綠能量柱增減）</span>
</div>
""", unsafe_allow_html=True)
w_momentum = st.sidebar.slider("3. MACD動能權重", min_value=0.0, max_value=5.0, value=1.0, step=0.1, key="w_momentum", label_visibility="collapsed")

# 4. Force
st.sidebar.markdown("""
<div style='margin-top: 10px; margin-bottom: 2px;'>
    <b style='color: #f1f5f9; font-size: 0.95rem;'>4. 成交量爆量權重</b>
    <span style='color: #cbd5e1; font-size: 0.8rem; display: block; line-height: 1.3;'>（看買氣熱不熱！有沒有爆量大買或主力大出貨）</span>
</div>
""", unsafe_allow_html=True)
w_force = st.sidebar.slider("4. 成交力道權重", min_value=0.0, max_value=5.0, value=1.0, step=0.1, key="w_force", label_visibility="collapsed")

# 5. Chip
st.sidebar.markdown("""
<div style='margin-top: 10px; margin-bottom: 2px;'>
    <b style='color: #f1f5f9; font-size: 0.95rem;'>5. 法人籌碼權重</b>
    <span style='color: #cbd5e1; font-size: 0.8rem; display: block; line-height: 1.3;'>（跟著大戶走！外資投信有沒有同步連續大買）</span>
</div>
""", unsafe_allow_html=True)
w_chip = st.sidebar.slider("5. 法人底氣權重", min_value=0.0, max_value=5.0, value=1.0, step=0.1, key="w_chip", label_visibility="collapsed")

st.sidebar.markdown("---")
st.sidebar.markdown("<h3 style='color: #38bdf8; font-weight: 700; margin-bottom: 10px; font-size: 1.1rem;'>📊 交易手續費與稅金</h3>", unsafe_allow_html=True)
st.sidebar.markdown("""
<div style='margin-bottom: 2px;'>
    <span style='color: #cbd5e1; font-size: 0.8rem; display: block; line-height: 1.3;'>（每次買賣收取的摩擦成本，包含券商手續費與證交稅）</span>
</div>
""", unsafe_allow_html=True)
friction = st.sidebar.slider("單次交易成本 (%)", min_value=0.0, max_value=1.5, value=0.4, step=0.05, label_visibility="collapsed") / 100.0
st.session_state.friction = friction

# ── 🛡️ 濾網設定（雜訊與頻率控制）──────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.markdown("<h3 style='color: #f59e0b; font-weight: 700; margin-bottom: 5px; font-size: 1.1rem;'>🛡️ 濾網設定 (雜訊與頻率控制)</h3>", unsafe_allow_html=True)
st.sidebar.markdown("<span style='color: #cbd5e1; font-size: 0.8rem; display: block; line-height: 1.4; margin-bottom: 10px;'>（開啟後自動過濾盤整期假突破，大幅降低交易頻率，最適合上班族！）</span>", unsafe_allow_html=True)

lf_mode_on = st.sidebar.toggle(
    "🧑‍💼 開啟上班族低頻交易模式",
    value=st.session_state.get("lf_mode_on", True),
    key="lf_mode_on",
    help="開啟後自動啟用三重噪音過濾器，濾掉盤整區的雜訊交易"
)

if lf_mode_on:
    st.sidebar.markdown("""
    <div style='background: rgba(245,158,11,0.08); border: 1px solid rgba(245,158,11,0.3); border-radius:8px; padding:10px 12px; margin-bottom:8px;'>
        <b style='color:#f59e0b; font-size:0.85rem;'>✅ 低頻模式已啟動</b>
        <p style='color:#94a3b8; font-size:0.78rem; margin:4px 0 0 0; line-height:1.4;'>三重過濾器運作中：布林擠壓偵測、連續訊號確認、最低持有天數</p>
    </div>
    """, unsafe_allow_html=True)

    st.sidebar.markdown("""
    <div style='margin-top: 8px; margin-bottom: 2px;'>
        <b style='color: #f1f5f9; font-size: 0.9rem;'>① 訊號連續確認天數</b>
        <span style='color: #94a3b8; font-size: 0.78rem; display: block; line-height: 1.3;'>（必須連續幾天出現買/賣訊號才執行，預設 2 天可濾掉大量假突破）</span>
    </div>
    """, unsafe_allow_html=True)
    confirm_days = st.sidebar.slider("訊號確認天數", min_value=1, max_value=5, value=st.session_state.get("confirm_days", 2), step=1, key="confirm_days", label_visibility="collapsed")

    st.sidebar.markdown("""
    <div style='margin-top: 8px; margin-bottom: 2px;'>
        <b style='color: #f1f5f9; font-size: 0.9rem;'>② 最低持有天數</b>
        <span style='color: #94a3b8; font-size: 0.78rem; display: block; line-height: 1.3;'>（買進後至少持有幾天才能觸發賣出，避免盤整來回洗盤，預設 5 天）</span>
    </div>
    """, unsafe_allow_html=True)
    min_hold_days = st.sidebar.slider("最低持有天數", min_value=1, max_value=20, value=st.session_state.get("min_hold_days", 5), step=1, key="min_hold_days", label_visibility="collapsed")

    st.sidebar.markdown("""
    <div style='margin-top: 8px; margin-bottom: 4px;'>
        <b style='color: #f1f5f9; font-size: 0.9rem;'>③ 布林盤整擠壓過濾</b>
        <span style='color: #94a3b8; font-size: 0.78rem; display: block; line-height: 1.3;'>（偵測到布林帶極度收窄時，自動壓制買進訊號，避免橫盤套牢）</span>
    </div>
    """, unsafe_allow_html=True)
    filter_squeeze = st.sidebar.checkbox("啟用布林擠壓偵測過濾", value=st.session_state.get("filter_squeeze", True), key="filter_squeeze")
else:
    st.sidebar.markdown("""
    <div style='background: rgba(100,116,139,0.1); border: 1px solid rgba(100,116,139,0.3); border-radius:8px; padding:10px 12px; margin-bottom:8px;'>
        <b style='color:#64748b; font-size:0.85rem;'>⏸️ 低頻模式已關閉</b>
        <p style='color:#475569; font-size:0.78rem; margin:4px 0 0 0; line-height:1.4;'>使用原始訊號，無過濾，交易頻率較高（適合進階測試）</p>
    </div>
    """, unsafe_allow_html=True)
    confirm_days = 1
    min_hold_days = 1
    filter_squeeze = False

st.sidebar.markdown("<br>", unsafe_allow_html=True)

# Custom premium chip update notice card
st.sidebar.markdown("""
<div style='background-color: rgba(56, 189, 248, 0.1); border: 1px solid rgba(56, 189, 248, 0.3); padding: 12px; border-radius: 8px;'>
    <b style='color: #38bdf8; font-size: 0.9rem;'>📢 籌碼數據更新提示：</b>
    <p style='color: #cbd5e1; font-size: 0.8rem; margin: 4px 0 0 0; line-height: 1.4;'>
        三大法人籌碼數據於每日下午 <b>15:30</b> 完成更新。非更新時間或無交易日則保留最近一日數據。
    </p>
</div>
""", unsafe_allow_html=True)

# 6. Sidebar Optimization Button (Directly defined here with callback)
st.sidebar.markdown("---")
st.sidebar.markdown("<h3 style='color: #10b981; font-weight: 700; margin-bottom: 5px; font-size: 1.1rem;'>🤖 權重智能最佳化</h3>", unsafe_allow_html=True)
st.sidebar.markdown("<span style='color: #cbd5e1; font-size: 0.8rem; display: block; line-height: 1.4; margin-bottom: 12px;'>（一鍵自動尋找黃金比重，讓策略模擬報酬最大化超越放著不動的傻傻持有）</span>", unsafe_allow_html=True)

if "df_past_year" in st.session_state:
    st.sidebar.button("🤖 一鍵自動最佳化比重", on_click=run_optimization_callback, use_container_width=True)
else:
    st.sidebar.button("🤖 一鍵自動最佳化比重 (請先載入數據)", disabled=True, use_container_width=True)

if "opt_success_msg" in st.session_state and st.session_state.opt_success_msg:
    st.sidebar.success(st.session_state.opt_success_msg)
    # Clear the success message so it does not persist on other reruns
    st.session_state.opt_success_msg = None

# --- Top Section: Stock Selection ---
stock_list = load_stock_list()

user_query = st.text_input(
    "🔍 請輸入台股代碼或中文名稱進行模糊搜尋（如輸入：2330、台積電、鴻海、8069 或 元太）：",
    value="2330"
).strip()

# Initialize default values
selected_code = "2330"
stock_symbol = "2330.TW"
stock_name = "台積電"

if user_query:
    q = user_query.upper().strip()
    matched_stock = None
    
    # 1. Exact match on code (e.g. "2330") or symbol (e.g. "2330.TW")
    for s in stock_list:
        if s['code'] == q or s['symbol'].upper() == q:
            matched_stock = s
            break
            
    # 2. Exact match on Chinese name (e.g. "台積電")
    if not matched_stock:
        for s in stock_list:
            if s['name'] == q:
                matched_stock = s
                break
                
    # 3. Fuzzy substring match on Chinese name or code (e.g. "台泥" or "233")
    if not matched_stock:
        for s in stock_list:
            if q in s['name'] or q in s['code']:
                matched_stock = s
                break
                
    # 4. Apply results
    if matched_stock:
        selected_code = matched_stock['code']
        stock_symbol = matched_stock['symbol']
        stock_name = matched_stock['name']
        st.success(f"✅ **自動比對成功**！目前載入：**{selected_code} - {stock_name} ({matched_stock['market']})**，資料代碼：`{stock_symbol}`")
    else:
        # Fallback if manual or not found
        if "." in q:
            stock_symbol = q
            selected_code = q.split(".")[0]
            stock_name = "手動輸入"
        elif q.isdigit():
            selected_code = q
            stock_symbol = f"{q}.TW"
            stock_name = f"自訂代碼 {q}"
        else:
            selected_code = q
            stock_symbol = q
            stock_name = q
        st.info(f"ℹ️ **直接解析代碼**：未在常用台股資料庫中找到完全相符項目，將直接下載：`{stock_symbol}`")

# Fetch Data Dates
# We fetch 450 days of data to warm up indicators, and slice to past 1 year for display and backtesting
end_date = datetime.today()
start_date = end_date - timedelta(days=450)

start_date_str = start_date.strftime('%Y-%m-%d')
end_date_str = end_date.strftime('%Y-%m-%d')

with st.spinner("🚀 正在安全下載並計算最新個股多空數據..."):
    # Fetch price and chip data
    df_price_raw = fetch_stock_price(stock_symbol, start_date_str, end_date_str)
    df_chip_raw = fetch_chip_data(selected_code, start_date_str, end_date_str)
    
if df_price_raw.empty:
    st.warning("⚠️ 無法獲取該個股的歷史價格。請確認代碼是否輸入正確，例如台股上市後綴 `.TW`，上櫃後綴 `.TWO`。")
    st.stop()

# Compute all scores
df_scored = calculate_quant_scores(df_price_raw, df_chip_raw)

# Slice to exactly the past 1 year (365 days) for visual display and backtest alignment
cutoff_date = (datetime.today() - timedelta(days=365)).strftime('%Y-%m-%d')
df_past_year = df_scored[df_scored['date_str'] >= cutoff_date].copy().reset_index(drop=True)

if df_past_year.empty:
    st.error("⚠️ 資料時間跨度不足一年，無法建立回測。")
    st.stop()

# Run strategy backtest using selected weights + noise filter settings
df_backtest, metrics = run_backtest(
    df_past_year,
    w_trend,
    w_space,
    w_momentum,
    w_force,
    w_chip,
    friction_rate=friction,
    confirm_days=confirm_days,
    min_hold_days=min_hold_days,
    filter_squeeze=filter_squeeze
)

# Save df_past_year to session state for the callback to use
st.session_state.df_past_year = df_past_year

# Extract today's scores
today_row = df_backtest.iloc[-1]
today_score = today_row['total_score']
today_signal = today_row['signal']
today_date = today_row['date_str']

# Display Top Section: Neon Large Status Light Card
if today_score >= 3.0:
    glow_class = "neon-green"
    light_text = "🟢 綜合判定：建議買進 (綠燈)"
    score_color = "#10b981"
elif today_score <= -3.0:
    glow_class = "neon-red"
    light_text = "🔴 綜合判定：建議賣出 (紅燈)"
    score_color = "#ef4444"
else:
    glow_class = "neon-yellow"
    light_text = "🟡 綜合判定：持股觀望 (黃燈)"
    score_color = "#f59e0b"

st.markdown(f"""
<div class="neon-card {glow_class}">
    <div class="neon-title">{light_text}</div>
    <div class="neon-subtitle">
        個股代號：<span style="color: #ffffff; font-weight: 600;">{stock_symbol} - {stock_name}</span> &nbsp;|&nbsp; 
        資料日期：<span style="color: #ffffff; font-weight: 600;">{today_date}</span> &nbsp;|&nbsp; 
        當日綜合多空評分：<span style="color: {score_color}; font-weight: 800; font-size: 1.3rem;">{today_score:+.1f} 分</span>
    </div>
</div>
""", unsafe_allow_html=True)


# ==============================================================================
# MIDDLE SECTION: SPEAKING INTERACTIVE K-LINE CHART
# ==============================================================================
st.markdown("<h3 style='font-weight: 700; color: #f1f5f9; margin-top: 10px; margin-bottom: 10px;'>📊 股票走勢與紅綠燈交易訊號圖</h3>", unsafe_allow_html=True)
st.markdown("<p style='color: #94a3b8; font-size: 0.85rem; margin-top: -5px; margin-bottom: 15px;'>（下方標記 🟢 買 與 🔴 賣 代表策略執行交易的日子，成交量亮藍色表示當日法人合力大買護盤）</p>", unsafe_allow_html=True)

# Generate subplot: Candlestick (Row 1), Volume (Row 2)
fig = make_subplots(
    rows=2, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.03,
    row_heights=[0.75, 0.25]
)

# 1. Bollinger Bands transparent shadow area
fig.add_trace(
    go.Scatter(
        x=df_backtest['date_str'],
        y=df_backtest['Upper'],
        line=dict(color='rgba(168, 85, 247, 0.15)', width=1),
        name='布林上軌',
        showlegend=False
    ),
    row=1, col=1
)

fig.add_trace(
    go.Scatter(
        x=df_backtest['date_str'],
        y=df_backtest['Lower'],
        line=dict(color='rgba(168, 85, 247, 0.15)', width=1),
        fill='tonexty',
        fillcolor='rgba(168, 85, 247, 0.04)',
        name='布林通道陰影區',
        showlegend=True
    ),
    row=1, col=1
)

# 2. Bollinger Mid Band (20MA)
fig.add_trace(
    go.Scatter(
        x=df_backtest['date_str'],
        y=df_backtest['MA20'],
        line=dict(color='rgba(245, 158, 11, 0.8)', width=1.5, dash='dash'),
        name='20MA 中軌'
    ),
    row=1, col=1
)

# 3. Main Candlestick Chart
fig.add_trace(
    go.Candlestick(
        x=df_backtest['date_str'],
        open=df_backtest['Open'],
        high=df_backtest['High'],
        low=df_backtest['Low'],
        close=df_backtest['Close'],
        increasing_line_color='#ef4444',  # Taiwan Red Up
        decreasing_line_color='#22c55e',  # Taiwan Green Down
        increasing_fillcolor='#ef4444',
        decreasing_fillcolor='#22c55e',
        name='日 K 線'
    ),
    row=1, col=1
)

# 4. Overlaid Signal Arrow Markers
# Buy signal markers
buy_signals = df_backtest[df_backtest['action'] == 'Buy']
fig.add_trace(
    go.Scatter(
        x=buy_signals['date_str'],
        y=buy_signals['Low'] * 0.98,
        mode='markers+text',
        marker=dict(symbol='triangle-up', size=14, color='#10b981', line=dict(width=1.5, color='#ffffff')),
        name='買進點 🟢',
        text=[f"<b>買 {p:.1f}</b>" for p in buy_signals['Close']],
        textposition="bottom center",
        textfont=dict(color="#10b981", size=10, family="Noto Sans TC"),
        customdata=buy_signals['Close'],
        hovertemplate="<b>🟢 買進訊號</b><br>日期: %{x}<br>成交價: %{customdata:.1f} 元<extra></extra>"
    ),
    row=1, col=1
)

# Sell signal markers
sell_signals = df_backtest[df_backtest['action'] == 'Sell']
fig.add_trace(
    go.Scatter(
        x=sell_signals['date_str'],
        y=sell_signals['High'] * 1.02,
        mode='markers+text',
        marker=dict(symbol='triangle-down', size=14, color='#ef4444', line=dict(width=1.5, color='#ffffff')),
        name='賣出點 🔴',
        text=[f"<b>賣 {p:.1f}</b>" for p in sell_signals['Close']],
        textposition="top center",
        textfont=dict(color="#ef4444", size=10, family="Noto Sans TC"),
        customdata=sell_signals['Close'],
        hovertemplate="<b>🔴 賣出訊號</b><br>日期: %{x}<br>成交價: %{customdata:.1f} 元<extra></extra>"
    ),
    row=1, col=1
)

# 5. Volume Subplot (Row 2)
# Set colors: If Big Three Institutional net buying is high (e.g. > 0), color it bright blue, else standard red/green based on price return
volume_colors = []
for idx, row in df_backtest.iterrows():
    if row['chip_net'] > 0:
        volume_colors.append('#38bdf8') # Bright blue for big institutional support
    else:
        # Standard color based on price change
        if row['Close'] >= row['Open']:
            volume_colors.append('rgba(239, 68, 68, 0.45)') # Soft red
        else:
            volume_colors.append('rgba(34, 197, 94, 0.45)') # Soft green

fig.add_trace(
    go.Bar(
        x=df_backtest['date_str'],
        y=df_backtest['Volume'],
        marker_color=volume_colors,
        name='成交量 (亮藍色表法人大買)'
    ),
    row=2, col=1
)

# Styling and Interactive layout overrides
fig.update_layout(
    template='plotly_dark',
    paper_bgcolor='#0f172a',
    plot_bgcolor='rgba(15, 23, 42, 0.6)',
    xaxis_rangeslider_visible=False,
    height=550,
    margin=dict(l=50, r=30, t=10, b=10),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
        font=dict(color="#f8fafc", size=11)
    ),
    hovermode='x unified',
    yaxis1=dict(title='股價 (TWD)', gridcolor='rgba(255, 255, 255, 0.05)'),
    yaxis2=dict(title='成交量 (股)', gridcolor='rgba(255, 255, 255, 0.05)'),
    xaxis2=dict(gridcolor='rgba(255, 255, 255, 0.05)')
)

st.plotly_chart(fig, use_container_width=True)

# 6. Responsive Historical Signals Detail Section (Mobile Friendly)
with st.expander("📋 歷史交易訊號明細 (手機版可展開此處進行對照)", expanded=False):
    trades_list = metrics.get('trades', [])
    if not trades_list:
        st.markdown("<p style='color: #94a3b8; text-align: center; margin: 10px;'>目前此期間策略尚無完整的交易紀錄（須包含買進與賣出）。</p>", unsafe_allow_html=True)
    else:
        # Construct responsive cards list
        html_content = "<div style='display: grid; gap: 12px; max-height: 400px; overflow-y: auto; padding: 4px;'>"
        for i, t in enumerate(trades_list[::-1]):  # Show latest trade first
            ret_pct = t['return'] * 100
            ret_color = "#10b981" if ret_pct > 0 else ("#ef4444" if ret_pct < 0 else "#94a3b8")
            ret_sign = "+" if ret_pct > 0 else ""
            
            html_content += f"""
            <div style='background-color: #1e293b; border-left: 4px solid {ret_color}; padding: 12px 16px; border-radius: 8px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);'>
                <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 8px;'>
                    <span style='font-weight: 700; color: #f8fafc; font-size: 0.95rem;'>第 {len(trades_list)-i} 次交易</span>
                    <span style='font-weight: 800; color: {ret_color}; font-size: 0.95rem; background-color: rgba(255,255,255,0.03); padding: 2px 8px; border-radius: 4px;'>
                        損益：{ret_sign}{ret_pct:.2f}%
                    </span>
                </div>
                <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 16px; font-size: 0.85rem; color: #cbd5e1;'>
                    <div>
                        <span style='color: #94a3b8; display: block; font-size: 0.75rem; margin-bottom: 2px;'>🟢 買進時間/價格</span>
                        <b>{t['buy_date']}</b> @ <span style='color: #10b981; font-weight: 700;'>{t['buy_price']:.1f} 元</span>
                    </div>
                    <div>
                        <span style='color: #94a3b8; display: block; font-size: 0.75rem; margin-bottom: 2px;'>🔴 賣出時間/價格</span>
                        <b>{t['sell_date']}</b> @ <span style='color: #ef4444; font-weight: 700;'>{t['sell_price']:.1f} 元</span>
                    </div>
                </div>
            </div>
            """
        html_content += "</div>"
        st.markdown(html_content, unsafe_allow_html=True)


# ==============================================================================
# BOTTOM SECTION: TRUST & TRANSPARENCY
# ==============================================================================
st.markdown("<br>", unsafe_allow_html=True)
col_left, col_right = st.columns([1, 1])

# --- LEFT COLUMN: BACKTEST PERFORMANCE ---
with col_left:
    st.markdown("<h3 style='font-weight: 700; color: #f1f5f9;'>📈 本策略過去一年模擬回測賺錢效果</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94a3b8; font-size: 0.85rem; margin-top: -5px; margin-bottom: 15px;'>（以 100 萬台幣為本金，嚴格按照紅綠燈訊號在黃/紅燈轉綠燈時買進、綠燈轉紅燈時賣出）</p>", unsafe_allow_html=True)
    
    # 4 metrics cards
    st.markdown(f"""
    <div class="metric-container">
        <div class="metric-card">
            <div class="metric-value" style="color: {score_color};">{metrics['strategy_return']:+.2f}%</div>
            <div class="metric-label">本策略累積賺多少 (%)</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{metrics['win_rate']:.1f}%</div>
            <div class="metric-label">買賣勝率 (做對次數 %)</div>
        </div>
        <div class="metric-card">
            <div class="metric-value" style="color: #ef4444;">{metrics['mdd']:.2f}%</div>
            <div class="metric-label">最大可能虧損 (MDD)</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{metrics['trade_count']} 次</div>
            <div class="metric-label">累積交易次數</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Cumulative NAV comparison chart
    fig_nav = go.Figure()
    fig_nav.add_trace(
        go.Scatter(
            x=df_backtest['date_str'],
            y=df_backtest['strategy_nav'] * 100 - 100,
            line=dict(color=score_color, width=2.5),
            name='跟著紅綠燈訊號買賣'
        )
    )
    fig_nav.add_trace(
        go.Scatter(
            x=df_backtest['date_str'],
            y=df_backtest['bh_nav'] * 100 - 100,
            line=dict(color='#64748b', width=1.5, dash='dot'),
            name=f'放著不動傻傻持有 ({stock_name})'
        )
    )
    
    fig_nav.update_layout(
        template='plotly_dark',
        paper_bgcolor='#0f172a',
        plot_bgcolor='rgba(15, 23, 42, 0.6)',
        height=280,
        margin=dict(l=40, r=20, t=10, b=10),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(color="#f8fafc", size=11)
        ),
        yaxis=dict(
            title='模擬帳戶獲利百分比 (%)', 
            gridcolor='rgba(255, 255, 255, 0.05)',
            ticksuffix='%'
        ),
        xaxis=dict(gridcolor='rgba(255, 255, 255, 0.05)'),
        hovermode='x unified'
    )
    st.plotly_chart(fig_nav, use_container_width=True)


# --- RIGHT COLUMN: FIVE FACTOR HEALTH CHECK TABLE ---
with col_right:
    st.markdown("<h3 style='font-weight: 700; color: #f1f5f9;'>📋 今日股票五大核心指標診斷</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94a3b8; font-size: 0.85rem; margin-top: -5px; margin-bottom: 15px;'>（診斷當天股票的健康狀態，看分數高低決定買賣，右側有大白話解讀）</p>", unsafe_allow_html=True)
    
    # Helper functions to build pretty rows
    def get_badge(score):
        if score == 1:
            return '<span class="score-badge badge-pos">多方 (+1)</span>'
        elif score == -1:
            return '<span class="score-badge badge-neg">空方 (-1)</span>'
        else:
            return '<span class="score-badge badge-zero">中性 (0)</span>'
            
    # Set display texts and detail strings for today's factors
    
    # 1. Trend MA
    trend_val = today_row['score_trend']
    trend_detail = "🟢 股價站在 20天平均線 (20MA) 之上，且均線朝上，代表現在是上升波段，偏多操作！" if trend_val == 1 else ("🔴 股價跌破 20天平均線 (20MA) 之下，且均線朝下，代表現在是下跌波段，危險避開！" if trend_val == -1 else "⚪ 股價在均線附近橫盤整理，沒有明顯的漲跌趨勢。")
    
    # 2. Space Bollinger
    space_val = today_row['score_space']
    space_detail = "🟢 股價剛往上衝破中軌，或是在便宜的下軌量縮止跌，是極佳的便宜買點！" if space_val == 1 else ("🔴 股價跌破中軌，或是在高檔太貴的上軌出現轉弱，小心被套牢在山頂！" if space_val == -1 else "⚪ 股價處於通道中間的安全區，沒有太貴也沒有太便宜的特別訊號。")
    
    # 3. MACD
    macd_val = today_row['score_momentum']
    macd_detail = "🟢 紅色能量柱持續變長，代表買盤力道正在快速增強，股價往上衝的動能很足！" if macd_val == 1 else ("🔴 綠色能量柱持續變長，代表賣壓非常沉重，股價往下探的力道還在加大！" if macd_val == -1 else "⚪ 能量柱正在縮短或方向不明，多空雙方力道暫時均衡。")
    
    # 4. Force Volume
    force_val = today_row['score_force']
    force_detail = "🟢 成交量比平常大增 1.5 倍以上且收紅K棒，代表買氣極旺，有主力大資金進場！" if force_val == 1 else ("🔴 成交量爆量卻收黑K棒，代表主力或大戶在大舉出貨拋售，重大警訊！" if force_val == -1 else "⚪ 成交量一般般，沒有爆量大買或大賣的動靜。")
    
    # 5. Chip Institutional
    chip_val = today_row['score_chip']
    chip_detail = "🟢 外資與投信連續 3 天同步加碼買進，代表大法人非常看好，有籌碼撐腰！" if chip_val == 1 else ("🔴 外資與投信連續 3 天同步大賣，代表法人大戶正在撤退，不要隨便接刀子！" if chip_val == -1 else "⚪ 法人有買有賣沒有共識，或者目前籌碼方向不明確。")
    if df_chip_raw.empty:
        chip_detail = "⚠️ 籌碼資料庫暫無回應，以中性 (0分) 處理"
        chip_val = 0
        
    st.markdown(f"""
    <div style="overflow-x: auto;">
        <table class="factor-table">
            <thead>
                <tr>
                    <th style="width: 25%;">分析指標 (做啥用的)</th>
                    <th style="width: 15%;">今日燈號</th>
                    <th style="width: 12%;">比重權重</th>
                    <th style="width: 13%;">加權分數</th>
                    <th style="width: 35%;">當前狀態診斷 (大白話解讀)</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><b>1. 趨勢方向 (Trend)</b><br><span style="color:#94a3b8; font-size:0.75rem;">(看股價有沒有站在均線上)</span></td>
                    <td>{get_badge(trend_val)}</td>
                    <td>{w_trend:.1f}</td>
                    <td style="font-weight: 700; color: {'#10b981' if trend_val*w_trend > 0 else ('#ef4444' if trend_val*w_trend < 0 else '#94a3b8')};">{trend_val*w_trend:+.1f}</td>
                    <td style="color: #cbd5e1; font-size: 0.85rem; line-height: 1.4;">{trend_detail}</td>
                </tr>
                <tr>
                    <td><b>2. 便宜/貴通道 (Space)</b><br><span style="color:#94a3b8; font-size:0.75rem;">(股價現在是便宜還是太貴)</span></td>
                    <td>{get_badge(space_val)}</td>
                    <td>{w_space:.1f}</td>
                    <td style="font-weight: 700; color: {'#10b981' if space_val*w_space > 0 else ('#ef4444' if space_val*w_space < 0 else '#94a3b8')};">{space_val*w_space:+.1f}</td>
                    <td style="color: #cbd5e1; font-size: 0.85rem; line-height: 1.4;">{space_detail}</td>
                </tr>
                <tr>
                    <td><b>3. 多空力量 (MACD)</b><br><span style="color:#94a3b8; font-size:0.75rem;">(股價漲跌的力道強不強)</span></td>
                    <td>{get_badge(macd_val)}</td>
                    <td>{w_momentum:.1f}</td>
                    <td style="font-weight: 700; color: {'#10b981' if macd_val*w_momentum > 0 else ('#ef4444' if macd_val*w_momentum < 0 else '#94a3b8')};">{macd_val*w_momentum:+.1f}</td>
                    <td style="color: #cbd5e1; font-size: 0.85rem; line-height: 1.4;">{macd_detail}</td>
                </tr>
                <tr>
                    <td><b>4. 成交爆量 (Force)</b><br><span style="color:#94a3b8; font-size:0.75rem;">(今日買氣熱不熱、有沒有爆量)</span></td>
                    <td>{get_badge(force_val)}</td>
                    <td>{w_force:.1f}</td>
                    <td style="font-weight: 700; color: {'#10b981' if force_val*w_force > 0 else ('#ef4444' if force_val*w_force < 0 else '#94a3b8')};">{force_val*w_force:+.1f}</td>
                    <td style="color: #cbd5e1; font-size: 0.85rem; line-height: 1.4;">{force_detail}</td>
                </tr>
                <tr>
                    <td><b>5. 法人籌碼 (Chip)</b><br><span style="color:#94a3b8; font-size:0.75rem;">(外資跟投信有沒有偷偷在買)</span></td>
                    <td>{get_badge(chip_val)}</td>
                    <td>{w_chip:.1f}</td>
                    <td style="font-weight: 700; color: {'#10b981' if chip_val*w_chip > 0 else ('#ef4444' if chip_val*w_chip < 0 else '#94a3b8')};">{chip_val*w_chip:+.1f}</td>
                    <td style="color: #cbd5e1; font-size: 0.85rem; line-height: 1.4;">{chip_detail}</td>
                </tr>
            </tbody>
        </table>
    </div>
    """, unsafe_allow_html=True)

# Footer disclaimer & developer info
st.markdown("""
<div class="info-footer">
    台股紅綠燈綜合量化看盤系統 &copy; 2026 | 量化交易策略僅供學術研究與模擬參考，並不構成任何投資買賣建議。市場有風險，投資需謹慎！<br>
    數據來源：Yahoo Finance API 與 證交所公開資料 (FinMind Open API). 本程式所引用之 API 皆為免費公共管道，完全無收費項目。
</div>
""", unsafe_allow_html=True)
