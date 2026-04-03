#!/usr/bin/env python
"""Test script to verify structured candidate response format."""
import asyncio
import httpx
import json
from src.application.orchestration_service import RequestOrchestrationService


async def test_structured_response():
    """Test that candidates are extracted and returned in structured format."""
    orchestration = RequestOrchestrationService()
    
    # Test query
    query = "find and match candidate with architect experience"
    user_id = 1
    
    print("📝 Test Query:", query)
    print("👤 User ID:", user_id)
    print("-" * 80)
    
    # Run agentic query
    result = await orchestration.run_agentic_query(
        user_id=user_id,
        query=query,
        use_agent_if_complex=False,
    )
    
    print("\n✅ Response Structure:")
    print(f"  Status: {result.get('status')}")
    print(f"  Route: {result.get('route')}")
    print(f"  Time: {result.get('processing_time_ms')}ms")
    print(f"  Candidates Count: {len(result.get('candidates', []))}")
    print(f"  Source Docs Count: {len(result.get('sources', []))}")
    
    print("\n📊 Full Response:")
    print(json.dumps(result, indent=2, default=str))
    
    if result.get('candidates'):
        print("\n🎯 First Candidate Details:")
        first_candidate = result['candidates'][0]
        print(f"  Name: {first_candidate.get('name')}")
        print(f"  Total Experience: {first_candidate.get('total_experience')}")
        print(f"  Relevant Experience: {first_candidate.get('relevant_experience')}")
        print(f"  Summary: {first_candidate.get('summary')}")
        print(f"  Relevance Score: {first_candidate.get('relevance_score')}")
        print(f"  Key Projects: {first_candidate.get('key_projects')}")
    else:
        print("\n⚠️  No candidates extracted!")


if __name__ == "__main__":
    asyncio.run(test_structured_response())
