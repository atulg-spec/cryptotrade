from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from stockmanagement.models import Stock


class DashboardSmokeTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="dashboard-user",
            email="dashboard-user@example.com",
            password="testpass123",
            wallet=200,
        )
        Stock.objects.create(
            symbol="BTCUSDT",
            name="Bitcoin",
            exchange="BINANCE",
            current_price=Decimal("50000.00"),
            open_price=Decimal("49000.00"),
            high_price=Decimal("51000.00"),
            low_price=Decimal("48000.00"),
            close_price=Decimal("49500.00"),
        )

    def test_orders_page_requires_authentication(self):
        response = self.client.get(reverse("orders"))
        self.assertEqual(response.status_code, 302)

    def test_orders_page_renders_for_authenticated_user(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("orders"))
        self.assertEqual(response.status_code, 200)
