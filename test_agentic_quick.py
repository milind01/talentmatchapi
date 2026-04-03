#!/usr/bin/env python3
"""Quick test script for agentic system."""
import asyncio
import httpx
import json
import sys
from typing import Dict, Any

BASE_URL = "http://localhost:8000"
USER_ID = 42


async def test_endpoint(name: str, method: str, url: str, **kwargs) -> Dict[str, Any]:
    """Test an endpoint and print results."""
    print(f"\n{'='*70}")
    print(f"✓ TEST: {name}")
    print(f"{'='*70}")
    print(f"{method} {url}")
    if "json" in kwargs:
        print(f"Body: {json.dumps(kwargs['json'], indent=2)}")
    if "params" in kwargs:
        print(f"Params: {kwargs['params']}")
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            if method == "GET":
                response = await client.get(url, **kwargs)
            elif method == "POST":
                response = await client.post(url, **kwargs)
            elif method == "DELETE":
                response = await client.delete(url, **kwargs)
            
            result = response.json()
            print(f"\n✓ Status: {response.status_code}")
            
            # Print abbreviated response
            if isinstance(result, dict):
                if "execution_trace" in result:
                    result_copy = result.copy()
                    trace = result_copy.pop("execution_trace", [])
                    print(f"Response (summary):\n{json.dumps(result_copy, indent=2)}")
                    print(f"\nExecution Trace ({len(trace)} steps):")
                    for step in trace[:5]:  # Show first 5 steps
                        if isinstance(step, dict):
                            print(f"  - {step.get('step_id', step.get('step', 'unknown'))}: "
                                  f"{step.get('tool', '')} "
                                  f"({step.get('time_ms', 0)}ms)")
                    if len(trace) > 5:
                        print(f"  ... and {len(trace) - 5} more steps")
                else:
                    print(f"Response:\n{json.dumps(result, indent=2)[:500]}")
            
            return result
    except httpx.ConnectError:
        print(f"✗ ERROR: Cannot connect to {BASE_URL}")
        print(f"  Make sure FastAPI is running: uvicorn src.api.main:app --reload")
        sys.exit(1)
    except Exception as e:
        print(f"✗ ERROR: {str(e)}")
        return {"error": str(e)}


async def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("AGENTIC SYSTEM - API TESTING")
    print("="*70)
    
    # Test 1: Health check
    print("\n[1/8] Checking API health...")
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{BASE_URL}/health")
            if response.status_code == 200:
                print("✓ API is running")
            else:
                print("✗ API not responding correctly")
                sys.exit(1)
    except Exception as e:
        print(f"✗ API not running: {str(e)}")
        print(f"  Start it with: uvicorn src.api.main:app --reload")
        sys.exit(1)
    
    # Test 2: List tools
    print("\n[2/8] Testing: List Available Tools")
    tools_response = await test_endpoint(
        "List Available Tools",
        "GET",
        f"{BASE_URL}/api/agent/tools"
    )
    
    if tools_response.get("status") != "success":
        print("✗ Failed to list tools")
        sys.exit(1)
    
    tool_count = tools_response.get("tool_count", 0)
    print(f"\n✓ Found {tool_count} tools")
    if tool_count != 5:
        print(f"  WARNING: Expected 5 tools, got {tool_count}")
    
    # Test 3: Query classification - simple
    print("\n[3/8] Testing: Classify Simple Query")
    simple_query = "Find Python developers"
    await test_endpoint(
        "Classify Simple Query",
        "GET",
        f"{BASE_URL}/api/agent/query-info",
        params={"query": simple_query}
    )
    
    # Test 4: Query classification - complex
    print("\n[4/8] Testing: Classify Complex Query")
    complex_query = "Find 5 senior Python developers, score them against our backend role JD, analyze their resume authenticity, and generate outreach emails"
    await test_endpoint(
        "Classify Complex Query",
        "GET",
        f"{BASE_URL}/api/agent/query-info",
        params={"query": complex_query}
    )
    
    # Test 5: Execute simple query
    print("\n[5/8] Testing: Execute Simple Query (RAG)")
    await test_endpoint(
        "Execute Simple Query (RAG)",
        "POST",
        f"{BASE_URL}/api/agent/query",
        json={
            "query": "Find candidates with Python experience",
            "user_id": USER_ID,
            "use_agent_if_complex": False,
        }
    )
    
    # Test 6: Execute complex query with agent
    print("\n[6/8] Testing: Execute Complex Query (Agent)")
    await test_endpoint(
        "Execute Complex Query (Agent)",
        "POST",
        f"{BASE_URL}/api/agent/query",
        json={
            "query": "Find senior Python developers and score them",
            "user_id": USER_ID,
            "use_agent_if_complex": True,
        }
    )
    
    # Test 7: Check memory
    print("\n[7/8] Testing: Get Conversation Memory")
    memory_response = await test_endpoint(
        "Get Conversation Memory",
        "GET",
        f"{BASE_URL}/api/agent/memory/{USER_ID}"
    )
    
    message_count = memory_response.get("message_count", 0)
    print(f"\n✓ Conversation has {message_count} messages")
    
    # Test 8: Clear memory
    print("\n[8/8] Testing: Clear Conversation Memory")
    await test_endpoint(
        "Clear Conversation Memory",
        "DELETE",
        f"{BASE_URL}/api/agent/memory/{USER_ID}"
    )
    
    # Summary
    print(f"\n{'='*70}")
    print("✓ ALL TESTS COMPLETED SUCCESSFULLY")
    print(f"{'='*70}")
    print("\nNext steps:")
    print("1. Check logs: tail -f logs/app.log | grep agent")
    print("2. Try individual tool tests: curl ... /api/agent/test-tool")
    print("3. Read AGENTIC_SYSTEM_TESTING.md for detailed guide")
    print("4. See examples_agentic_usage.py for Python examples")
    print("\n")


if __name__ == "__main__":
    asyncio.run(main())
