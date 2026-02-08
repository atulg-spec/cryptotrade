from decimal import Decimal

charges = 0

def wallet_checked(user,amount):
    max = 0
    max = user.wallet
    if amount < max:
        return True
    else:
        return False

def add_amount(user,amount):
    user.wallet = (Decimal(str(user.wallet))) + amount
    user.save()

def deduct_amount(user,amount):
    if user.wallet > amount:
        user.wallet = (Decimal(str(user.wallet))) - amount
        user.save()
    

def add_wallet(user,amount):
    user.wallet = float(user.wallet) + amount
    user.save()

def deduct_wallet(user,amount):
    user.wallet = float(user.wallet) - amount
    user.save()