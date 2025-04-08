import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

def plot_candlestick(df, title="Price Chart"):
    """
    Create a candlestick chart from OHLC data
    
    Parameters:
    df (DataFrame): OHLC price data
    title (str): Chart title
    
    Returns:
    Figure: Plotly figure object
    """
    fig = go.Figure(data=[
        go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name="OHLC"
        )
    ])
    
    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title="Price",
        xaxis_rangeslider_visible=False,
        template="plotly_white"
    )
    
    return fig

def plot_with_sma(df, title="Price with SMA", period1=20, period2=50):
    """
    Create a chart with price and SMA lines
    
    Parameters:
    df (DataFrame): Price data with SMA columns
    title (str): Chart title
    period1 (int): First SMA period
    period2 (int): Second SMA period
    
    Returns:
    Figure: Plotly figure object
    """
    fig = go.Figure()
    
    # Add candlestick chart
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name="OHLC"
        )
    )
    
    # Add SMAs
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[f'SMA_{period1}'],
            mode='lines',
            name=f'SMA {period1}',
            line=dict(width=2, color='blue')
        )
    )
    
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[f'SMA_{period2}'],
            mode='lines',
            name=f'SMA {period2}',
            line=dict(width=2, color='red')
        )
    )
    
    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title="Price",
        xaxis_rangeslider_visible=False,
        template="plotly_white"
    )
    
    return fig

def plot_with_ema(df, title="Price with EMA", period=20):
    """
    Create a chart with price and EMA line
    
    Parameters:
    df (DataFrame): Price data with EMA column
    title (str): Chart title
    period (int): EMA period
    
    Returns:
    Figure: Plotly figure object
    """
    fig = go.Figure()
    
    # Add candlestick chart
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name="OHLC"
        )
    )
    
    # Add EMA
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[f'EMA_{period}'],
            mode='lines',
            name=f'EMA {period}',
            line=dict(width=2, color='purple')
        )
    )
    
    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title="Price",
        xaxis_rangeslider_visible=False,
        template="plotly_white"
    )
    
    return fig

def plot_rsi(df, period=14):
    """
    Create an RSI chart
    
    Parameters:
    df (DataFrame): Price data with RSI column
    period (int): RSI period
    
    Returns:
    Figure: Plotly figure object
    """
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.1, row_heights=[0.7, 0.3])
    
    # Add candlestick chart
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name="OHLC"
        ),
        row=1, col=1
    )
    
    # Add RSI
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[f'RSI_{period}'],
            mode='lines',
            name=f'RSI {period}',
            line=dict(width=2, color='orange')
        ),
        row=2, col=1
    )
    
    # Add overbought/oversold lines
    fig.add_trace(
        go.Scatter(
            x=[df.index[0], df.index[-1]],
            y=[70, 70],
            mode='lines',
            name='Overbought',
            line=dict(width=1, color='red', dash='dash')
        ),
        row=2, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=[df.index[0], df.index[-1]],
            y=[30, 30],
            mode='lines',
            name='Oversold',
            line=dict(width=1, color='green', dash='dash')
        ),
        row=2, col=1
    )
    
    fig.update_layout(
        title=f"Price with RSI ({period})",
        xaxis_title="Date",
        yaxis_title="Price",
        xaxis2_title="Date",
        yaxis2_title="RSI",
        xaxis_rangeslider_visible=False,
        template="plotly_white"
    )
    
    # Update y-axis range for RSI
    fig.update_yaxes(range=[0, 100], row=2, col=1)
    
    return fig

def plot_macd(df):
    """
    Create a MACD chart
    
    Parameters:
    df (DataFrame): Price data with MACD columns
    
    Returns:
    Figure: Plotly figure object
    """
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.1, row_heights=[0.7, 0.3])
    
    # Add candlestick chart
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name="OHLC"
        ),
        row=1, col=1
    )
    
    # Add MACD and signal line
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['MACD'],
            mode='lines',
            name='MACD',
            line=dict(width=2, color='blue')
        ),
        row=2, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['MACD_Signal'],
            mode='lines',
            name='Signal Line',
            line=dict(width=2, color='red')
        ),
        row=2, col=1
    )
    
    # Add histogram
    colors = ['green' if val >= 0 else 'red' for val in df['MACD_Histogram']]
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df['MACD_Histogram'],
            name='Histogram',
            marker_color=colors
        ),
        row=2, col=1
    )
    
    fig.update_layout(
        title="Price with MACD",
        xaxis_title="Date",
        yaxis_title="Price",
        xaxis2_title="Date",
        yaxis2_title="MACD",
        xaxis_rangeslider_visible=False,
        template="plotly_white"
    )
    
    return fig

def plot_with_bollinger_bands(df, title="Price with Bollinger Bands", period=20):
    """
    Create a chart with price and Bollinger Bands
    
    Parameters:
    df (DataFrame): Price data with Bollinger Bands columns
    title (str): Chart title
    period (int): Bollinger Bands period
    
    Returns:
    Figure: Plotly figure object
    """
    fig = go.Figure()
    
    # Add candlestick chart
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name="OHLC"
        )
    )
    
    # Add Bollinger Bands
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['BB_Upper'],
            mode='lines',
            name='Upper Band',
            line=dict(width=1, color='rgba(250,128,114,0.7)')
        )
    )
    
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['BB_Middle'],
            mode='lines',
            name='Middle Band',
            line=dict(width=1, color='rgba(0,0,255,0.7)')
        )
    )
    
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['BB_Lower'],
            mode='lines',
            name='Lower Band',
            line=dict(width=1, color='rgba(250,128,114,0.7)')
        )
    )
    
    # Fill between upper and lower bands
    fig.add_trace(
        go.Scatter(
            x=df.index.tolist() + df.index.tolist()[::-1],
            y=df['BB_Upper'].tolist() + df['BB_Lower'].tolist()[::-1],
            fill='toself',
            fillcolor='rgba(173,216,230,0.2)',
            line=dict(width=0),
            name='Bollinger Band Range'
        )
    )
    
    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title="Price",
        xaxis_rangeslider_visible=False,
        template="plotly_white"
    )
    
    return fig

def plot_prediction(historical_df, forecast_df, symbol, model_name):
    """
    Create a chart with historical data and prediction
    
    Parameters:
    historical_df (DataFrame): Historical price data
    forecast_df (DataFrame): Forecast data
    symbol (str): Asset symbol
    model_name (str): Name of the prediction model
    
    Returns:
    Figure: Plotly figure object
    """
    fig = go.Figure()
    
    # Add historical price
    fig.add_trace(
        go.Scatter(
            x=historical_df.index,
            y=historical_df['Close'],
            mode='lines',
            name='Historical Price',
            line=dict(width=2, color='blue')
        )
    )
    
    # Add prediction
    fig.add_trace(
        go.Scatter(
            x=forecast_df.index,
            y=forecast_df['Predicted_Close'],
            mode='lines',
            name='Predicted Price',
            line=dict(width=2, color='red')
        )
    )
    
    # Add prediction confidence interval if available
    if 'Predicted_Lower' in forecast_df.columns and 'Predicted_Upper' in forecast_df.columns:
        fig.add_trace(
            go.Scatter(
                x=forecast_df.index.tolist() + forecast_df.index.tolist()[::-1],
                y=forecast_df['Predicted_Upper'].tolist() + forecast_df['Predicted_Lower'].tolist()[::-1],
                fill='toself',
                fillcolor='rgba(255,0,0,0.2)',
                line=dict(width=0),
                name='Prediction Interval'
            )
        )
    
    # Add a vertical line separating historical and forecast data
    fig.add_vline(
        x=historical_df.index[-1],
        line_width=1,
        line_dash="dash",
        line_color="green",
        annotation_text="Forecast Start",
        annotation_position="top right"
    )
    
    fig.update_layout(
        title=f"{symbol} Price Prediction ({model_name})",
        xaxis_title="Date",
        yaxis_title="Price",
        template="plotly_white",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig

def create_heatmap(data_dict):
    """
    Create a heatmap visualization for comparing performance of multiple assets
    
    Parameters:
    data_dict (dict): Dictionary with asset names as keys and performance values as values
    
    Returns:
    Figure: Plotly figure object
    """
    # Sort data by value
    sorted_data = {k: v for k, v in sorted(data_dict.items(), key=lambda item: item[1], reverse=True)}
    
    # Create data for heatmap
    symbols = list(sorted_data.keys())
    values = list(sorted_data.values())
    
    # Determine colors based on values
    colors = ['red' if v < 0 else 'green' for v in values]
    
    # Create figure
    fig = go.Figure(data=[
        go.Bar(
            x=symbols,
            y=values,
            marker_color=colors
        )
    ])
    
    fig.update_layout(
        title="Price Change (%)",
        xaxis_title="Asset",
        yaxis_title="Change (%)",
        template="plotly_white"
    )
    
    return fig

# Function to plot forecast
def plot_forecast(forecast_df, title):
    fig = go.Figure()

    # Plot actual data if available (assuming forecast_df contains original data points too)
    # Usually, Prophet forecast plots don't show original points by default in this format, 
    # so we focus on the forecast components.
    
    # Plot predicted values
    fig.add_trace(go.Scatter(
        x=forecast_df['ds'], 
        y=forecast_df['yhat'], 
        mode='lines',
        name='Prediction (yhat)',
        line=dict(color='blue')
    ))
    
    # Plot uncertainty interval (yhat_lower and yhat_upper)
    fig.add_trace(go.Scatter(
        x=forecast_df['ds'],
        y=forecast_df['yhat_upper'],
        mode='lines',
        line=dict(width=0),
        showlegend=False
    ))
    fig.add_trace(go.Scatter(
        x=forecast_df['ds'],
        y=forecast_df['yhat_lower'],
        mode='lines',
        line=dict(width=0),
        fill='tonexty',
        fillcolor='rgba(0,100,80,0.2)', # Example uncertainty color
        name='Uncertainty Interval'
    ))

    fig.update_layout(
        title=f'{title} - Price Prediction',
        xaxis_title='Date',
        yaxis_title='Price',
        hovermode="x unified"
    )
    return fig

# Function to plot price with SMA and Bollinger Bands
def plot_price_with_sma_bb(df, title, sma_period1=20, sma_period2=50, bb_period=20):
    fig = go.Figure()

    # Candlestick
    fig.add_trace(go.Candlestick(x=df.index,
                    open=df['Open'],
                    high=df['High'],
                    low=df['Low'],
                    close=df['Close'], name='Price'))

    # SMA
    if f'SMA_{sma_period1}' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df[f'SMA_{sma_period1}'], mode='lines', name=f'SMA {sma_period1}', line=dict(color='orange')))
    if f'SMA_{sma_period2}' in df.columns:
         fig.add_trace(go.Scatter(x=df.index, y=df[f'SMA_{sma_period2}'], mode='lines', name=f'SMA {sma_period2}', line=dict(color='purple')))

    # Bollinger Bands
    if f'BB_Upper_{bb_period}' in df.columns and f'BB_Lower_{bb_period}' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df[f'BB_Upper_{bb_period}'], mode='lines', line=dict(width=0.5, color='gray'), showlegend=False))
        fig.add_trace(go.Scatter(x=df.index, y=df[f'BB_Lower_{bb_period}'], mode='lines', line=dict(width=0.5, color='gray'), fill='tonexty', fillcolor='rgba(128,128,128,0.1)', name=f'Bollinger Bands {bb_period}'))

    fig.update_layout(
        title=f'{title} - Price, SMA & Bollinger Bands',
        xaxis_title='Time',
        yaxis_title='Price',
        xaxis_rangeslider_visible=False, # Usually disable for indicator plots
        hovermode="x unified"
    )
    return fig
