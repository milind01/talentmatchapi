# Tech Stack Seeding Setup Guide

## Overview

This setup allows you to pre-populate the database with technology stack categories (Java, SAP, ServiceNow, etc.) so your recruitment system can organize and search resumes by department/technology.

---

## Files

| File | Purpose |
|------|---------|
| `seed_data/tech_stacks.json` | Default tech stack definitions (20 IT departments) |
| `seed_tech_stacks.py` | Migration script to load JSON into database |

---

## Quick Start (3 Steps)

### Step 1: Verify JSON is Valid

```bash
python seed_tech_stacks.py --verify
```

**Output Example:**
```
📊 Found 20 tech stacks in JSON
✅ JSON is valid! Tech stacks definition:

  1. Java Backend
     Description: Java-based backend development using Spring Boot...
     Skills: Java, Spring Boot, Spring Framework...

  2. Python Development
     Description: Python-based development including Django, FastAPI...
     Skills: Python, Django, FastAPI...

  ... (18 more tech stacks)
```

### Step 2: Load into Database

```bash
# Load with user_id=1 (default)
python seed_tech_stacks.py

# Or specify different user
python seed_tech_stacks.py --user_id=5

# Or reset existing stacks first
python seed_tech_stacks.py --user_id=1 --reset
```

**Output Example:**
```
✅ Loaded JSON from seed_data/tech_stacks.json
📊 Found 20 tech stacks in JSON

🔗 Connecting to database...
✅ Connected to PostgreSQL

📁 Creating upload directories...
   ✓ uploads/tech_stack/java_backend
   ✓ uploads/tech_stack/python_dev
   ... (18 more directories)

📝 Inserting 20 tech stacks...
   ✓ Java Backend
   ✓ Python Development
   ✓ SAP
   ... (17 more)

✅ Successfully inserted 20/20 tech stacks

============================
✅ SEED COMPLETED SUCCESSFULLY
============================

📚 Next Steps:
   1. Use /api/v1/recruitment/tech-stack to list loaded stacks
   2. Upload resumes via /resume/bulk-upload?tech_stack_id=<id>
   3. Query with tech stack: POST /api/agent/query
```

### Step 3: Verify in Database

```bash
# List all tech stacks
curl http://localhost:8000/api/v1/recruitment/tech-stack

# Get specific tech stack
curl http://localhost:8000/api/v1/recruitment/tech-stack/1
```

---

## Available Tech Stacks (20 Departments)

After seeding, you'll have these categories:

1. **Java Backend** - Spring Boot, microservices, Maven
2. **Python Development** - Django, FastAPI, data analysis
3. **SAP** - ABAP, FIORI, enterprise systems
4. **ServiceNow** - Platform administration, workflows
5. **Mainframe** - COBOL, JCL, legacy systems
6. **Cloud Architecture (AWS)** - EC2, S3, Lambda
7. **Cloud Architecture (Azure)** - VMs, Functions, SQL
8. **React Frontend** - React, TypeScript, component libraries
9. **DevOps & CI/CD** - Jenkins, Docker, Kubernetes
10. **Database Administration** - SQL, MySQL, PostgreSQL, Oracle
11. **Data Engineering** - Spark, Hadoop, Kafka, Airflow
12. **QA & Testing** - Selenium, JUnit, Pytest, automation
13. **Security & Compliance** - SIEM, pentesting, encryption
14. **HR Technology** - Workday, SuccessFactors, payroll
15. **.NET Development** - C#, ASP.NET, Entity Framework
16. **Mobile Development** - iOS, Android, React Native, Flutter
17. **Salesforce** - Apex, Visualforce, Lightning
18. **Business Intelligence** - Tableau, Power BI, Looker
19. **Machine Learning & AI** - TensorFlow, PyTorch, NLP
20. **Network & Infrastructure** - Cisco, firewalls, virtualization

---

## How It Works

### Upload Flow

```
1. Create Tech Stack (API or preloaded from seed)
   ↓
2. Upload Resume with tech_stack_id
   POST /api/v1/recruitment/resume/bulk-upload
   {
     "jd_id": 1,
     "tech_stack_id": 3,      ← Links to "SAP" tech stack
     "file": <resume.pdf>
   }
   ↓
3. Resume Stored with Tech Stack Reference
   Candidate.tech_stack_id = 3
   ChromaDB chunks get {tech_stack_id: 3} in metadata
   ↓
4. Uploaded Folder Structure
   uploads/tech_stack/sap/
   ├── resume_john.pdf
   ├── resume_sarah.pdf
   └── ...
```

### Query Flow

```
1. Agent Query with Tech Stack Filter
   POST /api/agent/query
   {
     "query": "Find candidates with ABAP experience",
     "tech_stack_id": 3,      ← Search ONLY SAP resumes
     "user_id": 1
   }
   ↓
2. Orchestration Applies Filter
   Added to ChromaDB filters: {tech_stack_id: 3}
   ↓
3. Optimized Retrieval
   ChromaDB searches ONLY resumes with tech_stack_id=3
   No unnecessary searches across all resumes
   ↓
4. Results
   Only SAP candidates returned
   Fast, relevant, optimized
```

---

## API Usage Examples

### 1. List All Tech Stacks

```bash
curl -X GET http://localhost:8000/api/v1/recruitment/tech-stack
```

**Response:**
```json
[
  {
    "id": 1,
    "name": "Java Backend",
    "description": "Java-based backend development...",
    "keywords": ["java", "spring", "maven", ...],
    "skills": ["Java", "Spring Boot", ...],
    "upload_dir": "uploads/tech_stack/java_backend",
    "is_active": true,
    "created_at": "2026-04-06T10:00:00"
  },
  ...
]
```

### 2. Get Specific Tech Stack

```bash
curl -X GET http://localhost:8000/api/v1/recruitment/tech-stack/3
```

### 3. Upload Resumes to Tech Stack

```bash
curl -X POST http://localhost:8000/api/v1/recruitment/resume/bulk-upload \
  -F "jd_id=1" \
  -F "user_id=1" \
  -F "tech_stack_id=3" \
  -F "file=@/path/to/resume.pdf"
```

Response:
```json
{
  "jd_id": 1,
  "uploaded": 1,
  "failed": 0,
  "candidates": [
    {
      "id": 5,
      "file_name": "resume.pdf",
      "candidate_name": "John Doe",
      "status": "parsed"
    }
  ]
}
```

### 4. Query by Tech Stack

```bash
curl -X POST http://localhost:8000/api/agent/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Find candidates with ABAP experience",
    "user_id": 1,
    "tech_stack_id": 3
  }'
```

Response:
```json
{
  "status": "success",
  "route": "rag",
  "answer": "Found 3 candidates with ABAP experience...",
  "candidates": [
    {
      "name": "Ravi Kumar",
      "relevant_experience": "8+ years in ABAP",
      "relevance_score": 0.92,
      ...
    }
  ]
}
```

### 5. Get Count by Tech Stack

```bash
curl -X POST http://localhost:8000/api/agent/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How many Java developers do we have?",
    "user_id": 1,
    "tech_stack_id": 1
  }'
```

Response:
```json
{
  "status": "success",
  "route": "analytics",
  "answer": "Found 12 Java developers",
  "metadata": {
    "query_type": "count",
    "count": 12,
    "total": 47
  }
}
```

---

## Customization

### Add New Tech Stack

```bash
curl -X POST http://localhost:8000/api/v1/recruitment/tech-stack \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Oracle Database",
    "description": "Oracle database administration and development",
    "keywords": ["oracle", "plsql", "sql", "dba", "awr"],
    "skills": ["Oracle", "PL/SQL", "Database Tuning", "AWR Reports"],
    "upload_dir": "uploads/tech_stack/oracle_db"
  }'
```

### Modify Existing Stack

Edit `seed_data/tech_stacks.json`, update the entry, then:

```bash
python seed_tech_stacks.py --reset  # Delete old stacks
python seed_tech_stacks.py          # Reload with new data
```

### Delete Tech Stack

```bash
curl -X DELETE http://localhost:8000/api/v1/recruitment/tech-stack/1
```

---

## Troubleshooting

### Issue: "JSON file not found"

**Solution:** Make sure `seed_data/tech_stacks.json` exists in the root directory

```bash
ls -la seed_data/
# Should show: tech_stacks.json
```

### Issue: "Database connection error"

**Solution:** Verify database is running and `.env` has correct `DATABASE_URL`

```bash
# Check .env
cat .env | grep DATABASE_URL

# Should output something like:
# DATABASE_URL=postgresql+asyncpg://user:pass@localhost/talentmatchapi
```

### Issue: "Import error for src modules"

**Solution:** Make sure you're in the project root directory

```bash
pwd
# Should be: /path/to/talentmatchapi

python seed_tech_stacks.py  # Run from here
```

### Issue: Duplicate entries after re-seeding

**Solution:** Use `--reset` flag to delete old data first

```bash
python seed_tech_stacks.py --reset
```

---

## Database Schema

### TechStack Table

```sql
CREATE TABLE tech_stacks (
    id INTEGER PRIMARY KEY,
    owner_id INTEGER NOT NULL REFERENCES users(id),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    keywords JSON,              -- ["java", "spring", ...]
    skills JSON,                -- ["Java", "Spring Boot", ...]
    upload_dir VARCHAR(500),    -- "uploads/tech_stack/java_backend"
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### Candidate-TechStack Relationship

```sql
ALTER TABLE candidates ADD COLUMN tech_stack_id INTEGER 
    REFERENCES tech_stacks(id) ON DELETE SET NULL;
```

---

## Testing the Setup

### 1. Run One-Off Test Query

```bash
# Start API server
python -m uvicorn main:app --reload

# In another terminal, test a query
python -c "
import asyncio
import httpx

async def test():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            'http://localhost:8000/api/agent/query',
            json={
                'query': 'Count Java developers',
                'user_id': 1,
                'tech_stack_id': 1
            }
        )
        print(response.json())

asyncio.run(test())
"
```

### 2. Verify Upload Directories Created

```bash
ls -la uploads/tech_stack/
# Should show 20 directories:
# aws/,  azure/, business_intelligence/, database_admin/, ...
```

### 3. Check Database Records

```bash
# Using psql (if PostgreSQL)
psql talentmatchapi -c "SELECT id, name, is_active FROM tech_stacks LIMIT 5;"

# Output:
#  id |        name         | is_active
# ----+---------------------+-----------
#   1 | Java Backend        | t
#   2 | Python Development  | t
#   3 | SAP                 | t
#   4 | ServiceNow          | t
#   5 | Mainframe           | t
```

---

## FAQ

**Q: Can I modify the JSON after seeding?**

A: Yes, but you must re-seed after changes:
```bash
python seed_tech_stacks.py --reset
```

**Q: What if I want different tech stacks for user 2?**

A: Create them separately:
```bash
# User 1 stacks
python seed_tech_stacks.py --user_id=1

# User 2 stacks (will have different entries)
python seed_tech_stacks.py --user_id=2
```

**Q: Does seeding affect existing resumes?**

A: No. Existing resumes are unaffected. Only new uploads will use the tech stack.

**Q: Can I query across multiple tech stacks?**

A: Not in single query, but you can:
1. Make separate queries with different tech_stack_id values
2. Or omit tech_stack_id to search all stacks

**Q: How do I export the tech stacks list?**

A: Use the API:
```bash
curl http://localhost:8000/api/v1/recruitment/tech-stack > tech_stacks_list.json
```

---

## Next Steps

1. ✅ Run `python seed_tech_stacks.py --verify` to validate JSON
2. ✅ Run `python seed_tech_stacks.py` to load into database
3. ✅ Verify with `curl http://localhost:8000/api/v1/recruitment/tech-stack`
4. ✅ Upload first resume: `POST /api/v1/recruitment/resume/bulk-upload`
5. ✅ Query with tech stack filter: `POST /api/agent/query`

---

## Will It Work?

**YES!** ✅

The tech stack system is fully integrated:

1. ✅ **Database Layer** - TechStack model with FK relationships
2. ✅ **API Layer** - Endpoints to create/list/delete tech stacks
3. ✅ **Upload Layer** - Associates resumes with tech stacks
4. ✅ **Retrieval Layer** - ChromaDB filters by tech_stack_id
5. ✅ **Query Layer** - Agent queries can filter by tech stack

**System handles:**
- Multiple tech stacks ✅
- Separate upload directories ✅
- Category-specific searches ✅
- Dynamic tech stack management ✅
- No hardcoding needed ✅
