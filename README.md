# Forex & Crypto Prediction App

A comprehensive dashboard for analyzing and predicting Forex and Cryptocurrency markets using various technical indicators and machine learning models.

## Features

- Real-time market data for Forex and Cryptocurrencies
- Technical analysis with multiple indicators (SMA, EMA, RSI, MACD, Bollinger Bands)
- Price predictions using multiple models (Linear Regression, Prophet, ARIMA)
- Trading signals generation
- Price alerts system
- Interactive visualizations

## Local Development Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd ForexCryptoPro
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
streamlit run app.py
```

The application will be available at http://localhost:8501

## Project Structure

- `app.py`: Main Streamlit application
- `data_service.py`: Data fetching and processing
- `technical_indicators.py`: Technical analysis calculations
- `prediction_models.py`: Machine learning models for predictions
- `visualization.py`: Plotting and visualization functions
- `alerts.py`: Price alert system
- `trading_signals.py`: Trading signal generation

## Deployment

The application is configured for deployment on Streamlit Cloud. Simply connect your repository to Streamlit Cloud and it will automatically deploy using the configuration in `.streamlit/config.toml`.

## Requirements

- Python 3.11 or higher
- Dependencies listed in requirements.txt

## License

MIT License 