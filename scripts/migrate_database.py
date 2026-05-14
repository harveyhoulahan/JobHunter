#!/usr/bin/env python3
"""
Database Migration Script
Adds new application tracking columns to existing database
"""
import sqlite3
import os
from datetime import datetime

DB_PATH = "src/data/jobhunter.db"

def migrate_database():
    """Add new columns to existing jobs table"""
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}")
        return False
    
    print(f"🔄 Migrating database: {DB_PATH}")
    print(f"   Backup will be created at: {DB_PATH}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    
    # Create backup
    backup_path = f"{DB_PATH}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    import shutil
    shutil.copy2(DB_PATH, backup_path)
    print(f"✓ Backup created: {backup_path}")
    
    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get existing columns
    cursor.execute("PRAGMA table_info(jobs)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    print(f"\n📋 Existing columns: {len(existing_columns)}")
    
    # Define new columns to add
    new_columns = [
        ("applied_date", "DATETIME"),
        ("rejected_reason", "VARCHAR(50)"),
        ("cv_version", "VARCHAR(100)"),
        ("cover_letter_version", "VARCHAR(100)"),
        ("application_method", "VARCHAR(50)"),
        ("status", "VARCHAR(50)"),
        ("interview_rounds", "TEXT"),  # JSON
        ("offer_details", "TEXT"),     # JSON
    ]
    
    # Add missing columns
    added = 0
    for col_name, col_type in new_columns:
        if col_name not in existing_columns:
            try:
                sql = f"ALTER TABLE jobs ADD COLUMN {col_name} {col_type}"
                cursor.execute(sql)
                print(f"✓ Added column: {col_name} ({col_type})")
                added += 1
            except sqlite3.OperationalError as e:
                print(f"⚠ Failed to add {col_name}: {e}")
        else:
            print(f"  Column already exists: {col_name}")
    
    # Commit changes
    conn.commit()
    
    # Verify new schema
    cursor.execute("PRAGMA table_info(jobs)")
    all_columns = [row[1] for row in cursor.fetchall()]
    print(f"\n✓ Database now has {len(all_columns)} columns")
    print(f"✓ Added {added} new columns")
    
    # Show some stats
    cursor.execute("SELECT COUNT(*) FROM jobs")
    job_count = cursor.fetchone()[0]
    print(f"\n📊 Database contains {job_count} jobs")
    
    if job_count > 0:
        # Set default status for existing jobs
        cursor.execute("UPDATE jobs SET status = 'new' WHERE status IS NULL")
        updated = cursor.rowcount
        if updated > 0:
            print(f"✓ Set default status='new' for {updated} existing jobs")
        conn.commit()
    
    conn.close()
    
    print("\n✅ Migration complete!")
    print(f"   Backup saved at: {backup_path}")
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("JobHunter Database Migration")
    print("=" * 60)
    print()
    
    success = migrate_database()
    
    if success:
        print("\n🎉 You can now run: python3 test_optimized.py")
    else:
        print("\n❌ Migration failed. Check the error messages above.")
