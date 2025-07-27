#!/usr/bin/env python
"""
Check database schema for permission tables
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Disable Claude AI during initialization
os.environ['SKIP_CLAUDE_AI'] = 'true'

from app import create_app, db

def check_schema():
    """Check the actual database schema"""
    app = create_app()
    
    with app.app_context():
        # Check if permission_category table exists and its columns
        result = db.session.execute(db.text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'permission_category'
            ORDER BY ordinal_position;
        """))
        
        print("📊 Columns in permission_category table:")
        for row in result:
            print(f"   - {row[0]}: {row[1]} (nullable: {row[2]})")
        
        # Check if there are any rows
        count_result = db.session.execute(db.text("SELECT COUNT(*) FROM permission_category"))
        count = count_result.scalar()
        print(f"\n📈 Total rows: {count}")
        
        # If there are rows, show them
        if count > 0:
            rows = db.session.execute(db.text("SELECT * FROM permission_category LIMIT 5"))
            print("\n📋 Sample data:")
            for row in rows:
                print(f"   {row}")

if __name__ == "__main__":
    check_schema()