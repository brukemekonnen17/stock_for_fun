#!/usr/bin/env python3
"""
Quick test to verify ANTHROPIC_API_KEY is accessible
"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load .env
from dotenv import load_dotenv
env_path = project_root / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ Loaded .env from: {env_path}")
else:
    print(f"❌ .env file not found at: {env_path}")
    sys.exit(1)

# Check API key
api_key = os.getenv('ANTHROPIC_API_KEY')
if api_key:
    print(f"✅ ANTHROPIC_API_KEY is set")
    print(f"   Length: {len(api_key)} characters")
    print(f"   Starts with: {api_key[:15]}...")
    print(f"   Ends with: ...{api_key[-15:]}")
    
    # Test if it's accessible from the LLM client
    try:
        from services.llm.client import API_KEY
        if API_KEY:
            print(f"✅ LLM client can access API_KEY")
            print(f"   Client key length: {len(API_KEY)}")
        else:
            print("❌ LLM client API_KEY is None/empty")
    except Exception as e:
        print(f"⚠️  Error importing LLM client: {e}")
else:
    print("❌ ANTHROPIC_API_KEY is not set in environment")
    sys.exit(1)

