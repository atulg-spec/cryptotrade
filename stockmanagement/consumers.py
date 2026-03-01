import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from stockmanagement.models import Stock
from decimal import Decimal


class WatchlistConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            await self.accept()
            self.price_update_task = None
            self.is_connected = True
            
            # Start sending price updates
            self.price_update_task = asyncio.create_task(self.send_price_updates())
            print(f"WebSocket connected: {self.scope['client']}")
        except Exception as e:
            print(f"Error in WebSocket connect: {e}")
            await self.close()

    async def disconnect(self, close_code):
        self.is_connected = False
        if self.price_update_task:
            self.price_update_task.cancel()
            try:
                await self.price_update_task
            except asyncio.CancelledError:
                pass

    async def receive(self, text_data):
        """Handle messages from client if needed"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong'
                }))
        except json.JSONDecodeError:
            pass

    @database_sync_to_async
    def get_all_stocks(self):
        """Fetch all stocks from database"""
        stocks = Stock.objects.all().order_by('symbol')
        return [
            {
                'id': stock.id,
                'symbol': stock.symbol,
                'name': stock.name,
                'current_price': float(stock.current_price),
                'open_price': float(stock.open_price),
                'high_price': float(stock.high_price),
                'low_price': float(stock.low_price),
                'close_price': float(stock.close_price),
                'price_change': float(stock.price_change),
                'percentage_change': float(stock.percentage_change),
                'volume': float(stock.quote_volume_24h),
                'last_updated': stock.last_updated.isoformat() if stock.last_updated else None,
            }
            for stock in stocks
        ]

    async def send_price_updates(self):
        """Continuously poll database and send price updates"""
        last_prices = {}
        
        while self.is_connected:
            try:
                stocks = await self.get_all_stocks()
                
                # Check for price changes and send updates
                updates = []
                for stock in stocks:
                    stock_id = stock['id']
                    current_price = stock['current_price']
                    
                    # Send update if price changed or it's the first time
                    if stock_id not in last_prices or last_prices[stock_id] != current_price:
                        
                        updates.append({
                            'id': stock_id,
                            'symbol': stock['symbol'],
                            'current_price': current_price,
                            'change': stock['price_change'],
                            'percentage_change': stock['percentage_change'],
                            'open_price': stock['open_price'],
                            'high_price': stock['high_price'],
                            'low_price': stock['low_price'],
                            'volume': stock['volume'],
                            'last_updated': stock['last_updated'],
                        })
                        
                        last_prices[stock_id] = current_price
                
                # Send updates if any
                if updates:
                    await self.send(text_data=json.dumps({
                        'type': 'price_update',
                        'updates': updates
                    }))
                
                # Wait before next poll (poll every 1 second for real-time feel)
                await asyncio.sleep(0.5)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error but continue
                print(f"Error in price update loop: {e}")
                await asyncio.sleep(1)

