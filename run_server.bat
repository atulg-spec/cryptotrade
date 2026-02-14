@echo off
echo Starting TradeHub server with WebSocket support...
echo.
echo Make sure you have activated your virtual environment!
echo.
daphne -b 0.0.0.0 -p 8000 tradehub.asgi:application

