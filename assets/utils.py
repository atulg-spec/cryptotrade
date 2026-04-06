from assets.models import order as Order
from accounts.wallet.utils import add_amount, deduct_amount
from assets.position_logic import (
    get_position,
    position_open,
    add_more_position,
    createPosition,
    close_some_position,
    close_full_position,
)
from decimal import Decimal, ROUND_DOWN


# PLACE ORDER FUNCTION
def place_order(user, symbol, quantity, order_type, amount=None):
    """
    Core trade execution.

    - `quantity` is a Decimal and may be fractional.
    - If `amount` is None, it is derived as quantity * current_price.
    """
    charges = Decimal("0.00")
    price = Decimal(symbol.current_price)
    quantity = Decimal(str(quantity))
    wallet_balance = Decimal(str(user.wallet))

    if amount is None:
        amount = (quantity * price).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    else:
        amount = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_DOWN)

    pos = get_position(user, symbol)
    pos_quantity = Decimal("0")
    if pos is not None:
        pos_quantity = Decimal(str(pos.quantity))

    if order_type == "BUY":
        if amount <= wallet_balance:
            order = Order.objects.create(
                user=user,
                stock=symbol,
                price=price,
                amount=amount,
                quantity=quantity,
                order_type=order_type,
                status="initiated",
                charges=charges,
            )
            order.status = "completed"
            order.save()
            deduct_amount(user, amount)
            # POSITION SETTLEMENT
            if get_position(user, symbol) is not None:
                if position_open(user, symbol):
                    add_more_position(user, symbol, quantity, price)
                else:
                    createPosition(user, symbol, quantity, order_type, price)
            else:
                createPosition(user, symbol, quantity, order_type, price)
            # END POSITION SETTLEMENT
            return True, "Order placed successfully."
        else:
            return False, "Order Rejected. Insufficient Funds !"
    # SELL SECTION
    else:
        if position_open(user, symbol):
            if quantity > pos_quantity:
                return False, "Oops! Can't sell the stocks you didn't own."

            # Recompute amount for precision
            amount = (quantity * price).quantize(Decimal("0.01"), rounding=ROUND_DOWN)

            if quantity < pos_quantity:
                order = Order.objects.create(
                    user=user,
                    stock=symbol,
                    price=price,
                    amount=amount,
                    quantity=quantity,
                    order_type=order_type,
                    status="initiated",
                )
                order.status = "completed"
                order.save()
                close_some_position(user, symbol, quantity, price)
                add_amount(user, amount)
                return True, "Part Position closed successfully."
            else:
                order = Order.objects.create(
                    user=user,
                    stock=symbol,
                    price=price,
                    amount=amount,
                    quantity=quantity,
                    order_type=order_type,
                    status="initiated",
                )
                order.status = "completed"
                order.save()
                close_full_position(user, symbol, price)
                add_amount(user, amount)
                return True, "Position closed Successfully."
        else:
            return False, "Oops! Can't sell the stocks you didn't own."
