#!/usr/bin/env python
"""Debug database connection and verify documents are being stored."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

async def main():
    print("🔍 Database Debug Check\n")
    
    try:
        from src.core.database import async_engine, AsyncSessionLocal, init_db
        from src.data.models import Document
        from src.core.config import settings
        from sqlalchemy import select, func
        
        print(f"📍 Database URL: {settings.database_url}")
        print()
        
        # Initialize database
        print("1️⃣  Initializing database tables...")
        await init_db()
        print("   ✅ Tables created\n")
        
        # Test connection
        print("2️⃣  Testing database connection...")
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(func.count(Document.id)))
            count = result.scalar()
            print(f"   ✅ Connected! Document count: {count}\n")
        
        # List all documents
        print("3️⃣  Fetching all documents...")
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Document))
            docs = result.scalars().all()
            
            if docs:
                print(f"   Found {len(docs)} documents:")
                for doc in docs:
                    print(f"      - ID: {doc.id}, Title: {doc.title}, Status: {doc.status}")
            else:
                print("   No documents found")
        
        print("\n✅ Database check complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
