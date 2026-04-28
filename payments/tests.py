from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser


class PaymentsSmokeTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="payments-user",
            email="payments-user@example.com",
            password="testpass123",
        )

    def test_my_transactions_requires_authentication(self):
        response = self.client.get(reverse("my-transactions"))
        self.assertEqual(response.status_code, 302)

    def test_my_transactions_renders_for_authenticated_user(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("my-transactions"))
        self.assertEqual(response.status_code, 200)
