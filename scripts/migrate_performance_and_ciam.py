import os
import sys
import secrets

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import app
from extensions import db
from models import CiamSetting, CiamAuditLog, LoginLog
from sqlalchemy import text

def run_migration():
    print("Starting Performance and CIAM Migration...")
    with app.app_context():
        # 1. Create any missing tables (ciam_settings, ciam_audit_logs, login_logs)
        print("Creating new tables if not exists...")
        db.create_all()
        print("Tables checked/created successfully.")

        # 2. Add performance indexes on purchase_orders, customers, and products
        indexes = [
            ("idx_po_sale_user_id", 'CREATE INDEX IF NOT EXISTS idx_po_sale_user_id ON purchase_orders(sale_user_id);'),
            ("idx_po_status", 'CREATE INDEX IF NOT EXISTS idx_po_status ON purchase_orders(status);'),
            ("idx_po_created", 'CREATE INDEX IF NOT EXISTS idx_po_created ON purchase_orders(created);'),
            ("idx_po_updated_at", 'CREATE INDEX IF NOT EXISTS idx_po_updated_at ON purchase_orders("updatedAt");'),
            ("idx_po_sale_created", 'CREATE INDEX IF NOT EXISTS idx_po_sale_created ON purchase_orders(sale_user_id, created);'),
            ("idx_customers_inactive_id", 'CREATE INDEX IF NOT EXISTS idx_customers_inactive_id ON customers(inactive, id);'),
            ("idx_customers_code", 'CREATE INDEX IF NOT EXISTS idx_customers_code ON customers("customerCode");'),
            ("idx_customers_name", 'CREATE INDEX IF NOT EXISTS idx_customers_name ON customers(name);'),
            ("idx_customers_phone", 'CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(telephone1);'),
            ("idx_products_inactive_code", 'CREATE INDEX IF NOT EXISTS idx_products_inactive_code ON products(inactive, "productCode");'),
        ]

        print("Checking/creating performance indexes on purchase_orders, customers, products...")
        for name, sql in indexes:
            try:
                db.session.execute(text(sql))
                print(f"  - Index {name}: OK")
            except Exception as e:
                print(f"  - Index {name} warning: {e}")
        db.session.commit()

        # Refresh database optimizer statistics
        print("Refreshing PostgreSQL query planner statistics (ANALYZE)...")
        try:
            db.session.execute(text("ANALYZE purchase_orders; ANALYZE customers; ANALYZE products; ANALYZE users;"))
            db.session.commit()
            print("  - Database statistics updated successfully.")
        except Exception as e:
            print(f"  - ANALYZE warning: {e}")

        # 3. Seed default CIAM settings if empty
        setting = CiamSetting.query.first()
        if not setting:
            random_token = secrets.token_hex(16)
            api_key = f"sec_po_mgmt_{random_token}"
            new_setting = CiamSetting(
                is_enabled=True,
                api_key=api_key,
                allowed_ips="157.173.219.153, 192.168.12.11, 127.0.0.1",
                default_role="Sale"
            )
            db.session.add(new_setting)
            db.session.commit()
            print(f"Seeded default CIAM settings with API Key: {api_key}")
        else:
            print(f"CIAM settings already exist. API Key is configured.")

    print("Migration completed successfully!")

if __name__ == "__main__":
    run_migration()
