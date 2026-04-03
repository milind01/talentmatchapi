#!/usr/bin/env python3
"""Test query augmentation to show domain-aware search expansion."""

import sys
sys.path.insert(0, '/Users/milinddeshmukh/docAi')

from src.application.query_augmentation_service import QueryAugmentationService

def test_query_augmentation():
    """Test that queries are augmented with domain context."""
    service = QueryAugmentationService()
    
    test_cases = [
        "find architect",
        "find python developer", 
        "find react developer",
        "find devops engineer",
        "find data scientist",
        "find backend engineer",
    ]
    
    print("\n" + "="*80)
    print("QUERY AUGMENTATION TEST - Domain-Aware Search Expansion")
    print("="*80 + "\n")
    
    for original_query in test_cases:
        print(f"Original Query: '{original_query}'")
        
        # Augment the query
        augmented = service.augment_query(original_query)
        print(f"Augmented Query: '{augmented}'")
        
        # Show what domain was detected
        domain = service._detect_domain(original_query.lower())
        print(f"Detected Domain: '{domain}'")
        
        if domain:
            # Show the keywords that will be searched
            keywords = service.get_search_keywords_for_domain(domain, limit=5)
            print(f"Search Keywords: {keywords}")
        
        print("-" * 80)
    
    print("\n" + "="*80)
    print("EXPLANATION:")
    print("="*80)
    print("""
Before Query Augmentation:
- User asks: "find architect"
- System searches for literal word "architect" in documents
- Retrieves any mention of "architect" (definitions, job descriptions, etc.)
- WRONG: Not finding actual people with architect experience

After Query Augmentation:
- User asks: "find architect"
- System recognizes domain: "architect"
- Augmented query becomes: "find architect (designed systems OR architected infrastructure OR ...) (microservices OR distributed systems OR ...)"
- System searches for people who have THESE SKILLS, not just the word "architect"
- CORRECT: Finds people who actually designed systems, did architecture work, etc.

KEY BENEFIT:
Instead of searching for definitions of "architect", the system now searches for
the actual skills and responsibilities of architects, leading to finding real
candidates with relevant experience.
""")

if __name__ == "__main__":
    test_query_augmentation()
