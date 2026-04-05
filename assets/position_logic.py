from accounts.wallet.utils import add_amount, deduct_amount
from django.utils import timezone
from assets.models import Position
from decimal import Decimal, InvalidOperation
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# POSITION QUERY HELPERS
# ============================================================================

def position_open(user, symbol):
    """
    Check if user has an open (non-zero quantity) position in the given stock.
    
    Args:
        user: The user to check
        symbol: The stock to check
        
    Returns:
        bool: True if position exists and quantity > 0
    """
    pos = Position.objects.filter(user=user, stock=symbol, is_closed=False).last()
    if pos and pos.quantity > 0:
        return True
    return False


def get_position(user, symbol):
    """
    Get the current open position for a user in a given stock.
    
    Args:
        user: The user
        symbol: The stock
        
    Returns:
        Position or None: The open position if exists, None otherwise
    """
    return Position.objects.filter(user=user, stock=symbol, is_closed=False).last()


# ============================================================================
# POSITION CREATION & MANAGEMENT
# ============================================================================

def create_position(user, symbol, quantity, order_type, price):
    """
    Create a new position or update existing one for BUY orders.
    
    For BUY orders:
    - If no position exists: creates new position
    - If position exists: updates with weighted average buy price
    
    Args:
        user: The user
        symbol: The stock
        quantity: Quantity bought (must be positive for BUY)
        order_type: 'BUY' or 'SELL'
        price: Price at which the trade occurred
        
    Returns:
        Position: The created or updated position
        
    Raises:
        ValueError: If inputs are invalid
    """
    # Validate inputs
    if quantity <= 0:
        raise ValueError("Quantity must be positive")
    if price <= 0:
        raise ValueError("Price must be positive")
    if order_type not in ['BUY', 'SELL']:
        raise ValueError("Order type must be BUY or SELL")
    
    quantity = Decimal(str(quantity))
    price = Decimal(str(price))
    
    existing_pos = get_position(user, symbol)
    
    if order_type == 'BUY':
        return _handle_buy_position(user, symbol, existing_pos, quantity, price)
    else:  # SELL
        return _handle_sell_position(user, symbol, existing_pos, quantity, price)


def _handle_buy_position(user, symbol, existing_pos, quantity, price):
    """
    Handle BUY order position logic.
    
    - Creates new position if none exists
    - Updates existing position with weighted average price
    """
    if existing_pos is None:
        # Create new position
        pos = Position.objects.create(
            user=user,
            stock=symbol,
            quantity=quantity,
            buy_price=price,
            sell_price=Decimal('0.00'),
            last_traded_datetime=timezone.now()
        )
        logger.info(f"Created new BUY position: {user.username} - {symbol.symbol} - {quantity} @ {price}")
        return pos
    else:
        # Update existing position with weighted average
        existing_quantity = Decimal(str(existing_pos.quantity))
        existing_buy_price = Decimal(str(existing_pos.buy_price))
        
        # Calculate weighted average buy price
        existing_cost = existing_quantity * existing_buy_price
        new_cost = quantity * price
        total_cost = existing_cost + new_cost
        total_quantity = existing_quantity + quantity
        
        if total_quantity > 0:
            new_buy_price = total_cost / total_quantity
        else:
            new_buy_price = Decimal('0.00')
        
        # Update position
        existing_pos.quantity = total_quantity
        existing_pos.buy_price = new_buy_price.quantize(Decimal('0.01'))
        existing_pos.last_traded_datetime = timezone.now()
        existing_pos.save()
        
        logger.info(f"Updated BUY position: {user.username} - {symbol.symbol} - "
                   f"New qty: {total_quantity}, Avg price: {existing_pos.buy_price}")
        return existing_pos


def _handle_sell_position(user, symbol, existing_pos, quantity, price):
    """
    Handle SELL order position logic.
    
    - Validates sufficient quantity exists
    - Reduces position quantity
    - Closes position if quantity becomes zero
    - Calculates realized P&L
    """
    if existing_pos is None:
        raise ValueError("Cannot sell without an existing position")
    
    existing_quantity = Decimal(str(existing_pos.quantity))
    quantity = Decimal(str(quantity))
    price = Decimal(str(price))
    
    # Validate sufficient quantity
    if quantity > existing_quantity:
        raise ValueError(f"Cannot sell {quantity} when only {existing_quantity} available")
    
    # Calculate realized P&L for this sale
    buy_price = Decimal(str(existing_pos.buy_price))
    realized_pnl = (price - buy_price) * quantity
    
    # Update position
    existing_pos.sell_price = price
    existing_pos.last_traded_quantity = quantity
    existing_pos.quantity = existing_quantity - quantity
    
    # Add realized P&L to position (cumulative)
    existing_pos.realised_pnl = Decimal(str(existing_pos.realised_pnl)) + realized_pnl
    existing_pos.last_traded_datetime = timezone.now()
    
    # Check if position should be closed
    if existing_pos.quantity <= 0:
        existing_pos.quantity = Decimal('0')
        existing_pos.is_closed = True
        logger.info(f"Closed position: {user.username} - {symbol.symbol} - "
                   f"P&L: {existing_pos.realised_pnl}")
    else:
        logger.info(f"Reduced position: {user.username} - {symbol.symbol} - "
                   f"Remaining: {existing_pos.quantity}")
    
    existing_pos.save()
    return existing_pos


# ============================================================================
# LEGACY COMPATIBILITY FUNCTIONS
# ============================================================================
# These functions maintain backward compatibility with existing code
# but delegate to the new refactored logic

def add_more_position(user, symbol, quantity, price):
    """
    Add to an existing position with proper weighted average buy price calculation.
    
    DEPRECATED: Use create_position() instead.
    This function is kept for backward compatibility.
    
    Formula:
        total_cost = (existing_quantity × existing_buy_price) + (new_quantity × new_price)
        total_quantity = existing_quantity + new_quantity
        new_buy_price = total_cost ÷ total_quantity
    
    Args:
        user: The user owning the position
        symbol: The stock being added to
        quantity: Additional quantity (Decimal, must be positive)
        price: Price at which additional quantity is bought (Decimal, must be positive)
        
    Returns:
        Position or None: Updated position, or None if no open position exists
    """
    pos = get_position(user, symbol)
    if not pos or not position_open(user, symbol):
        return None
    
    # Validate inputs
    if quantity <= 0:
        raise ValueError("Quantity must be positive for adding to position")
    if price <= 0:
        raise ValueError("Price must be positive")
    
    existing_quantity = Decimal(str(pos.quantity))
    existing_buy_price = Decimal(str(pos.buy_price))
    new_quantity = Decimal(str(quantity))
    new_price = Decimal(str(price))
    
    # Calculate total cost and total quantity
    existing_cost = existing_quantity * existing_buy_price
    new_cost = new_quantity * new_price
    total_cost = existing_cost + new_cost
    total_quantity = existing_quantity + new_quantity
    
    # Calculate weighted average buy price
    if total_quantity > 0:
        new_buy_price = total_cost / total_quantity
    else:
        new_buy_price = Decimal('0.00')
    
    # Update position
    pos.quantity = total_quantity
    pos.buy_price = new_buy_price.quantize(Decimal('0.01'))
    pos.save()
    
    return pos


def close_full_position(user, symbol, price):
    """
    Close an entire position.
    
    DEPRECATED: Use create_position() with SELL order_type instead.
    This function is kept for backward compatibility.
    
    Args:
        user: The user
        symbol: The stock
        price: Selling price
    """
    pos = get_position(user, symbol)
    if not pos or not position_open(user, symbol):
        return
    
    quantity = pos.quantity
    buy_price = Decimal(str(pos.buy_price))
    price = Decimal(str(price))
    
    # Calculate realized P&L
    realized_pnl = (price - buy_price) * quantity
    
    # Update position
    pos.last_traded_quantity = quantity
    pos.quantity = Decimal('0')
    pos.sell_price = price
    pos.realised_pnl = Decimal(str(pos.realised_pnl)) + realized_pnl
    pos.is_closed = True
    pos.last_traded_datetime = timezone.now()
    pos.save()
    
    logger.info(f"Closed full position: {user.username} - {symbol.symbol} - "
               f"P&L: {realized_pnl}")


def close_some_position(user, symbol, quantity, price):
    """
    Partially close a position.
    
    DEPRECATED: Use create_position() with SELL order_type instead.
    This function is kept for backward compatibility.
    
    Args:
        user: The user
        symbol: The stock
        quantity: Quantity to sell
        price: Selling price
    """
    pos = get_position(user, symbol)
    if not pos or not position_open(user, symbol):
        return
    
    quantity = Decimal(str(quantity))
    price = Decimal(str(price))
    existing_quantity = Decimal(str(pos.quantity))
    
    # Validate
    if quantity > existing_quantity:
        raise ValueError(f"Cannot sell {quantity} when only {existing_quantity} available")
    
    # Calculate P&L for this partial close
    buy_price = Decimal(str(pos.buy_price))
    realized_pnl = (price - buy_price) * quantity
    
    # Update position
    pos.last_traded_quantity = quantity
    pos.quantity = existing_quantity - quantity
    pos.sell_price = price
    pos.realised_pnl = Decimal(str(pos.realised_pnl)) + realized_pnl
    pos.last_traded_datetime = timezone.now()
    
    # Close if quantity is zero
    if pos.quantity <= 0:
        pos.quantity = Decimal('0')
        pos.is_closed = True
    
    pos.save()
    
    logger.info(f"Partial close: {user.username} - {symbol.symbol} - "
               f"Sold {quantity}, Remaining: {pos.quantity}")


# ============================================================================
# BACKWARD COMPATIBILITY ALIASES (camelCase -> snake_case)
# ============================================================================
# These aliases allow existing code using camelCase function names to work
# without modification.

createPosition = create_position
