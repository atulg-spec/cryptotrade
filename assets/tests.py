from decimal import Decimal

from django.test import Client, TestCase, override_settings

from accounts.models import CustomUser
from assets.models import Position
from stockmanagement.models import Stock


@override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
class InitiateOrderTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="order-user",
            email="order-user@example.com",
            password="testpass123",
            wallet=100.0,
        )
        self.stock = Stock.objects.create(
            symbol="SOLUSDT",
            name="Solana",
            exchange="BINANCE",
            current_price=Decimal("80.00"),
            open_price=Decimal("79.00"),
            high_price=Decimal("82.00"),
            low_price=Decimal("78.00"),
            close_price=Decimal("79.50"),
        )
        self.client = Client()
        self.client.force_login(self.user)

    def _post_order(self, **payload):
        return self.client.post(
            "/assets/initiate-order/",
            payload,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

    def test_buy_accepts_multiple_valid_amounts(self):
        for amount in ["1", "5", "11", "12.5", "50"]:
            response = self._post_order(
                symbol="SOLUSDT",
                order_type="BUY",
                amount=amount,
            )
            self.assertEqual(response.status_code, 200, amount)
            self.assertTrue(response.json()["success"], amount)

    def test_buy_can_spend_full_wallet_balance(self):
        self.user.wallet = 11.0
        self.user.save(update_fields=["wallet"])

        response = self._post_order(
            symbol="SOLUSDT",
            order_type="BUY",
            amount="11",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.user.refresh_from_db()
        self.assertEqual(Decimal(str(self.user.wallet)), Decimal("0.0"))

    def test_sell_accepts_multiple_valid_quantities(self):
        buy_response = self._post_order(
            symbol="SOLUSDT",
            order_type="BUY",
            amount="40",
        )
        self.assertEqual(buy_response.status_code, 200)
        self.assertTrue(buy_response.json()["success"])

        for quantity in ["0.05", "0.10", "0.15"]:
            response = self._post_order(
                symbol="SOLUSDT",
                order_type="SELL",
                quantity=quantity,
            )
            self.assertEqual(response.status_code, 200, quantity)
            self.assertTrue(response.json()["success"], quantity)

        self.assertTrue(
            Position.objects.filter(user=self.user, stock=self.stock, is_closed=False).exists()
        )
