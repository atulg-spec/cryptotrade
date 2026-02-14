# WebSocket Setup for Real-Time Price Updates

## ⚠️ IMPORTANT: You MUST Use Daphne, Not Runserver!

If you're seeing **"Not Found: /ws/watchlist/"** or **404 errors**, it means you're still using `python manage.py runserver`. 
**Django's runserver does NOT support WebSockets!** You MUST use `daphne` instead.

## Quick Fix

### Step 1: Stop Your Current Server
Press `Ctrl+C` in the terminal where `runserver` is running.

### Step 2: Start with Daphne

**Windows (PowerShell):**
```powershell
daphne -b 0.0.0.0 -p 8000 tradehub.asgi:application
```

**Or use the batch file:**
```powershell
.\run_server.bat
```

**Linux/Mac:**
```bash
daphne -b 0.0.0.0 -p 8000 tradehub.asgi:application
```

**Or use the shell script:**
```bash
chmod +x run_server.sh
./run_server.sh
```

### Step 3: Verify It's Working

You should see output like:
```
2026-02-09 02:43:00 [INFO] Starting server at tcp:port=8000:interface=0.0.0.0
2026-02-09 02:43:00 [INFO] HTTP/2 support not enabled (install the http2 and tls Twisted extras)
2026-02-09 02:43:00 [INFO] Configuring endpoint tcp:port=8000:interface=0.0.0.0
2026-02-09 02:43:00 [INFO] Listening on TCP address 0.0.0.0:8000
```

If you see "Starting development server at http://127.0.0.1:8000/" - that's **WRONG**, you're still using runserver!

### Step 4: Test the WebSocket

Run the test script in a separate terminal:
```bash
python test_websocket.py
```

Or just open your watchlist page and check the browser console - you should see "WebSocket connected" instead of errors.

## Alternative: Use Uvicorn

If you prefer uvicorn:
```bash
uvicorn tradehub.asgi:application --host 0.0.0.0 --port 8000
```

## Important Notes

1. **ALWAYS use daphne/uvicorn for WebSocket support** - never use `runserver`
2. The WebSocket endpoint is: `ws://localhost:8000/ws/watchlist/`
3. Make sure your price streaming command is running in a separate terminal:
   ```bash
   python manage.py stream
   ```

## Troubleshooting

### Still seeing 404 errors?
- ✅ Make sure you stopped `runserver` completely
- ✅ Make sure you're using `daphne` (check the startup message)
- ✅ Check that daphne is installed: `pip list | Select-String daphne` (Windows) or `pip list | grep daphne` (Linux/Mac)

### WebSocket connects but no updates?
- Make sure `python manage.py stream` is running to update prices in the database
- Check the browser console for any JavaScript errors

### Connection refused?
- Make sure the server is running on port 8000
- Check if another process is using port 8000
- Try a different port: `daphne -b 0.0.0.0 -p 8001 tradehub.asgi:application`

