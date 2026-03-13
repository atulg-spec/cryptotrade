# Alternative version with category information

from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
from stockmanagement.models import Stock


class Command(BaseCommand):
    help = 'Import all financial symbols with category metadata'

    def handle(self, *args, **options):
        # Complete symbol data with categories
        symbols_with_categories = [
            # Stocks
            {'category': 'Stocks', 'symbols': [
                ('TSLA', 'Tesla Inc'),
                ('NVDA', 'NVIDIA Corp'),
                ('AAPL', 'Apple Inc'),
                ('AMD', 'AMD'),
                ('MSFT', 'Microsoft'),
                ('ORCL', 'Oracle'),
                ('GOOGL', 'Alphabet'),
                ('NKE', 'Nike'),
            ]},
            # Crypto
            {'category': 'Crypto', 'symbols': [
                ('BTC/USD', 'Bitcoin'),
                ('ETH/USD', 'Ethereum'),
                ('BTC/XAU', 'Bitcoin Gold'),
                ('BTC/JPY', 'Bitcoin Yen'),
            ]},
            # Metals
            {'category': 'Metals', 'symbols': [
                ('XAU/USD', 'Gold'),
                ('XAG/USD', 'Silver'),
                ('XCU/USD', 'Copper'),
            ]},
            # Indices
            {'category': 'Indices', 'symbols': [
                ('US30', 'Wall St'),
                ('USTEC', 'Nasdaq 100'),
            ]},
            # Forex
            {'category': 'Forex', 'symbols': [
                ('EUR/USD', 'Euro'),
                ('GBP/USD', 'Pound'),
                ('USD/JPY', 'Dollar Yen'),
                ('USD/ZAR', 'Dollar Rand'),
                ('GBP/JPY', 'Pound Yen'),
            ]},
            # Energies
            {'category': 'Energies', 'symbols': [
                ('USOIL', 'WTI Crude'),
                ('UKOIL', 'Brent'),
                ('XNG/USD', 'Natural Gas'),
            ]},
        ]

        created_count = 0
        updated_count = 0

        with transaction.atomic():
            for category_group in symbols_with_categories:
                category = category_group['category']
                self.stdout.write(self.style.SUCCESS(f"\nProcessing {category}..."))

                for symbol, name in category_group['symbols']:
                    # Parse base and quote assets
                    if '/' in symbol:
                        base, quote = symbol.split('/')
                    else:
                        base = symbol
                        quote = 'USD'  # Default quote for indices and energies

                    stock, created = Stock.objects.update_or_create(
                        symbol=symbol,
                        defaults={
                            'name': name,
                            'base_asset': base,
                            'quote_asset': quote,
                            # Initialize price fields
                            'open_price': Decimal('0.00'),
                            'high_price': Decimal('0.00'),
                            'low_price': Decimal('0.00'),
                            'close_price': Decimal('0.00'),
                            'current_price': Decimal('0.00'),
                            'bid_price': Decimal('0.00'),
                            'ask_price': Decimal('0.00'),
                            'high_24h': Decimal('0.00'),
                            'low_24h': Decimal('0.00'),
                            'quote_volume_24h': Decimal('0.00'),
                            'price_change': Decimal('0.00'),
                            'percentage_change': Decimal('0.00'),
                        }
                    )

                    if created:
                        created_count += 1
                        self.stdout.write(f"  ✓ Created: {symbol}")
                    else:
                        updated_count += 1
                        self.stdout.write(f"  • Updated: {symbol}")

        # Final summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS(f'Import completed: {created_count} created, {updated_count} updated'))