"""
Migration Script: Seed default technology stacks into the database.

Usage:
    python seed_tech_stacks.py
    
    Optional flags:
    --user_id=1                 User ID to own the tech stacks (default: 1)
    --reset                     Delete existing tech stacks before seeding
    --verify                    Just verify JSON is valid, don't load
"""

import asyncio
import json
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import delete
from src.core.database import AsyncSessionLocal, get_db_url
from src.data.recruitment_models import TechStack


async def load_tech_stacks_from_json(json_file: str) -> list:
    """Load tech stack definitions from JSON file."""
    if not os.path.exists(json_file):
        print(f"❌ Error: JSON file not found: {json_file}")
        return None
    
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        print(f"✅ Loaded JSON from {json_file}")
        return data.get("tech_stacks", [])
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON: {e}")
        return None
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return None


async def seed_tech_stacks(
    json_file: str,
    user_id: int = 1,
    reset: bool = False,
    verify_only: bool = False
):
    """
    Seed technology stacks from JSON into database.
    
    Args:
        json_file: Path to JSON file with tech stack definitions
        user_id: User ID to own the tech stacks
        reset: Delete existing tech stacks before seeding
        verify_only: Just verify JSON, don't load into DB
    """
    # Load JSON
    tech_stacks_data = await load_tech_stacks_from_json(json_file)
    if not tech_stacks_data:
        print("❌ Failed to load JSON data")
        return False
    
    print(f"📊 Found {len(tech_stacks_data)} tech stacks in JSON")
    
    # Verify only?
    if verify_only:
        print("\n✅ JSON is valid! Tech stacks definition:")
        for i, ts in enumerate(tech_stacks_data, 1):
            print(f"\n  {i}. {ts['name']}")
            print(f"     Description: {ts['description']}")
            print(f"     Skills: {', '.join(ts['skills'][:3])}...")
        return True
    
    # Connect to database
    try:
        db_url = get_db_url()
        print(f"🔗 Connecting to database: {db_url[:50]}...")
        
        async with AsyncSessionLocal() as session:
            # Reset if requested
            if reset:
                print(f"🗑️  Deleting existing tech stacks for user {user_id}...")
                await session.execute(
                    delete(TechStack).where(TechStack.owner_id == user_id)
                )
                await session.commit()
                print("✅ Deleted existing tech stacks")
            
            # Create directories
            print("\n📁 Creating upload directories...")
            for ts_data in tech_stacks_data:
                upload_dir = ts_data.get("upload_dir")
                if upload_dir:
                    os.makedirs(upload_dir, exist_ok=True)
                    print(f"   ✓ {upload_dir}")
            
            # Insert tech stacks
            print(f"\n📝 Inserting {len(tech_stacks_data)} tech stacks...")
            inserted = 0
            
            for ts_data in tech_stacks_data:
                try:
                    tech_stack = TechStack(
                        owner_id=user_id,
                        name=ts_data["name"],
                        description=ts_data.get("description"),
                        keywords=ts_data.get("keywords", []),
                        skills=ts_data.get("skills", []),
                        upload_dir=ts_data.get("upload_dir"),
                        is_active=True
                    )
                    session.add(tech_stack)
                    inserted += 1
                    print(f"   ✓ {ts_data['name']}")
                except Exception as e:
                    print(f"   ✗ {ts_data['name']}: {str(e)}")
            
            await session.commit()
            print(f"\n✅ Successfully inserted {inserted}/{len(tech_stacks_data)} tech stacks")
        
        return True
        
    except Exception as e:
        print(f"❌ Database error: {str(e)}")
        return False


def main():
    """Parse arguments and run seed."""
    # Parse arguments
    user_id = 1
    reset = False
    verify_only = False
    json_file = os.path.join(os.path.dirname(__file__), "tech_stacks.json")
    
    for arg in sys.argv[1:]:
        if arg.startswith("--user_id="):
            user_id = int(arg.split("=")[1])
        elif arg == "--reset":
            reset = True
        elif arg == "--verify":
            verify_only = True
        elif arg.startswith("--json="):
            json_file = arg.split("=")[1]
    
    print(f"""
╔═══════════════════════════════════════════════════════════════╗
║         Tech Stack Database Seeder                           ║
╚═══════════════════════════════════════════════════════════════╝

📋 Configuration:
   JSON File: {json_file}
   User ID: {user_id}
   Reset Existing: {reset}
   Verify Only: {verify_only}

""")
    
    # Run async seed
    success = asyncio.run(seed_tech_stacks(
        json_file=json_file,
        user_id=user_id,
        reset=reset,
        verify_only=verify_only
    ))
    
    if success:
        print("\n" + "="*60)
        print("✅ SEED COMPLETED SUCCESSFULLY")
        print("="*60)
        print("\n📚 Next Steps:")
        print("   1. Use /api/v1/recruitment/tech-stack to list loaded stacks")
        print("   2. Upload resumes via /resume/bulk-upload?tech_stack_id=<id>")
        print("   3. Query with tech stack: POST /api/agent/query")
        print("      {\"query\": \"...\", \"tech_stack_id\": <id>}")
        sys.exit(0)
    else:
        print("\n" + "="*60)
        print("❌ SEED FAILED")
        print("="*60)
        sys.exit(1)


if __name__ == "__main__":
    main()
