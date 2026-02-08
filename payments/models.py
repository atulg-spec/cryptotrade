# payments/models.py
from django.db import models
from accounts.models import CustomUser as User
from accounts.wallet.utils import deduct_wallet, add_wallet

transaction_status = [
        ('PENDING', 'PENDING'),
        ('REQUESTED', 'REQUESTED'),
        ('CANCELLED', 'CANCELLED'),
        ('COMPLETED', 'COMPLETED'),
        ('FAILED', 'FAILED'),
    ]

t_type = [
        ('WITHDRAW', 'WITHDRAW'),
        ('DEPOSIT', 'DEPOSIT'),
    ]

class transaction(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    transaction_id = models.CharField(max_length=200, default="")
    screenshot = models.ImageField(upload_to='manual_payments/', blank=True, null=True)
    status = models.CharField(choices=transaction_status,max_length=15,default = "REQUESTED")
    transaction_type = models.CharField(choices=t_type,max_length=15,default = "WITHDRAW")
    amount = models.PositiveIntegerField(default=0.0)
    remark = models.CharField(max_length=255,default = "Secured Payment")
    promo_code = models.CharField(max_length=200, default="", blank=True, null=True)
    promo_code_reward = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"

    def save(self, *args, **kwargs):
        if self.status == 'REQUESTED':
            deduct_wallet(self.user,self.amount)

        if self.status == 'CANCELLED':
            if self.transaction_type == 'WITHDRAW':
                add_wallet(self.user,self.amount)

        if self.status == 'COMPLETED':
            if self.transaction_type == 'DEPOSIT':
                add_wallet(self.user,self.amount)
                add_wallet(self.user,self.promo_code_reward)
            self.wallet = self.user.wallet

        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.user.first_name} --> {self.transaction_type} --> {self.amount}'
    
class payment_settings(models.Model):
    upi_id = models.CharField(max_length=100,default = "")

    class Meta:
        verbose_name = "Payment Settings"
        verbose_name_plural = "Payment Settings"

    def __str__(self):
        return f'{self.upi_id}'