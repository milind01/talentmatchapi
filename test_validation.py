#!/usr/bin/env python
"""Test candidate extraction with validation."""
import asyncio
from src.application.candidate_extraction_service import CandidateExtractionService


async def test():
    service = CandidateExtractionService()
    
    print("Testing candidate extraction validation...\n")
    
    # Test 1: Bad content (should be rejected)
    print("Test 1: Bad resume content (fragments)")
    bad_resume = 'cross-functional teams. E-Commerce -a5708231Featured Case Studies'
    result = await service.extract_candidate_details(bad_resume, 'architect')
    print(f"  Result: {'REJECTED (correct)' if result is None else 'FAILED - should reject'}\n")
    
    # Test 2: Good resume
    print("Test 2: Valid resume with name and experience")
    good_resume = """JOHN SMITH
john.smith@email.com | (555) 123-4567

PROFESSIONAL SUMMARY
Solution Architect with 8+ years of experience in cloud systems.

EXPERIENCE
Senior Architect at TechCorp - Led 10+ projects in microservices architecture.
Designed distributed systems using AWS and Kubernetes.
"""
    result = await service.extract_candidate_details(good_resume, 'architect')
    if result:
        print(f"  Name: {result.name}")
        print(f"  Experience: {result.total_experience}")
        print(f"  Relevant: {result.relevant_experience}")
        print("  Result: ACCEPTED (correct)\n")
    else:
        print("  Result: REJECTED - should accept\n")
    
    # Test 3: Invalid name extraction
    print("Test 3: Document with bad name extraction")
    bad_name_doc = """Led architecture design for 12+ projects
    Designed microservices and distributed systems
    5+ years of experience in cloud technology"""
    result = await service.extract_candidate_details(bad_name_doc, 'architect')
    print(f"  Result: {'REJECTED (correct)' if result is None else 'FAILED - should reject'}\n")


if __name__ == "__main__":
    asyncio.run(test())
