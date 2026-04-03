#!/usr/bin/env python3
"""
SOLUTION: Recruitment API candidate extraction fix

PROBLEM:
The recruitment API endpoint GET /api/v1/recruitment/jd/2/candidates was returning:
{
  "candidate_name": null,
  "email": null,
  "phone": null,
  "skills": [],
  "experience_years": null,
  "education": null,
  "current_role": null,
  "status": "parsed",
  ...
}

All candidate fields were null/empty even though status was "parsed"!

ROOT CAUSE:
1. The resume parsing was happening via LLMService.parse_resume()
2. The LLM was returning incomplete/null values
3. No fallback extraction mechanism existed
4. The recruitment pipeline had no intelligent resume parsing

SOLUTION IMPLEMENTED:
1. Integrated CandidateExtractionService (our intelligent parser) into recruitment_routes.py
2. Updated bulk_upload_resumes() to use CandidateExtractionService first
3. Falls back to LLM parse_resume() if extraction returns empty
4. Added helper function to parse experience years from extracted text
5. Stores extracted data properly in database

FILE CHANGES:
/src/api/recruitment_routes.py:
  - Added import: from src.application.candidate_extraction_service import CandidateExtractionService
  - Added service initialization: _candidate_extraction_service and get_candidate_extraction_service()
  - Modified bulk_upload_resumes():
    * Calls extraction_service.extract_candidate_details() first
    * Falls back to LLM parsing if extraction returns empty
    * Properly converts CandidateDetail to database format
    * Stores candidate_name, experience_years, education, current_role
  - Added helper: _parse_years_from_string() to parse "10+ years" -> 10.0

FLOW CHANGE:
BEFORE:
  Resume uploaded -> Raw text extracted -> LLM parse_resume() -> [mostly null values] -> Database

AFTER:
  Resume uploaded -> Raw text extracted -> CandidateExtractionService (intelligent) 
    ✓ Extracts name from headers/content (not field labels)
    ✓ Parses experience from multiple patterns
    ✓ Identifies education, skills, projects
    -> Fallback: LLM parse_resume() if needed
    -> [Actual candidate data] -> Database

EXPECTED RESULT:
Next time you call:
  GET /api/v1/recruitment/jd/2/candidates

You should see:
{
  "candidate_name": "MILIND DESHMUKH",
  "email": null,
  "phone": null,
  "skills": [],
  "experience_years": 10.0,
  "education": "B.Tech in Computer Science",
  "current_role": "Solution Architect",
  "status": "parsed",
  "summary": "Experienced architect with 10+ years in system design..."
  ...
}

BENEFITS:
✓ Intelligent resume parsing (understands resume structure)
✓ Works even when LLM fails
✓ Extracts names correctly (doesn't search for "Name:" label)
✓ Parses experience from multiple formats
✓ Proper fallback mechanism
✓ Reuses our proven CandidateExtractionService

TO TEST:
1. Re-upload the resume (MILIND_SA_2026.pdf) to JD 2
2. Check the response - should now have candidate_name, experience_years, etc.
3. Verify the /api/v1/recruitment/jd/2/candidates endpoint returns populated fields
"""

print(__doc__)

# Show code changes
print("\n" + "="*80)
print("KEY CODE CHANGES")
print("="*80 + "\n")

print("""
1. IMPORT ADDITION:
   from src.application.candidate_extraction_service import CandidateExtractionService

2. SERVICE INITIALIZATION:
   def get_candidate_extraction_service() -> CandidateExtractionService:
       global _candidate_extraction_service
       if _candidate_extraction_service is None:
           _candidate_extraction_service = CandidateExtractionService()
       return _candidate_extraction_service

3. IN bulk_upload_resumes():
   extraction_service = get_candidate_extraction_service()
   
   # Use intelligent extraction first
   candidate_detail = extraction_service.extract_candidate_details(
       content=raw_text,
       domain=None,
   )
   
   # Fallback to LLM if extraction returns empty
   if not candidate_detail or not candidate_detail.name:
       parsed = await ai.parse_resume(raw_text)
   else:
       # Convert extracted data to database format
       parsed = {
           "candidate_name": candidate_detail.name,
           "experience_years": _parse_years_from_string(candidate_detail.total_experience),
           "education": candidate_detail.additional_details.get("education") if candidate_detail.additional_details else None,
           "current_role": candidate_detail.additional_details.get("current_role") if candidate_detail.additional_details else None,
           ...
       }

4. HELPER FUNCTION:
   def _parse_years_from_string(exp_string: str) -> Optional[float]:
       # Parses "10+ years" -> 10.0
       # Parses "8-10 years" -> 8.0
       match = re.search(r'(\\d+(?:\\.\\d+)?)', exp_string)
       return float(match.group(1)) if match else None
""")

print("\n" + "="*80)
print("NEXT STEPS")
print("="*80 + "\n")

print("""
1. Test endpoint with re-uploaded resume:
   POST /api/v1/recruitment/resume/bulk-upload
   Form data:
     - jd_id: 2
     - file: MILIND_SA_2026.pdf
     - user_id: 1

2. Verify extraction results:
   GET /api/v1/recruitment/jd/2/candidates?shortlisted_only=false
   
   Check response has:
     ✓ candidate_name (not null)
     ✓ experience_years (not null)
     ✓ education (if present in resume)
     ✓ current_role (if present in resume)
     ✓ status: "parsed"

3. The matching/scoring will work better now with actual candidate data
""")
