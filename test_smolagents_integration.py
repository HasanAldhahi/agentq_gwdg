#!/usr/bin/env python3

import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test imports
try:
    from agentq.core.agent.smol_executor_agent import execute_sub_task, smol_executor
    from agentq.core.tools.browser_tools import (
        get_current_url, open_url, get_dom_content, click, enter_text,
        enter_text_and_click, get_screenshot, press_key, solve_captcha_tool, upload_file
    )
    print("✅ Successfully imported smolagents components")
    print(f"📦 Available tools: {len(smol_executor.tools)} browser automation tools")
except ImportError as e:
    print(f"❌ Import error: {e}")
    exit(1)

async def test_simple_task():
    """Test a simple sub-task execution."""
    print("\n🧪 Testing simple sub-task execution...")
    
    # Test a simple task that doesn't require browser interaction
    result = await execute_sub_task("Print 'Hello from smolagents!' and return the current timestamp")
    print(f"📋 Result: {result}")

async def test_browser_task():
    """Test a browser-related task."""
    print("\n🌐 Testing browser task execution...")
    
    # Test opening a URL and getting current URL
    result = await execute_sub_task("Open the URL 'https://www.google.com' and then get the current URL")
    print(f"📋 Result: {result}")

async def main():
    print("🚀 AgentQ + smolagents Integration Test")
    print("="*50)
    
    # Check environment variables
    print(f"📍 Base URL: {os.environ.get('ACADEMIC_CLOUD_BASE_URL', 'Not set')}")
    print(f"🤖 Model: {os.environ.get('MODEL_NAME', 'Not set')}")
    print(f"🔑 API Key: {'Set' if os.environ.get('ACADEMIC_CLOUD_API_KEY') else 'Not set'}")
    
    if not all([
        os.environ.get('ACADEMIC_CLOUD_BASE_URL'),
        os.environ.get('MODEL_NAME'),
        os.environ.get('ACADEMIC_CLOUD_API_KEY')
    ]):
        print("⚠️  Warning: Some environment variables are not set. Tests may fail.")
    
    try:
        # Test 1: Simple task
        await test_simple_task()
        
        # Test 2: Browser task (commented out for now as it requires browser setup)
        # await test_browser_task()
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 