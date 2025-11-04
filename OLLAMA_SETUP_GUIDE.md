# 🚀 Ollama Setup Guide

## Installation Instructions for macOS

### Method 1: Direct Download (Recommended)

1. **Download Ollama:**
   - Visit: https://ollama.ai/download
   - Click "Download for Mac"
   - Open the downloaded `.dmg` file
   - Drag Ollama to Applications folder

2. **Launch Ollama:**
   - Open Applications folder
   - Double-click Ollama
   - Ollama will start in the menu bar (look for the llama icon)

### Method 2: Using Homebrew

```bash
brew install ollama
```

## After Installation

### 1. Verify Installation
```bash
ollama --version
```

### 2. Pull DeepSeek Model
```bash
# Option A: DeepSeek Coder (smaller, faster)
ollama pull deepseek-coder:6.7b

# Option B: DeepSeek Chat (better for trading)
ollama pull deepseek-chat

# Option C: Alternative - Llama 3 (also works well)
ollama pull llama3:8b
```

### 3. Test the Model
```bash
# Test that it works
ollama run deepseek-coder:6.7b "Hello, generate a JSON response"
```

### 4. Ensure Ollama is Serving
```bash
# Check if Ollama API is running
curl http://localhost:11434/api/tags

# Should return JSON with available models
```

## Configuration for Your Trading System

Your system is already configured! It will automatically use:
- **URL:** `http://localhost:11434/v1/chat/completions`
- **Model:** `deepseek-chat` (specified in prompts)

No changes needed to `.env` file.

## Verify Integration

After Ollama is running:

```bash
# Restart your API (it will auto-reload)
# Then test:
curl -s "http://localhost:8000/analyze/AAPL" | python -c "
import sys, json
data = json.load(sys.stdin)
plan = data.get('plan', {})
print('Confidence:', plan.get('confidence'))
print('Reason:', plan.get('reason', '')[:80])
if plan.get('confidence', 0) > 0.5:
    print('✅ LLM is working!')
else:
    print('⚠️ Still using mock plan')
"
```

## Expected Behavior

**Before Ollama:**
- Confidence: 0.5 (50%)
- Reason: "LLM unavailable - generated mock plan"

**After Ollama:**
- Confidence: 0.6-0.9 (60-90%)
- Reason: Detailed trading thesis based on market data

## Troubleshooting

### Ollama Not Starting
```bash
# Kill any existing Ollama processes
pkill ollama

# Start fresh
ollama serve
```

### Wrong Port
```bash
# Check what port Ollama is using
lsof -i :11434
```

### Model Not Found
```bash
# List available models
ollama list

# Pull the model if missing
ollama pull deepseek-coder:6.7b
```

## Model Recommendations

For momentum trading with social sentiment:

1. **deepseek-coder:6.7b** (Recommended)
   - Size: 4GB
   - Speed: Fast
   - Good at structured JSON responses

2. **llama3:8b**
   - Size: 4.7GB
   - Speed: Fast
   - Excellent reasoning

3. **mistral:7b**
   - Size: 4.1GB
   - Speed: Very fast
   - Good for rapid trading decisions

## System Requirements

- **RAM:** 8GB minimum (16GB recommended)
- **Disk:** 10GB free space
- **macOS:** 10.15+ (Catalina or later)

## Next Steps

1. Install Ollama from https://ollama.ai/download
2. Pull model: `ollama pull deepseek-coder:6.7b`
3. Verify: `curl http://localhost:11434/api/tags`
4. Test your trading system: `curl http://localhost:8000/analyze/AAPL`

Your trading system will automatically detect Ollama and start using it for intelligent trade plans!

