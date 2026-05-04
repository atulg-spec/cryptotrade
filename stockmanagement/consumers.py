import json
import asyncio
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from stockmanagement.models import Stock

logger = logging.getLogger(__name__)


class WatchlistConsumer(AsyncWebsocketConsumer):
    POLL_INTERVAL_SECONDS = 0.5
    FAILURE_BACKOFF_SECONDS = 1

    async def connect(self):
        try:
            await self.accept()
            self.price_update_task = None
            self.is_connected = True
            
            # Start sending price updates
            self.price_update_task = asyncio.create_task(self.send_price_updates())
            logger.debug("Watchlist websocket connected: %s", self.scope.get("client"))
        except Exception as e:
            logger.exception("Watchlist websocket connect failed: %s", e)
            await self.close()

    async def disconnect(self, close_code):
        await self._cleanup()

    async def _cleanup(self):
        self.is_connected = False
        task = getattr(self, "price_update_task", None)
        if not task:
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        finally:
            self.price_update_task = None

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
            logger.warning("Watchlist websocket received invalid JSON payload")

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
                await asyncio.sleep(self.POLL_INTERVAL_SECONDS)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error but continue
                logger.exception("Watchlist update loop error: %s", e)
                await asyncio.sleep(self.FAILURE_BACKOFF_SECONDS)

class UserEventsConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Only allow authenticated users to receive user-specific events
        user = self.scope.get("user")
        if user is None or user.is_anonymous:
            await self.close()
            return

        self.group_name = f"user_{user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        user = self.scope.get("user")
        if hasattr(self, "group_name") and user and not user.is_anonymous:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        # Reserved for future client-originated messages (e.g. symbol subscriptions)
        return

    async def user_event(self, event):
        """
        Handler for events sent via channel_layer.group_send with type 'user_event'.
        Forwards the payload to the connected WebSocket client.
        """
        payload = event.get("payload", {})
        await self.send(text_data=json.dumps(payload))