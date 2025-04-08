import pandas as pd
import numpy as np
import yfinance as yf
import ccxt
import requests
from datetime import datetime, timedelta
import time

def get_asset_data(symbol, interval='1d', period='1mo'):
    """
    Fetch historical data for a given asset from Yahoo Finance
    
    Parameters:
    symbol (str): Asset symbol (e.g., 'BTC-USD', 'EUR/USD')
    interval (str): Data interval (e.g., '1d', '1h')
    period (str): Data period (e.g., '1mo', '1y')
    
    Returns:
    pandas.DataFrame: Historical data for the asset
    """
    try:
        # Convert forex symbols to Yahoo Finance format
        if '/' in symbol:
            base, quote = symbol.split('/')
            symbol = f"{base}{quote}=X"
        
        # Fetch data from Yahoo Finance
        data = yf.Ticker(symbol).history(period=period, interval=interval)
        
        # Ensure we have expected columns
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in required_cols:
            if col not in data.columns:
                if col == 'Volume' and 'X' in symbol:  # For forex pairs, volume might be missing
                    data['Volume'] = 0
                else:
                    raise ValueError(f"Missing required column: {col}")
        
        # Drop any rows with NaN in required columns
        data = data.dropna(subset=['Open', 'High', 'Low', 'Close'])
        
        # If empty, raise exception
        if len(data) == 0:
            raise ValueError(f"No data returned for {symbol}")
            
        return data
    
    except Exception as e:
        raise Exception(f"Error fetching data for {symbol}: {str(e)}")

def get_current_price(symbol):
    """
    Get current price and 24h change for an asset
    
    Parameters:
    symbol (str): Asset symbol (e.g., 'BTC-USD', 'EUR/USD')
    
    Returns:
    dict: Current price data including price and percent change
    """
    try:
        # Convert forex symbols to Yahoo Finance format
        if '/' in symbol:
            base, quote = symbol.split('/')
            yf_symbol = f"{base}{quote}=X"
        else:
            yf_symbol = symbol
        
        # Fetch data
        ticker = yf.Ticker(yf_symbol)
        
        # Get price
        current_data = ticker.history(period='2d')
        
        if len(current_data) < 2:
            # If we don't have 2 days of data, just get the latest price
            price = current_data['Close'].iloc[-1]
            prev_price = price  # No change if we only have one data point
        else:
            # Calculate price and change
            price = current_data['Close'].iloc[-1]
            prev_price = current_data['Close'].iloc[-2]
        
        change = price - prev_price
        change_percent = (change / prev_price) * 100 if prev_price != 0 else 0
        
        return {
            'price': price,
            'change': change,
            'change_percent': change_percent
        }
    
    except Exception as e:
        raise Exception(f"Error fetching current price for {symbol}: {str(e)}")

def get_multiple_assets_data(symbols, interval='1d', period='7d'):
    """
    Fetch data for multiple assets
    
    Parameters:
    symbols (list): List of asset symbols
    interval (str): Data interval
    period (str): Data period
    
    Returns:
    dict: Dictionary of DataFrames with asset data
    """
    results = {}
    for symbol in symbols:
        try:
            results[symbol] = get_asset_data(symbol, interval, period)
        except Exception as e:
            # Just log the error but continue with other assets
            print(f"Error fetching {symbol}: {str(e)}")
    
    return results
