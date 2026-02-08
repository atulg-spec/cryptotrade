from django.urls import path
from . import views

urlpatterns = [
    path('add-amount/', views.add_amount, name='add-amount'),
    path('withdraw-amount/', views.withdraw_amount, name='withdraw-amount'),
    path('my-transactions/', views.my_transactions, name='my-transactions'),
    path('transactions/cancel/<int:transaction_id>/', views.cancel_transaction, name='cancel_transaction'),

    path('save-payment-requests/', views.save_payment_requests, name='save-payment-requests'),
]