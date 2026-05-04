import time, os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tradehub.settings')
django.setup()

from django.contrib.auth import get_user_model
from assets.models import MarginPosition

print("Waiting 25 seconds for browser to place order...")
time.sleep(25)

User = get_user_model()
user = User.objects.get(email='atul@gmail.com')

# Make sure they have plenty of money before the order
print(f"Original Wallet: {user.wallet}")

pos = MarginPosition.objects.filter(user=user, status='OPEN').first()
if pos:
    target_wallet = float(pos.margin_used) / 0.96
    print(f"Found position margin_used: {pos.margin_used}. Setting wallet to {target_wallet} to trigger 96% risk.")
    user.wallet = target_wallet
    user.save()
    print("Wallet updated! Backend should trigger auto-close within 5-10 seconds.")
else:
    print("No open positions found.")
