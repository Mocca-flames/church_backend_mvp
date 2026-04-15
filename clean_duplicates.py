import sys

sys.path.append("/app")

from app.database import SessionLocal
from app.models import Attendance
from collections import defaultdict

db = SessionLocal()

try:
    attendances = db.query(Attendance).all()
    groups = defaultdict(list)

    for att in attendances:
        key = att.contact_id
        groups[key].append(att)

    duplicates_removed = 0
    for key, atts in groups.items():
        if len(atts) > 1:
            # Sort by service_date desc, keep the latest attendance
            atts.sort(key=lambda x: x.service_date, reverse=True)
            to_delete = atts[1:]
            for att in to_delete:
                db.delete(att)
                duplicates_removed += 1

    db.commit()
    print(f"Duplicates cleaned. Removed {duplicates_removed} duplicate records.")

except Exception as e:
    db.rollback()
    print(f"Error: {e}")

finally:
    db.close()
