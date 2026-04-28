# accounts/models.py
from django.db import models
import secrets
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import uuid

class CustomUser(AbstractUser):
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    phone_number = models.PositiveIntegerField(blank=True, null=True)
    wallet = models.FloatField(default=0.0)
    
    bank_account_name = models.CharField(max_length=150,default="")
    bank_account_number = models.CharField(max_length=150,default="")
    upi_id = models.CharField(max_length=150,default="")
    ifsc_code = models.CharField(max_length=12,default="")

    region_name = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    zip_code = models.CharField(max_length=20, blank=True, null=True)
    lat = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    lon = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    timezone = models.CharField(max_length=100, blank=True, null=True)
    isp = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.username