# Restart API Server to Load ANTHROPIC_API_KEY

## Quick Fix

The API server is running but needs to be restarted to pick up the `ANTHROPIC_API_KEY` from `.env`.

## Option 1: Restart via Terminal (Recommended)

1. **Find and kill the current server:**
   ```bash
   # Find the process
   ps aux | grep uvicorn
   
   # Kill it (replace PID with actual process ID)
   kill <PID>
   
   # Or kill all uvicorn processes
   pkill -f uvicorn
   ```

2. **Restart the server:**
   ```bash
   cd /Users/brukemekonnen/stock_investment
   ./start_api.sh
   ```

   OR manually:
   ```bash
   uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
   ```

## Option 2: Restart via Script

If you have a process manager, restart it there.

## Verify It Works

After restarting, test the endpoint:

```bash
curl -X POST http://localhost:8000/summarize \
  -H "Content-Type: application/json" \
  -d '{"file_path": "artifacts/analysis_contract.json"}' \
  | python3 -m json.tool
```

You should now get a proper summary response instead of the "empty response" error.

## Current Server Status

- **Process ID:** Check with `ps aux | grep uvicorn`
- **Running on:** http://localhost:8000
- **Has --reload:** Yes (but .env changes don't trigger reload)

