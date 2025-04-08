from datetime import datetime

def check_alert(alert, current_price):
    """
    Check if an alert has been triggered based on current price
    
    Parameters:
    alert (dict): Alert configuration with asset, type, and price
    current_price (float): Current price of the asset
    
    Returns:
    bool: True if alert is triggered, False otherwise
    """
    # Get alert details
    alert_type = alert["type"]
    alert_price = alert["price"]
    
    # Check if alert is triggered
    if alert_type == "Above" and current_price >= alert_price:
        return True
    elif alert_type == "Below" and current_price <= alert_price:
        return True
    
    return False

def create_alert(asset, alert_type, price):
    """
    Create a new price alert
    
    Parameters:
    asset (str): Asset symbol
    alert_type (str): Alert type ('Above' or 'Below')
    price (float): Alert price threshold
    
    Returns:
    dict: Alert configuration
    """
    return {
        "asset": asset,
        "type": alert_type,
        "price": price,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def format_alert_message(alert, current_price):
    """
    Format alert message for notification
    
    Parameters:
    alert (dict): Alert configuration
    current_price (float): Current price when alert was triggered
    
    Returns:
    str: Formatted alert message
    """
    asset = alert["asset"]
    alert_type = alert["type"].lower()
    alert_price = alert["price"]
    
    return f"ALERT: {asset} is now {alert_type} {alert_price:.4f} (Current: {current_price:.4f})"
