import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time

# Import custom modules
import data_service as ds
import trading_signals as ts
import technical_indicators as ti
import visualization as viz
import prediction_models as pm

# --- Asset Mapping ---
# Maps user-friendly names to yfinance symbols
ASSET_MAP = {
    # Forex Majors
    "EUR/USD": "EURUSD=X", "USD/JPY": "USDJPY=X", "GBP/USD": "GBPUSD=X",
    "USD/CHF": "USDCHF=X", "AUD/USD": "AUDUSD=X", "USD/CAD": "USDCAD=X",
    "NZD/USD": "NZDUSD=X",
    # Forex Minors
    "EUR/GBP": "EURGBP=X", "EUR/JPY": "EURJPY=X", "GBP/JPY": "GBPJPY=X",
    "CHF/JPY": "CHFJPY=X", "EUR/AUD": "EURAUD=X", "AUD/JPY": "AUDJPY=X",
    "CAD/JPY": "CADJPY=X", "GBP/CAD": "GBPCAD=X", "EUR/CAD": "EURCAD=X",
    "AUD/CAD": "AUDCAD=X", "NZD/JPY": "NZDJPY=X", "GBP/CHF": "GBPCHF=X",
    "AUD/NZD": "AUDNZD=X",
    # Forex Exotics (Examples)
    "USD/SGD": "USDSGD=X", "USD/HKD": "USDHKD=X", "USD/ZAR": "USDZAR=X",
    "EUR/TRY": "EURTRY=X", "USD/MXN": "USDMXN=X",
    # Crypto Majors
    "BTC-USD": "BTC-USD", "ETH-USD": "ETH-USD", "BNB-USD": "BNB-USD",
    "SOL-USD": "SOL-USD", "XRP-USD": "XRP-USD", "ADA-USD": "ADA-USD",
    "AVAX-USD": "AVAX-USD", "DOGE-USD": "DOGE-USD", "DOT-USD": "DOT-USD",
    "LINK-USD": "LINK-USD",
    # Crypto Minors/Altcoins
    "SHIB-USD": "SHIB-USD", "VET-USD": "VET-USD", "HBAR-USD": "HBAR-USD",
    "STX-USD": "STX-USD", "ARB-USD": "ARB-USD", "OP-USD": "OP-USD",
    "FTM-USD": "FTM-USD", "NEAR-USD": "NEAR-USD", "RNDR-USD": "RNDR-USD",
    "APT-USD": "APT-USD",
    # Stock Majors
    "AAPL": "AAPL", "MSFT": "MSFT", "AMZN": "AMZN", "GOOGL": "GOOGL",
    "TSLA": "TSLA", "META": "META", "NVDA": "NVDA", "BRK-B": "BRK-B", # Using B shares for Berkshire
    "JNJ": "JNJ", "V": "V",
    # Stock Minors/Popular Growth
    "PLTR": "PLTR", "RIVN": "RIVN", "LCID": "LCID", "ZM": "ZM",
    "ROKU": "ROKU", "COIN": "COIN", "SNOW": "SNOW", "SQ": "SQ",
    "HOOD": "HOOD", "DKNG": "DKNG",
    # Example Commodity
    "Gold": "GC=F", "Silver": "SI=F", "Crude Oil": "CL=F"
}

# Inverse map for displaying yfinance symbols from user input if not in map
INV_ASSET_MAP = {v: k for k, v in ASSET_MAP.items()}

# Default assets to display: Use ALL friendly names from the map
DEFAULT_ASSETS = list(ASSET_MAP.keys())

# --- Helper Functions ---
def get_yfinance_symbol(friendly_name):
    """Gets the yfinance symbol for a user-friendly name."""
    return ASSET_MAP.get(friendly_name, friendly_name) # Return original if not found

def get_friendly_name(yfinance_symbol):
    """Gets the user-friendly name for a yfinance symbol."""
    return INV_ASSET_MAP.get(yfinance_symbol, yfinance_symbol) # Return original if not found


# Page configuration
st.set_page_config(
    page_title="BeeHive Analysis - Trading Signals",
    page_icon="🐝",
    layout="wide"
)

# Initialize session state
if 'assets' not in st.session_state:
    # Store friendly names in session state
    st.session_state.assets = DEFAULT_ASSETS
    
if 'last_update' not in st.session_state:
    st.session_state.last_update = datetime.now() - timedelta(minutes=5)

if 'prediction_horizon' not in st.session_state:
    st.session_state.prediction_horizon = 7 # Default prediction horizon

# Main content
st.title("🐝 BeeHive Analysis: Trading Signals")

# Top section for inputs
col1, col2, col3 = st.columns(3)

with col1:
    # Asset selection (using friendly names)
    selected_friendly_asset = st.selectbox(
        "Select Asset",
        st.session_state.assets,
        key="signal_asset",
        format_func=get_friendly_name # Ensure display is friendly name
    )
    # Get the corresponding yfinance symbol for internal use
    selected_yfinance_asset = get_yfinance_symbol(selected_friendly_asset)
    
    # Add custom asset option
    new_asset_input = st.text_input("Or add symbol/name (e.g., BTC-USD, EUR/JPY, AAPL)", help="Enter a valid Yahoo Finance symbol or a known name.")
    if st.button("Add Asset"):
        if new_asset_input:
            # Try to map it, otherwise use the input directly
            yfinance_symbol_to_add = get_yfinance_symbol(new_asset_input)
            friendly_name_to_add = get_friendly_name(yfinance_symbol_to_add)
            
            if friendly_name_to_add not in st.session_state.assets:
                try:
                    # Validate asset by trying to fetch data using yfinance symbol
                    ds.get_asset_data(yfinance_symbol_to_add, '1d', '1d') 
                    st.session_state.assets.append(friendly_name_to_add)
                    st.success(f"{friendly_name_to_add} added!")
                    # Auto-select the new asset
                    st.session_state.signal_asset = friendly_name_to_add 
                    st.rerun()
                except Exception as e:
                    st.error(f"Error adding {new_asset_input}: {str(e)}. Check symbol validity on Yahoo Finance.")
            else:
                st.warning(f"{friendly_name_to_add} is already in the list.")

with col2:
    # Timeframe selection
    timeframe = st.radio(
        "Select Analysis Timeframe",
        ["5m", "15m", "30m", "1h", "4h", "1d"], # Adjusted timeframes
        index=3, # Default to 1h
        horizontal=True
    )
    
    # Period selection (depends on timeframe)
    # Shorter periods for intraday, longer for daily
    if timeframe in ["5m", "15m", "30m", "1h", "4h"]:
        period = st.radio(
            "Data Period (Intraday)",
            ["1d", "5d", "1mo"],
            index = 1, # Default 5d
            horizontal=True,
            help="How far back to fetch intraday data (Max 60 days usually)"
        )
    else: # Daily timeframe
         period = st.radio(
            "Data Period (Daily)",
            ["1mo", "3mo", "6mo", "1y", "2y", "5y"],
            index=3, # Default 1y
            horizontal=True,
            help="How far back to fetch daily data"
        )

    # Prediction Horizon
    st.session_state.prediction_horizon = st.slider(
        "Prediction Horizon (Days)", 
        min_value=1, 
        max_value=30, 
        value=st.session_state.prediction_horizon,
        help="How many days into the future to predict (uses daily data)"
    )

with col3:
    # Current price display
    try:
        current_data = ds.get_current_price(selected_yfinance_asset)
        st.metric(
            label=f"Current Price ({get_friendly_name(selected_yfinance_asset)})", 
            value=f"{current_data['price']:.4f}",
            delta=f"{current_data['change_percent']:.2f}%"
        )
    except Exception as e:
        st.error(f"Price Error: {str(e)}")
    
    # Generate signal button
    signal_button = st.button("🐝 GET ANALYSIS & PREDICTION", type="primary", use_container_width=True)
    
    # Last updated timestamp
    st.caption(f"Last update: {st.session_state.last_update.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Manual refresh button
    if st.button("Refresh Data", use_container_width=True):
        st.session_state.last_update = datetime.now()
        st.rerun()

# --- Global variable to track if signal button was clicked ---
generate_signal_clicked = signal_button

# Display signal if button is clicked
if generate_signal_clicked:
    try:
        st.markdown("---") # Add a separator
        analysis_col, prediction_col = st.columns(2)
        
        # Use selected_yfinance_asset for all data fetching and analysis
        asset_display_name = get_friendly_name(selected_yfinance_asset)
        tp = None # Initialize TP
        sl = None # Initialize SL

        with analysis_col:
            st.subheader(f"Signal Analysis ({asset_display_name} | {timeframe} / {period})")
            with st.spinner(f"Analyzing {asset_display_name}..."):
                # Fetch data for analysis timeframe
                df = ds.get_asset_data(selected_yfinance_asset, timeframe, period)
                
                if df.empty or len(df) < 20:
                    st.warning(f"Limited data ({len(df)} points) for {asset_display_name} ({timeframe}/{period}). Analysis may be unreliable.")
                    st.stop() # Stop execution if not enough data for analysis
                
                # --- Add Indicators (including ATR) ---
                df = ti.add_sma(df, 20, 50)
                df = ti.add_rsi(df, 14)
                df = ti.add_macd(df)
                df = ti.add_bollinger_bands(df, 20)
                df = ti.add_atr(df, 14) 
                latest = df.iloc[-1]

                # --- TP/SL Calculation ---
                latest_atr = latest.get('ATR_14', 0)
                latest_price = latest.get('Close', 0)
                atr_multiplier_tp = 1.5 
                atr_multiplier_sl = 1.0

                # --- Generate Trading Signal ---
                advice = ts.generate_trading_advice(selected_yfinance_asset, df)
                rec = advice["recommendation"]
                strength = advice["strength"]
                
                if latest_price > 0 and latest_atr > 0: # Only calc if valid price/ATR
                    if rec == "BUY":
                        tp = latest_price + atr_multiplier_tp * latest_atr
                        sl = latest_price - atr_multiplier_sl * latest_atr
                    elif rec == "SELL":
                        tp = latest_price - atr_multiplier_tp * latest_atr
                        sl = latest_price + atr_multiplier_sl * latest_atr
                
                # --- Display Recommendation & TP/SL ---
                if rec == "BUY": color, emoji = "green", "🟢"
                elif rec == "SELL": color, emoji = "red", "🔴"
                else: color, emoji = "orange", "🟠"
                atr_display = f"{latest_atr:.4f}" if latest_atr > 0 else "N/A"
                
                # Prepare TP/SL strings for cleaner display
                tp_string = f'<p style="text-align: center; font-size: 1.1em; margin-bottom: 5px; color: green;"><b>TP:</b> {tp:.4f}</p>' if tp is not None else ''
                sl_string = f'<p style="text-align: center; font-size: 1.1em; margin-bottom: 10px; color: red;"><b>SL:</b> {sl:.4f}</p>' if sl is not None else ''
                
                # Prepare Entry Trigger string
                entry_trigger_string = ""
                sl_display = f"{sl:.4f}" if sl is not None else "N/A"
                if rec == "BUY":
                    entry_trigger_string = f'<p style="text-align: center; font-size: 1.0em; margin-bottom: 8px;"><b>Entry Trigger:</b> Monitor <b>{timeframe} chart</b> near SL ({sl_display}) for bullish confirmation.</p>'
                elif rec == "SELL":
                    entry_trigger_string = f'<p style="text-align: center; font-size: 1.0em; margin-bottom: 8px;"><b>Entry Trigger:</b> Monitor <b>{timeframe} chart</b> near SL ({sl_display}) for bearish confirmation.</p>'
                else: # HOLD
                     entry_trigger_string = f'<p style="text-align: center; font-size: 1.0em; margin-bottom: 8px;"><b>Entry Trigger:</b> No clear entry signal. Wait for setup.</p>'       

                st.markdown(f"""
                <div style="padding: 15px; border-radius: 10px; background-color: {color}20; border: 2px solid {color}; margin-bottom: 15px;">
                    <h2 style="text-align: center; color: {color}; margin-bottom: 5px;">{emoji} {rec} {emoji}</h2>
                    <h4 style="text-align: center; margin-bottom: 10px;">Signal Strength: {strength:.1f}%</h4>
                    {entry_trigger_string}
                    {tp_string} 
                    {sl_string} 
                    <p style="text-align: center; font-size: 0.9em; margin-bottom: 0;">Analysis: {timeframe}/{period} | ATR(14): {atr_display}</p>
                </div>
                """, unsafe_allow_html=True)
                    
                st.markdown("**Analysis Reasoning:**")
                for reason in advice["reasoning"]:
                    st.markdown(f"- {reason}")

                st.markdown("**Current Indicator Values:**")
                # Prepare indicators for display
                analysis_df = df.copy()
                analysis_df = ti.add_sma(analysis_df, 20, 50)
                analysis_df = ti.add_rsi(analysis_df, 14)
                analysis_df = ti.add_macd(analysis_df)
                latest = analysis_df.iloc[-1]
                
                col_ind1, col_ind2 = st.columns(2)
                with col_ind1:
                    rsi_val = latest.get('RSI_14', float('nan'))
                    st.metric("RSI (14)", f"{rsi_val:.2f}", 
                              delta="Overbought" if rsi_val > 70 else ("Oversold" if rsi_val < 30 else "Neutral"),
                              delta_color="inverse")
                
                with col_ind2:
                    macd_val = latest.get('MACD', float('nan'))
                    signal_val = latest.get('MACD_Signal', float('nan'))
                    if pd.notna(macd_val) and pd.notna(signal_val):
                        macd_signal_diff = macd_val - signal_val
                        st.metric("MACD Diff", f"{macd_signal_diff:.4f}", 
                                  delta="Bullish" if macd_signal_diff > 0 else ("Bearish" if macd_signal_diff < 0 else "Neutral"))
                    else:
                        st.metric("MACD Diff", "N/A")

        with prediction_col:
            st.subheader(f"Price Prediction ({asset_display_name} | {st.session_state.prediction_horizon} Days)")
            with st.spinner(f"Generating {st.session_state.prediction_horizon}-day prediction..."):
                try:
                    # Fetch daily data for prediction (use yfinance symbol)
                    pred_df_hist = ds.get_asset_data(selected_yfinance_asset, "1d", "2y") # Use 2 years of daily data for better prediction
                    
                    if pred_df_hist.empty or len(pred_df_hist) < 60: # Increased requirement for prophet
                         st.warning(f"Not enough daily data ({len(pred_df_hist)} points) for prediction. Need at least 60.")
                         st.markdown("**Entry Suggestion:** Prediction unavailable.")
                         accuracy = None
                         forecast_df = pd.DataFrame() # Empty dataframe
                    else:
                        # Perform prediction using Prophet
                        forecast_df, accuracy = pm.prophet_forecast(pred_df_hist, st.session_state.prediction_horizon)
                        
                        # Display prediction chart
                        fig_pred = viz.plot_forecast(forecast_df, asset_display_name)
                        st.plotly_chart(fig_pred, use_container_width=True)
                        
                    # --- Entry Point Suggestion Logic ---
                    st.markdown("**Entry Suggestion (Based on Daily Prediction & Signal):**")
                    entry_suggestion = "Hold/Neutral position suggested based on current analysis." 
                    sl_display = f"{sl:.4f}" if sl is not None else "N/A"
                    
                    if not forecast_df.empty:
                        # Get the last actual price and the future predicted prices
                        last_actual_price = pred_df_hist['Close'].iloc[-1]
                        future_predictions = forecast_df[forecast_df['ds'] > pred_df_hist.index.max().tz_localize(None)] # Compare timezone naive
                    
                        if rec == "BUY":
                            potential_lows = future_predictions[future_predictions['yhat_lower'] < last_actual_price]
                            if not potential_lows.empty:
                                best_low_date = potential_lows['ds'].iloc[0].strftime('%Y-%m-%d')
                                entry_suggestion = f"Prediction suggests potential lows around **{best_low_date}**. Monitor the **{timeframe} chart** near the SL level (**{sl_display}**) for bullish confirmation before entry."
                            else:
                                entry_suggestion = f"Prediction shows no immediate lower lows. Monitor the **{timeframe} chart** near the SL level (**{sl_display}**) for bullish confirmation before entry."
                        
                        elif rec == "SELL":
                            potential_highs = future_predictions[future_predictions['yhat_upper'] > last_actual_price]
                            if not potential_highs.empty:
                                best_high_date = potential_highs['ds'].iloc[0].strftime('%Y-%m-%d')
                                entry_suggestion = f"Prediction suggests potential highs around **{best_high_date}**. Monitor the **{timeframe} chart** near the SL level (**{sl_display}**) for bearish confirmation before entry."
                            else:
                                entry_suggestion = f"Prediction shows no immediate higher highs. Monitor the **{timeframe} chart** near the SL level (**{sl_display}**) for bearish confirmation before entry."
                    else: 
                        # If prediction failed or not enough data
                        if rec == "BUY": entry_suggestion = f"Prediction unavailable. Monitor the **{timeframe} chart** near the SL level (**{sl_display}**) for bullish confirmation before entry."
                        elif rec == "SELL": entry_suggestion = f"Prediction unavailable. Monitor the **{timeframe} chart** near the SL level (**{sl_display}**) for bearish confirmation before entry."
                        else: entry_suggestion = "No clear signal. Prediction unavailable. Wait for clearer setup."

                    st.info(entry_suggestion)
                    if accuracy is not None:
                       st.caption(f"Prediction Model Accuracy (Daily MAPE): {accuracy:.2f}% (Lower is better)")
                    else:
                       st.caption("Prediction accuracy could not be calculated.")
                        
                except Exception as pred_e:
                    st.error(f"Error during prediction: {str(pred_e)}")
                    st.markdown("**Entry Suggestion:** Error generating prediction.")

        # --- Technical Analysis Charts (moved outside columns) ---
        st.markdown("---")
        st.subheader(f"Technical Analysis Charts ({asset_display_name} | {timeframe} / {period})")
        
        # Use the initially fetched dataframe 'df' for consistency with signal generation timeframe
        if 'df' in locals() and not df.empty:
            indicator_tabs = st.tabs(["Price + SMA + BB", "RSI", "MACD"])
            
            with indicator_tabs[0]: # Combined Price, SMA, Bollinger Bands
                try:
                    # We already added SMA/BB potentially in signal generation, but recalculate for safety
                    plot_df_sma_bb = df.copy()
                    plot_df_sma_bb = ti.add_sma(plot_df_sma_bb, 20, 50)
                    plot_df_sma_bb = ti.add_bollinger_bands(plot_df_sma_bb, 20)
                    fig_sma_bb = viz.plot_price_with_sma_bb(plot_df_sma_bb, asset_display_name, 20, 50)
                    st.plotly_chart(fig_sma_bb, use_container_width=True)
                except Exception as chart_e:
                    st.warning(f"Could not plot Price/SMA/BB: {chart_e}")
                
            with indicator_tabs[1]: # RSI
                try:
                    plot_df_rsi = df.copy()
                    plot_df_rsi = ti.add_rsi(plot_df_rsi, 14)
                    fig_rsi = viz.plot_rsi(plot_df_rsi, 14)
                    st.plotly_chart(fig_rsi, use_container_width=True)
                except Exception as chart_e:
                    st.warning(f"Could not plot RSI: {chart_e}")
                
            with indicator_tabs[2]: # MACD
                try:
                    plot_df_macd = df.copy()
                    plot_df_macd = ti.add_macd(plot_df_macd)
                    fig_macd = viz.plot_macd(plot_df_macd)
                    st.plotly_chart(fig_macd, use_container_width=True)
                except Exception as chart_e:
                    st.warning(f"Could not plot MACD: {chart_e}")
                
        else:
             st.warning("No analysis data available to plot technical indicators.")
            
    except Exception as e:
        st.error(f"An error occurred during analysis: {str(e)}")
        st.exception(e) # Show full traceback for debugging

else:
    # Default display when page loads
    st.info("👆 Select asset, timeframe, and prediction horizon, then click 'GET ANALYSIS & PREDICTION'.")
    
    # Show a sample list of available assets
    st.subheader("Default Assets")
    st.write("Analyze default assets or add your own yfinance symbol/name:")
    
    # Display available assets in clickable buttons
    asset_cols = st.columns(4) # Adjust number of columns as needed
    for i, friendly_asset_name in enumerate(st.session_state.assets):
        if asset_cols[i % 4].button(
            friendly_asset_name, 
            key=f"asset_button_{i}",
            on_click=lambda name=friendly_asset_name: st.session_state.update({"signal_asset": name}),
            use_container_width=True
        ):
            pass # Callback handles the selection

# Auto-refresh data every 5 minutes (increased interval)
if (datetime.now() - st.session_state.last_update).total_seconds() > 300:
    # Only rerun if a signal was previously generated to avoid rerunning on first load
    if generate_signal_clicked:
        st.session_state.last_update = datetime.now()
        st.rerun()