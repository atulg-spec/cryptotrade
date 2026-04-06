from decimal import Decimal

charges = 0

def wallet_checked(user,amount):
    wallet_balance = Decimal(str(user.wallet))
    amount = Decimal(str(amount))
    return amount <= wallet_balance

def add_amount(user,amount):
    user.wallet = (Decimal(str(user.wallet))) + amount
    user.save()

def deduct_amount(user,amount):
    wallet_balance = Decimal(str(user.wallet))
    amount = Decimal(str(amount))
    if wallet_balance >= amount:
        user.wallet = wallet_balance - amount
        user.save()
    

def add_wallet(user,amount):
    user.wallet = float(user.wallet) + amount
    user.save()

def deduct_wallet(user,amount):
    user.wallet = float(user.wallet) - amount
    user.save()
