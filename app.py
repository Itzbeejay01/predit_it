import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time

# Import custom modules
import data_service as ds
import prediction_models as pm
import technical_indicators as ti
import visualization as viz
import alerts as al
import trading_signals as ts

# Page configuration
st.set_page_config(
    page_title="Forex & Crypto Prediction App",
    page_icon="📈",
    layout="wide"
)

# Initialize session state
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = ['BTC-USD', 'ETH-USD', 'EUR/USD', 'GBP/USD', 'USD/JPY']
    
if 'alerts' not in st.session_state:
    st.session_state.alerts = []
    
if 'last_update' not in st.session_state:
    st.session_state.last_update = datetime.now() - timedelta(minutes=10)
    
if 'prediction_horizon' not in st.session_state:
    st.session_state.prediction_horizon = 7  # Default prediction for 7 days

# Function to update data
def update_data():
    st.session_state.last_update = datetime.now()
    st.rerun()

# Sidebar
with st.sidebar:
    st.title("Settings")
    
    # Asset Management
    st.subheader("Asset Management")
    
    # Add new asset
    new_asset = st.text_input("Add new asset (e.g., BTC-USD, EUR/USD)")
    
    if st.button("Add to Watchlist"):
        if new_asset and new_asset not in st.session_state.watchlist:
            try:
                # Validate the asset by trying to fetch data
                ds.get_asset_data(new_asset, '1d', '7d')
                st.session_state.watchlist.append(new_asset)
                st.success(f"{new_asset} added to watchlist!")
            except Exception as e:
                st.error(f"Error adding {new_asset}: {str(e)}")
    
    # Display and manage watchlist
    st.subheader("Watchlist")
    for idx, asset in enumerate(st.session_state.watchlist):
        col1, col2 = st.columns([4, 1])
        with col1:
            st.write(asset)
        with col2:
            if st.button("Remove", key=f"remove_{idx}"):
                st.session_state.watchlist.remove(asset)
                st.rerun()
    
    # Prediction settings
    st.subheader("Prediction Settings")
    st.session_state.prediction_horizon = st.slider(
        "Prediction Horizon (Days)", 
        min_value=1, 
        max_value=30, 
        value=st.session_state.prediction_horizon
    )
    
    # Alerts settings
    st.subheader("Price Alerts")
    alert_asset = st.selectbox("Select Asset", st.session_state.watchlist)
    alert_type = st.radio("Alert Type", ["Above", "Below"])
    alert_price = st.number_input("Price", min_value=0.0, step=0.01)
    
    if st.button("Set Alert"):
        alert = {
            "asset": alert_asset,
            "type": alert_type,
            "price": alert_price,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        st.session_state.alerts.append(alert)
        st.success(f"Alert set for {alert_asset} {alert_type.lower()} {alert_price}!")
    
    # Data refresh button
    st.subheader("Data Management")
    if st.button("Refresh Data"):
        update_data()
    
    st.write(f"Last update: {st.session_state.last_update.strftime('%Y-%m-%d %H:%M:%S')}")

# Main content
st.title("Forex & Crypto Prediction Dashboard")

# Tabs for different sections
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🔍 Market Overview", 
    "📊 Asset Analysis", 
    "🔮 Predictions", 
    "⚠️ Alerts",
    "💰 Trading Signals"
])

# Tab 1: Market Overview
with tab1:
    st.header("Market Overview")
    
    # Fetch current data for all assets in watchlist
    overview_data = {}
    
    # Display progress bar while fetching data
    with st.spinner("Fetching latest market data..."):
        for asset in st.session_state.watchlist:
            try:
                data = ds.get_current_price(asset)
                overview_data[asset] = data
            except Exception as e:
                st.error(f"Error fetching data for {asset}: {str(e)}")
    
    # Create columns for assets
    cols = st.columns(len(st.session_state.watchlist))
    
    # Display data for each asset
    for i, asset in enumerate(st.session_state.watchlist):
        if asset in overview_data:
            with cols[i]:
                data = overview_data[asset]
                st.metric(
                    label=asset,
                    value=f"{data['price']:.4f}",
                    delta=f"{data['change_percent']:.2f}%"
                )
    
    # Market heat map
    st.subheader("Price Change Heat Map")
    try:
        heatmap_data = {}
        for asset in st.session_state.watchlist:
            if asset in overview_data:
                heatmap_data[asset] = overview_data[asset]['change_percent']
        
        # Create and display heat map
        if heatmap_data:
            fig = viz.create_heatmap(heatmap_data)
            st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Error creating heat map: {str(e)}")

# Tab 2: Asset Analysis
with tab2:
    st.header("Asset Analysis")
    
    # Select asset
    selected_asset = st.selectbox("Select Asset for Analysis", st.session_state.watchlist)
    
    # Select timeframe
    col1, col2 = st.columns(2)
    with col1:
        period = st.selectbox(
            "Select Period", 
            ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "ytd", "max"]
        )
    with col2:
        interval = st.selectbox(
            "Select Interval", 
            ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"]
        )
    
    # Fetch and display data
    try:
        with st.spinner(f"Fetching data for {selected_asset}..."):
            df = ds.get_asset_data(selected_asset, interval, period)
            
            # Price chart
            st.subheader("Price Chart")
            fig = viz.plot_candlestick(df, selected_asset)
            st.plotly_chart(fig, use_container_width=True)
            
            # Technical indicators
            st.subheader("Technical Indicators")
            indicator_options = ['SMA', 'EMA', 'RSI', 'MACD', 'Bollinger Bands']
            selected_indicators = st.multiselect("Select Indicators", indicator_options)
            
            for indicator in selected_indicators:
                if indicator == 'SMA':
                    period1 = st.slider("SMA Period 1", 5, 200, 20)
                    period2 = st.slider("SMA Period 2", 5, 200, 50)
                    df = ti.add_sma(df, period1, period2)
                    fig = viz.plot_with_sma(df, selected_asset, period1, period2)
                    st.plotly_chart(fig, use_container_width=True)
                
                elif indicator == 'EMA':
                    period = st.slider("EMA Period", 5, 200, 20)
                    df = ti.add_ema(df, period)
                    fig = viz.plot_with_ema(df, selected_asset, period)
                    st.plotly_chart(fig, use_container_width=True)
                
                elif indicator == 'RSI':
                    period = st.slider("RSI Period", 5, 30, 14)
                    df = ti.add_rsi(df, period)
                    fig = viz.plot_rsi(df, period)
                    st.plotly_chart(fig, use_container_width=True)
                
                elif indicator == 'MACD':
                    df = ti.add_macd(df)
                    fig = viz.plot_macd(df)
                    st.plotly_chart(fig, use_container_width=True)
                
                elif indicator == 'Bollinger Bands':
                    period = st.slider("Bollinger Bands Period", 5, 50, 20)
                    df = ti.add_bollinger_bands(df, period)
                    fig = viz.plot_with_bollinger_bands(df, selected_asset, period)
                    st.plotly_chart(fig, use_container_width=True)
    
    except Exception as e:
        st.error(f"Error analyzing {selected_asset}: {str(e)}")

# Tab 3: Predictions
with tab3:
    st.header("Price Predictions")
    
    pred_asset = st.selectbox("Select Asset for Prediction", st.session_state.watchlist, key="pred_asset")
    
    # Model selection
    model_type = st.radio("Select Prediction Model", ["Linear Regression", "Prophet", "ARIMA"])
    
    try:
        # Fetch historical data for prediction
        with st.spinner(f"Fetching data for {pred_asset}..."):
            # For predictions, we use daily data with a longer period
            pred_df = ds.get_asset_data(pred_asset, "1d", "1y")
            
            if len(pred_df) < 30:
                st.warning(f"Not enough historical data for {pred_asset}. Need at least 30 data points.")
            else:
                # Perform prediction
                with st.spinner("Generating prediction..."):
                    if model_type == "Linear Regression":
                        forecast_df, accuracy = pm.linear_regression_forecast(
                            pred_df, 
                            st.session_state.prediction_horizon
                        )
                        
                    elif model_type == "Prophet":
                        forecast_df = pm.prophet_forecast(
                            pred_df, 
                            st.session_state.prediction_horizon
                        )
                        accuracy = None  # Prophet doesn't provide simple accuracy metrics
                        
                    elif model_type == "ARIMA":
                        forecast_df, accuracy = pm.arima_forecast(
                            pred_df, 
                            st.session_state.prediction_horizon
                        )
                
                # Display prediction results
                st.subheader(f"{pred_asset} Price Prediction ({st.session_state.prediction_horizon} days)")
                
                if accuracy is not None:
                    st.metric("Model Accuracy", f"{accuracy:.2f}%")
                
                # Plot historical data with prediction
                fig = viz.plot_prediction(pred_df, forecast_df, pred_asset, model_type)
                st.plotly_chart(fig, use_container_width=True)
                
                # Show prediction data in a table
                st.subheader("Predicted Values")
                st.dataframe(forecast_df)
                
                # Download prediction as CSV
                csv = forecast_df.to_csv(index=True)
                st.download_button(
                    label="Download Prediction Data",
                    data=csv,
                    file_name=f"{pred_asset}_{model_type}_prediction.csv",
                    mime="text/csv"
                )
    
    except Exception as e:
        st.error(f"Error generating prediction: {str(e)}")

# Tab 4: Alerts
with tab4:
    st.header("Price Alerts")
    
    # Display existing alerts
    if not st.session_state.alerts:
        st.info("No alerts set. Use the sidebar to create alerts.")
    else:
        # Check for triggered alerts
        triggered_alerts = []
        for i, alert in enumerate(st.session_state.alerts):
            try:
                current_price = ds.get_current_price(alert["asset"])["price"]
                triggered = al.check_alert(alert, current_price)
                
                if triggered:
                    triggered_alerts.append(i)
                    st.warning(f"⚠️ ALERT TRIGGERED: {alert['asset']} is {alert['type'].lower()} {alert['price']} (Current: {current_price:.4f})")
            except Exception as e:
                st.error(f"Error checking alert for {alert['asset']}: {str(e)}")
        
        # Remove triggered alerts (in reverse to avoid index issues)
        for i in sorted(triggered_alerts, reverse=True):
            del st.session_state.alerts[i]
        
        # Display active alerts
        st.subheader("Active Alerts")
        
        for i, alert in enumerate(st.session_state.alerts):
            col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
            
            with col1:
                st.write(alert["asset"])
            with col2:
                st.write(f"{alert['type']} {alert['price']}")
            with col3:
                st.write(f"Created: {alert['created_at']}")
            with col4:
                if st.button("Delete", key=f"del_alert_{i}"):
                    st.session_state.alerts.pop(i)
                    st.rerun()

# Tab 5: Trading Signals
with tab5:
    st.header("Trading Signals")
    
    signal_asset = st.selectbox("Select Asset for Trading Signal", st.session_state.watchlist, key="signal_asset")
    
    # Choose time period for analysis
    signal_period = st.select_slider(
        "Analysis Period",
        options=["1mo", "3mo", "6mo", "1y"], 
        value="3mo"
    )
    
    # Generate trading signal button
    if st.button("🔄 Generate Trading Signal", type="primary"):
        try:
            with st.spinner(f"Analyzing {signal_asset}..."):
                # Fetch data for trading signal analysis
                signal_df = ds.get_asset_data(signal_asset, "1d", signal_period)
                
                if len(signal_df) < 50:
                    st.warning(f"Limited historical data for {signal_asset}. Analysis may be less reliable.")
                
                # Generate trading advice
                advice = ts.generate_trading_advice(signal_asset, signal_df)
                
                # Display recommendation
                rec = advice["recommendation"]
                strength = advice["strength"]
                
                # Determine color based on recommendation
                if rec == "BUY":
                    color = "green"
                    emoji = "🟢"
                elif rec == "SELL":
                    color = "red"
                    emoji = "🔴"
                else:
                    color = "orange"
                    emoji = "🟠"
                
                # Display recommendation card
                st.markdown(f"""
                <div style="padding: 20px; border-radius: 10px; background-color: {color}20; border: 1px solid {color};">
                    <h1 style="text-align: center; color: {color};">{emoji} {rec} {emoji}</h1>
                    <h3 style="text-align: center;">Signal Strength: {strength:.1f}%</h3>
                </div>
                """, unsafe_allow_html=True)
                
                # Show reasoning
                st.subheader("Analysis Reasoning")
                for reason in advice["reasoning"]:
                    st.markdown(f"- {reason}")
                
                # Display current price
                current_price = ds.get_current_price(signal_asset)["price"]
                st.metric("Current Price", f"{current_price:.4f}")
                
                # Show technical indicators used in the analysis
                analysis_df = signal_df.copy()
                analysis_df = ti.add_sma(analysis_df, 20, 50)
                analysis_df = ti.add_ema(analysis_df, 20)
                analysis_df = ti.add_rsi(analysis_df, 14)
                analysis_df = ti.add_macd(analysis_df)
                analysis_df = ti.add_bollinger_bands(analysis_df, 20)
                
                # Display charts with indicators
                st.subheader("Technical Analysis")
                
                # SMA Chart
                fig_sma = viz.plot_with_sma(analysis_df, f"{signal_asset} with SMA", 20, 50)
                st.plotly_chart(fig_sma, use_container_width=True)
                
                # RSI Chart
                fig_rsi = viz.plot_rsi(analysis_df, 14)
                st.plotly_chart(fig_rsi, use_container_width=True)
                
                # MACD Chart
                fig_macd = viz.plot_macd(analysis_df)
                st.plotly_chart(fig_macd, use_container_width=True)
                
                # Bollinger Bands Chart
                fig_bb = viz.plot_with_bollinger_bands(analysis_df, f"{signal_asset} with Bollinger Bands", 20)
                st.plotly_chart(fig_bb, use_container_width=True)
                
        except Exception as e:
            st.error(f"Error generating trading signal for {signal_asset}: {str(e)}")
    else:
        st.info("Click the button above to generate a trading signal based on technical analysis.")

# Auto-refresh data every 5 minutes
if (datetime.now() - st.session_state.last_update).total_seconds() > 300:
    update_data()
