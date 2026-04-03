# Query Augmentation: Solving Definition Search Problem

## The Problem

**What was happening (WRONG):**
```
User Query: "find architect"
    ↓
System searches for: "architect" (literally)
    ↓
Vector DB finds: Any document mentioning "architect"
    ↓
Retrieved matches:
  1. "An architect is a professional who designs..."  ← Definition!
  2. "...under the architect's leadership..."
  3. "...architect-level decisions..."
    ↓
Result: Definition of architect, not actual architects!
```

**Why?** The vector database retrieves documents with the highest semantic similarity to "architect". If your uploaded documents contain definitions or mentions of the word, it returns those matches instead of candidates with architect experience.

---

## The Solution: Query Augmentation

**What happens now (CORRECT):**
```
User Query: "find architect"
    ↓
Query Augmentation Service:
  - Detects domain: "architect"
  - Augments query with actual responsibilities
    ↓
Augmented Query: "find architect (designed systems OR architected infrastructure 
                   OR system design) (microservices OR distributed systems OR ...)"
    ↓
System searches for: These specific skills/responsibilities
    ↓
Vector DB finds: Candidates who actually:
  - Designed systems
  - Architected infrastructure
  - Led technical architecture
  - Worked with microservices
    ↓
Result: Actual candidate resumes with relevant experience!
```

---

## How It Works

### 1. Domain Detection
When user queries for a role/skill, the system recognizes the domain:
- "architect" → Architect domain
- "python" → Python Developer domain
- "react" → React Developer domain
- "devops" → DevOps domain
- "data scientist" → Data Scientist domain

### 2. Query Expansion
For each domain, predefined skills and responsibilities are added:

```python
DOMAIN_SKILLS = {
    'architect': {
        'responsibilities': [
            'designed systems',
            'architected infrastructure',
            'system design',
            'led architecture',
            'architecture design',
            ...
        ],
        'technologies': [
            'microservices',
            'distributed systems',
            'scalable architecture',
            'cloud infrastructure',
            ...
        ],
        'keywords': ['architect', 'architecture', 'designed', 'led', 'infrastructure']
    },
    # More domains...
}
```

### 3. Augmented Query Format
Original: `"find architect"`
Augmented: `"find architect (designed systems OR architected infrastructure OR ...) (microservices OR distributed systems OR ...)"`

This tells the vector database to search for:
- Documents mentioning architect AND
- (Specific architectural responsibilities OR specific technologies)

---

## Example Flow

### User Query: "find architect candidate Get names + details + answers back"

**Step 1: Query Cleaning**
```
Input:  "find architect candidate Get names + details + answers back"
Output: "find architect candidate"
(Removes UI instructions like "Get names + details + answers back")
```

**Step 2: Query Augmentation**
```
Input:  "find architect candidate"
Output: "find architect candidate (designed systems OR architected infrastructure 
         OR system design) (microservices OR distributed systems OR scalable architecture)"
         
Domain detected: architect
Skills added: design, architecture, microservices, distributed systems
```

**Step 3: Vector DB Search**
```
Search for: Augmented query
Result: Candidates with actual architecture experience
  - Name: John Smith
    Experience: "Designed microservices architecture for e-commerce platform"
  - Name: Jane Doe
    Experience: "Led infrastructure design for cloud migration"
```

**Step 4: Candidate Extraction**
```
From retrieved documents:
- Extract: Names, experience, projects, skills
- Return: Structured candidate details
```

---

## Key Benefits

1. **Skill-Based Search**: Instead of searching for keyword "architect", search for actual architect skills
2. **Better Matching**: Finds candidates who actually DO the work, not just mention the title
3. **Contextual Understanding**: System understands what each role involves
4. **Flexible Expansion**: Easy to add new domains and skills
5. **Works with Messy Queries**: Handles user instructions mixed with actual query

---

## Supported Domains

The system currently augments queries for:
- **architect**: System design, infrastructure, microservices
- **python-developer**: Python, Django, Flask, FastAPI
- **react-developer**: React, JavaScript, Frontend, UI
- **backend-engineer**: APIs, REST, GraphQL, Databases
- **devops**: Kubernetes, Docker, CI/CD, Infrastructure
- **data-scientist**: Machine Learning, Analytics, Python, R

---

## Implementation Details

### Location
- Service: `/src/application/query_augmentation_service.py`
- Integration: `/src/application/orchestration_service.py`

### Flow in Orchestration
```python
# Step 0: Clean query to remove UI instructions
cleaned_query = self._clean_query_for_search(query)

# Step 0.5: Augment query with domain context
augmented_query = query_augmentation_service.augment_query(cleaned_query)

# Step 1+: Use augmented_query for ALL downstream processing
route_decision = await self.query_router.classify_and_route(query=augmented_query)
complexity = await self.query_router.determine_complexity(augmented_query)
result = await self.process_query_request(query=augmented_query, ...)
```

---

## Expected Results

### Before Fix
```
Query: "find architect"
Result: 
  - Definition of architect
  - Mentions of architect in unrelated content
  - Wrong candidates
```

### After Fix
```
Query: "find architect"
Result:
  - John Smith (Designed microservices architecture)
  - Jane Doe (Led infrastructure design)
  - Bob Johnson (Architected cloud migration)
  - Real candidates with relevant experience!
```

---

## How to Test

```bash
# Test query augmentation directly
python test_query_augmentation.py

# Test full pipeline
python -m uvicorn src.api.main:app --reload --port 8000

# Send test query
curl -X POST http://localhost:8000/api/agent/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "find architect candidate",
    "user_id": 1,
    "use_agent_if_complex": false
  }' | jq '.candidates'
```

Expected response:
```json
{
  "candidates": [
    {
      "name": "John Smith",
      "total_experience": "10+ years",
      "relevant_experience": "8+ years in system architecture",
      "summary": "Expert in designing scalable microservices architecture",
      "key_projects": [
        "Designed cloud migration architecture",
        "Led microservices transformation"
      ],
      "relevance_score": 0.92
    },
    ...
  ]
}
```

---

## Summary

The query augmentation service transforms user queries from simple keywords into domain-aware searches that understand what each role actually involves. This ensures that when you ask for an "architect", the system searches for people who actually designed systems and led architecture - not just people mentioned in the same paragraph as the word "architect".

**Result**: Better candidate matching, more relevant results, and structured candidate data returned.
