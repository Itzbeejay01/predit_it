import pandas as pd
import numpy as np
from technical_indicators import add_sma, add_ema, add_rsi, add_macd, add_bollinger_bands

def analyze_trading_signals(df):
    """
    Analyze multiple technical indicators to generate trading signals
    
    Parameters:
    df (DataFrame): Price data with technical indicators
    
    Returns:
    dict: Dictionary with trading signals and analysis
    """
    # Prepare DataFrame with all needed indicators
    analysis_df = df.copy()
    analysis_df = add_sma(analysis_df, 20, 50)
    analysis_df = add_ema(analysis_df, 20)
    analysis_df = add_rsi(analysis_df, 14)
    analysis_df = add_macd(analysis_df)
    analysis_df = add_bollinger_bands(analysis_df, 20)
    
    # Get the most recent values
    latest = analysis_df.iloc[-1]
    previous = analysis_df.iloc[-2] if len(analysis_df) > 1 else latest
    
    # Signals dictionary
    signals = {
        "current_price": latest["Close"],
        "signals": {},
        "recommendation": None,
        "strength": 0,
        "reasoning": []
    }
    
    # Check SMA crossover (SMA 20 crosses above SMA 50)
    if previous["SMA_20"] <= previous["SMA_50"] and latest["SMA_20"] > latest["SMA_50"]:
        signals["signals"]["sma_crossover"] = "bullish"
        signals["reasoning"].append("SMA 20 crossed above SMA 50 (bullish)")
    elif previous["SMA_20"] >= previous["SMA_50"] and latest["SMA_20"] < latest["SMA_50"]:
        signals["signals"]["sma_crossover"] = "bearish"
        signals["reasoning"].append("SMA 20 crossed below SMA 50 (bearish)")
    
    # Check price relative to SMAs
    if latest["Close"] > latest["SMA_20"] and latest["Close"] > latest["SMA_50"]:
        signals["signals"]["price_above_sma"] = "bullish"
        signals["reasoning"].append("Price above both SMA 20 and SMA 50 (bullish)")
    elif latest["Close"] < latest["SMA_20"] and latest["Close"] < latest["SMA_50"]:
        signals["signals"]["price_above_sma"] = "bearish"
        signals["reasoning"].append("Price below both SMA 20 and SMA 50 (bearish)")
    
    # Check RSI
    if latest["RSI_14"] < 30:
        signals["signals"]["rsi"] = "bullish"
        signals["reasoning"].append(f"RSI is oversold at {latest['RSI_14']:.2f} (bullish)")
    elif latest["RSI_14"] > 70:
        signals["signals"]["rsi"] = "bearish"
        signals["reasoning"].append(f"RSI is overbought at {latest['RSI_14']:.2f} (bearish)")
    
    # Check MACD
    if previous["MACD"] <= previous["MACD_Signal"] and latest["MACD"] > latest["MACD_Signal"]:
        signals["signals"]["macd"] = "bullish"
        signals["reasoning"].append("MACD crossed above signal line (bullish)")
    elif previous["MACD"] >= previous["MACD_Signal"] and latest["MACD"] < latest["MACD_Signal"]:
        signals["signals"]["macd"] = "bearish"
        signals["reasoning"].append("MACD crossed below signal line (bearish)")
    
    # Check Bollinger Bands
    if latest["Close"] < latest["BB_Lower"]:
        signals["signals"]["bollinger"] = "bullish"
        signals["reasoning"].append("Price below lower Bollinger Band, potential bounce (bullish)")
    elif latest["Close"] > latest["BB_Upper"]:
        signals["signals"]["bollinger"] = "bearish"
        signals["reasoning"].append("Price above upper Bollinger Band, potential reversal (bearish)")
    
    # Count bullish and bearish signals
    bullish_count = sum(1 for signal in signals["signals"].values() if signal == "bullish")
    bearish_count = sum(1 for signal in signals["signals"].values() if signal == "bearish")
    
    # Determine overall recommendation
    if bullish_count > bearish_count:
        signals["recommendation"] = "BUY"
        signals["strength"] = bullish_count / (bullish_count + bearish_count) * 100
    elif bearish_count > bullish_count:
        signals["recommendation"] = "SELL"
        signals["strength"] = bearish_count / (bullish_count + bearish_count) * 100
    else:
        signals["recommendation"] = "HOLD"
        signals["strength"] = 50
    
    return signals

def generate_trading_advice(symbol, df):
    """
    Generate trading advice based on technical analysis
    
    Parameters:
    symbol (str): Asset symbol
    df (DataFrame): Price data
    
    Returns:
    dict: Trading advice with recommendation and reasoning
    """
    # Ensure we have enough data
    if len(df) < 50:
        return {
            "recommendation": "HOLD",
            "strength": 0,
            "reasoning": ["Not enough historical data for reliable analysis"]
        }
    
    # Analyze signals
    signals = analyze_trading_signals(df)
    
    # Add symbol to the result
    signals["symbol"] = symbol
    
    return signals