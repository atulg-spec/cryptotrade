from assets.models import order as Order
from accounts.wallet.utils import *
from assets.position_logic import *
from decimal import Decimal

# PLACE ORDER FUNCTION
def place_order(user,symbol,quantity,order_type):
    charges = 0
    price = symbol.current_price
    quantity = Decimal(str(quantity))
    amount = quantity * price

    pos = get_position(user,symbol)
    pos_quantity = 0
    if pos is not None:
        pos_quantity = pos.quantity
    if order_type == 'BUY':
        if amount <= user.wallet:
            order = Order.objects.create(user=user, stock=symbol, price=price, amount=amount, quantity=quantity, order_type=order_type, status="initiated",charges=charges)
            order.status = 'completed'
            order.save()
            deduct_amount(user,amount)
            # POSITION SETTLEMENT
            if get_position(user,symbol) is not None:
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
            print('here')
            if quantity > pos_quantity:
                return False, "Oops! Can't sell the stocks you didn't own."
            if quantity < pos_quantity:
                amount = quantity * price
                order = Order.objects.create(user=user, stock=symbol, price=price, amount=amount, quantity=quantity, order_type=order_type, status="initiated")
                order.save()
                order.status = 'completed'
                order.save()
                close_some_position(user, symbol, quantity, price)
                add_amount(user,amount)
                return True, "Part Position closed successfully."
            else:
                amount = quantity * price
                order = Order.objects.create(user=user, stock=symbol, price=price, amount=amount, quantity=quantity, order_type=order_type, status="initiated")
                order.status = 'completed'
                order.save()
                close_full_position(user, symbol, price)
                add_amount(user,amount)
                return True, "Position closed Successfully."
        else:
            print('not selling')
            return False, "Oops! Can't sell the stocks you didn't own."