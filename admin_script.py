#!/usr/bin/env python3
"""
Admin script to delete all attendance records from the database.

Usage:
    python admin_script.py

This script will:
1. Connect to the database
2. Count the total number of attendance records
3. Ask for confirmation before deletion
4. Delete all attendance records if confirmed
5. Report the number of records deleted
"""

import sys
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Attendance
from dotenv import load_dotenv

load_dotenv()


def delete_all_attendance():
    """Delete all attendance records from the database."""
    db: Session = SessionLocal()
    try:
        # Count existing attendance records
        attendance_count = db.query(Attendance).count()
        
        if attendance_count == 0:
            print("No attendance records found in the database.")
            return
        
        print(f"Found {attendance_count} attendance record(s) in the database.")
        print("\n⚠️  WARNING: This action is irreversible!")
        
        # Ask for confirmation
        confirmation = input(f"\nAre you sure you want to delete all {attendance_count} attendance record(s)? (yes/no): ").strip().lower()
        
        if confirmation != 'yes':
            print("Operation cancelled. No records were deleted.")
            return
        
        # Delete all attendance records
        deleted_count = db.query(Attendance).delete()
        db.commit()
        
        print(f"\n✓ Successfully deleted {deleted_count} attendance record(s) from the database.")
        
    except Exception as e:
        db.rollback()
        print(f"\n✗ Error deleting attendance records: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    delete_all_attendance()
