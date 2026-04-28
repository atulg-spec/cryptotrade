from decimal import Decimal, ROUND_DOWN

from django.db import transaction

from accounts.wallet.utils import add_amount, deduct_amount
from assets.models import order as Order
from assets.position_logic import (
    add_more_position,
    close_full_position,
    close_some_position,
    createPosition,
    get_position,
    position_open,
)


def _normalize_trade_amount(quantity, price, amount=None):
    quantity = Decimal(str(quantity))
    price = Decimal(str(price))
    if amount is None:
        amount = quantity * price
    return quantity, price, Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_DOWN)


def execute_trade(user, symbol, quantity, order_type, amount=None):
    """
    Execute a trade and settle wallet + position state in one transaction.

    Returns:
        tuple[bool, str]: (success, message)
    """
    charges = Decimal("0.00")
    quantity, price, amount = _normalize_trade_amount(quantity, symbol.current_price, amount)
    wallet_balance = Decimal(str(user.wallet))

    with transaction.atomic():
        position = get_position(user, symbol)
        position_quantity = Decimal(str(position.quantity)) if position is not None else Decimal("0")

        if order_type == "BUY":
            if amount > wallet_balance:
                return False, "Order Rejected. Insufficient Funds !"

            Order.objects.create(
                user=user,
                stock=symbol,
                price=price,
                amount=amount,
                quantity=quantity,
                order_type=order_type,
                status="completed",
                charges=charges,
            )
            deduct_amount(user, amount)
            if get_position(user, symbol) is not None and position_open(user, symbol):
                add_more_position(user, symbol, quantity, price)
            else:
                createPosition(user, symbol, quantity, order_type, price)
            return True, "Order placed successfully."

        if not position_open(user, symbol):
            return False, "Oops! Can't sell the stocks you didn't own."
        if quantity > position_quantity:
            return False, "Oops! Can't sell the stocks you didn't own."

        sell_amount = (quantity * price).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
        Order.objects.create(
            user=user,
            stock=symbol,
            price=price,
            amount=sell_amount,
            quantity=quantity,
            order_type=order_type,
            status="completed",
            charges=charges,
        )

        if quantity < position_quantity:
            close_some_position(user, symbol, quantity, price)
            add_amount(user, sell_amount)
            return True, "Part Position closed successfully."

        close_full_position(user, symbol, price)
        add_amount(user, sell_amount)
        return True, "Position closed Successfully."
