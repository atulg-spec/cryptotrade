from assets.services.trading_service import execute_trade


# PLACE ORDER FUNCTION
def place_order(user, symbol, quantity, order_type, amount=None):
    """
    Backward-compatible proxy for trade execution.
    """
    return execute_trade(user, symbol, quantity, order_type, amount=amount)
