import os
import sys

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import app
from extensions import db
from models import SystemSetting, TransactionLog, User, CiamSetting
from utils_ciam import init_default_ciam_settings
from sqlalchemy import text

def run_migration():
    print("=" * 60)
    print("Starting CIAM Spec v2.7.0 Enterprise Database Migration...")
    print("=" * 60)

    with app.app_context():
        # 1. Ensure new tables system_settings and transaction_logs exist
        print("1. Creating system_settings and transaction_logs tables...")
        db.create_all()
        print("   -> Tables checked/created successfully.")

        # 2. Add use_ad_auth column to users table if missing
        print("2. Checking/adding 'use_ad_auth' column to 'users' table...")
        try:
            db.session.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS use_ad_auth BOOLEAN DEFAULT TRUE;"))
            db.session.commit()
            print("   -> Column 'use_ad_auth' verified/added.")
        except Exception as e:
            print(f"   -> Column check notice: {e}")
            db.session.rollback()

        # 3. Add indexes on system_settings and transaction_logs
        print("3. Checking indexes for system_settings and transaction_logs...")
        indexes = [
            ("idx_system_settings_key", "CREATE INDEX IF NOT EXISTS idx_system_settings_key ON system_settings(key);"),
            ("idx_system_settings_category", "CREATE INDEX IF NOT EXISTS idx_system_settings_category ON system_settings(category);"),
            ("idx_trans_logs_category", "CREATE INDEX IF NOT EXISTS idx_trans_logs_category ON transaction_logs(category);"),
            ("idx_trans_logs_created_at", "CREATE INDEX IF NOT EXISTS idx_trans_logs_created_at ON transaction_logs(created_at DESC);"),
        ]
        for name, sql in indexes:
            try:
                db.session.execute(text(sql))
                print(f"   -> Index {name}: OK")
            except Exception as e:
                print(f"   -> Index {name} notice: {e}")
                db.session.rollback()
        db.session.commit()

        # 4. Initialize default CIAM settings
        print("4. Initializing default Central IAM runtime parameters...")
        init_default_ciam_settings()
        print("   -> Central IAM runtime settings initialized.")

        # 5. Log migration milestone to transaction_logs
        TransactionLog.log(
            category="system_setting",
            action="migration_v2_7",
            status="success",
            message="Database migration for CIAM Enterprise Specification v2.7.0 completed successfully.",
            triggered_by="system:migration_script",
        )
        print("5. Recorded migration event in transaction_logs.")

    print("=" * 60)
    print("CIAM v2.7.0 Migration completed successfully!")
    print("=" * 60)

if __name__ == "__main__":
    run_migration()
