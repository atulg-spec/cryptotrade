from accounts.wallet.utils import add_amount, deduct_amount
from django.utils import timezone
from assets.models import Position
from decimal import Decimal

# POSITION LOGIC
def position_open(user, symbol):
    pos = Position.objects.filter(user=user,stock=symbol,is_closed=False)
    if pos.exists():
        pos = pos.last()
        if pos.quantity > 0:
            return True
        else:
            return False
    else:
        return False

def get_position(user, symbol):
    pos = Position.objects.filter(user=user, stock=symbol, is_closed=False).last()
    return pos


def createPosition(user, symbol, quantity, ordertype, price):
    pos = get_position(user, symbol)
    if pos is None:
        qty = quantity
        if ordertype == 'SELL':
            qty = quantity * -1
        pos = Position.objects.create(
            user = user,
            quantity = qty,
            stock = symbol,
            )
    else:
        pos.buy_price=0
        pos.sell_price=0
        if ordertype == 'BUY':
            pos.quantity = quantity
        else:
            pos.quantity = quantity * -1
            pos.save()

    if ordertype == 'BUY':
        pos.buy_price = price
        pos.save()


def close_full_position(user, symbol, price):
    pos = get_position(user, symbol)
    pos.last_traded_quantity = pos.quantity
    pos.quantity = 0
    if position_open(user, symbol):
        pos.sell_price = price
        pos.save()

def add_more_position(user, symbol, quantity, price):
    pos = get_position(user, symbol)
    if position_open(user, symbol):
        pos.quantity = pos.quantity + quantity
        pos.buy_price = (Decimal(str(pos.buy_price)) + price) / 2
        pos.save()


def close_some_position(user, symbol, quantity, price):
    pos = get_position(user, symbol)
    pos.last_traded_quantity = quantity
    if position_open(user, symbol):
        pos.quantity = pos.quantity - quantity
        pos.sell_price = price
        pos.save()