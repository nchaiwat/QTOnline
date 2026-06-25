"""
Auto-fix script for notifications table schema
Run: docker-compose exec app python fix_notifications.py
"""
from app import app, db
from sqlalchemy import text

def fix_notifications_table():
    with app.app_context():
        try:
            print("🔧 Fixing notifications table schema...")
            
            # Drop old table
            db.session.execute(text('DROP TABLE IF EXISTS notifications CASCADE'))
            print("  ✓ Dropped old table")
            
            # Create new table with correct schema
            db.session.execute(text('''
                CREATE TABLE notifications (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    text VARCHAR(255) NOT NULL,
                    link_id INTEGER,
                    is_read BOOLEAN DEFAULT FALSE,
                    created TIMESTAMP WITHOUT TIME ZONE NOT NULL
                )
            '''))
            print("  ✓ Created new table")
            
            db.session.commit()
            print("✅ SUCCESS: Notifications table fixed!")
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = fix_notifications_table()
    exit(0 if success else 1)
