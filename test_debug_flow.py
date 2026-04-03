#!/usr/bin/env python3
"""
Debug flow test - upload a resume and query it to trace the entire pipeline.
"""
import requests
import json
import time
from pathlib import Path

API_BASE = "http://localhost:8001"
USER_ID = 1

def upload_test_resume():
    """Upload a test resume"""
    print("\n" + "="*80)
    print("STEP 1: UPLOADING TEST RESUME")
    print("="*80)
    
    # Create a simple test resume file
    test_resume = """
JOHN DOE
john@example.com | (555) 123-4567 | linkedin.com/in/johndoe

PROFESSIONAL SUMMARY
Senior Python Developer with 8 years of experience building scalable backend systems.
Proficient in FastAPI, SQLAlchemy, and microservices architecture.

EXPERIENCE
Senior Python Developer - Tech Corp (2022-Present)
- Led development of Python microservices using FastAPI
- Optimized database queries improving performance by 40%
- Mentored 3 junior developers

Python Developer - StartupXYZ (2019-2022)
- Built RESTful APIs using FastAPI and Django
- Implemented real-time features using WebSockets
- 5+ years Python experience

SKILLS
- Python, FastAPI, Django, SQLAlchemy
- PostgreSQL, Redis, MongoDB
- Docker, Kubernetes, AWS
- Microservices, REST API, GraphQL

EDUCATION
BS Computer Science - State University (2016)
"""
    
    # Write to temp file
    resume_path = Path("temp_resume.txt")
    resume_path.write_text(test_resume)
    
    # Upload the file
    with open(resume_path, "rb") as f:
        files = {"file": ("test_resume.txt", f, "text/plain")}
        data = {
            "title": "John Doe - Senior Python Developer Resume",
            "user_id": USER_ID,
            "doctype": "resume"
        }
        
        response = requests.post(
            f"{API_BASE}/api/documents/upload",
            files=files,
            data=data
        )
    
    print(f"Upload Response Status: {response.status_code}")
    print(f"Upload Response: {json.dumps(response.json(), indent=2)}")
    
    # Get document ID from response
    doc_id = response.json().get("id")
    resume_path.unlink()  # Delete temp file
    
    print(f"\n✅ Uploaded document ID: {doc_id}")
    time.sleep(2)  # Wait for processing
    return doc_id


def query_api():
    """Query the API to test retrieval and candidate extraction"""
    print("\n" + "="*80)
    print("STEP 2: QUERYING FOR SENIOR PYTHON DEVELOPERS")
    print("="*80)
    
    query_data = {
        "query": "senior python developer with fastapi experience",
        "user_id": USER_ID,
        "route": "rag"  # Force RAG route for this test
    }
    
    response = requests.post(
        f"{API_BASE}/api/agent/query",
        json=query_data
    )
    
    print(f"Query Response Status: {response.status_code}")
    result = response.json()
    
    print(f"\n--- FULL RESPONSE ---")
    print(json.dumps(result, indent=2))
    
    print(f"\n--- SUMMARY ---")
    print(f"Status: {result.get('status')}")
    print(f"Candidates Found: {len(result.get('candidates', []))}")
    print(f"Documents Retrieved: {result.get('metadata', {}).get('documents_retrieved', 0)}")
    
    if result.get('candidates'):
        print(f"\n--- CANDIDATES ---")
        for cand in result['candidates']:
            print(f"  - {cand.get('name')}: {cand.get('experience_years')} years")
    else:
        print(f"\n❌ NO CANDIDATES RETURNED!")
        print(f"Answer: {result.get('answer', 'N/A')[:200]}")


if __name__ == "__main__":
    print("🧪 Starting debug flow test...")
    print(f"API Base: {API_BASE}")
    print(f"User ID: {USER_ID}")
    
    try:
        # Step 1: Upload resume
        doc_id = upload_test_resume()
        
        # Step 2: Query for candidates
        query_api()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
