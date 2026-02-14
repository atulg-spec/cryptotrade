"""
Quick test to verify WebSocket routing is configured correctly
Run this after starting the server with daphne
"""
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8000/ws/watchlist/"
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket connected successfully!")
            print("Waiting for messages...")
            
            # Wait for a few messages
            for i in range(3):
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(message)
                    print(f"📨 Received: {data.get('type', 'unknown')}")
                    if data.get('type') == 'price_update':
                        print(f"   Updates: {len(data.get('updates', []))} stocks")
                except asyncio.TimeoutError:
                    print("⏱️  No message received (this is OK if prices haven't changed)")
            
            print("\n✅ WebSocket is working correctly!")
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ Connection failed with status {e.status_code}")
        print("   Make sure the server is running with: daphne -b 0.0.0.0 -p 8000 tradehub.asgi:application")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("   Make sure the server is running with daphne, not runserver")

if __name__ == "__main__":
    asyncio.run(test_websocket())

