
import os
from sqlalchemy import text
from app import app, db

def drop_unused_columns():
    with app.app_context():
        try:
            with db.engine.connect() as conn:
                drop_statements = [
                    # Customers Table
                    'ALTER TABLE customers DROP COLUMN IF EXISTS "billToBlock";',
                    'ALTER TABLE customers DROP COLUMN IF EXISTS "billToStreetNo";',
                    'ALTER TABLE customers DROP COLUMN IF EXISTS "shipToBlock";',
                    'ALTER TABLE customers DROP COLUMN IF EXISTS "shipToStreetNo";',
                    'ALTER TABLE customers DROP COLUMN IF EXISTS "globalLocationNumber";',

                    # Products Table
                    'ALTER TABLE products DROP COLUMN IF EXISTS "valuationMethod";',
                    'ALTER TABLE products DROP COLUMN IF EXISTS "procurementMethod";',
                    'ALTER TABLE products DROP COLUMN IF EXISTS "planningMethod";',
                    'ALTER TABLE products DROP COLUMN IF EXISTS "glAccountPickMethod";',
                    'ALTER TABLE products DROP COLUMN IF EXISTS "setGlAccountsBy";',
                    'ALTER TABLE products DROP COLUMN IF EXISTS "assetClass";',
                    'ALTER TABLE products DROP COLUMN IF EXISTS "assetGroup";',
                    'ALTER TABLE products DROP COLUMN IF EXISTS "expenseAccount";',
                    'ALTER TABLE products DROP COLUMN IF EXISTS "revenueAccount";',
                    'ALTER TABLE products DROP COLUMN IF EXISTS "expenseAccountLocal";',
                    'ALTER TABLE products DROP COLUMN IF EXISTS "revenueAccountLocal";',
                    'ALTER TABLE products DROP COLUMN IF EXISTS "customsGroup";',
                    'ALTER TABLE products DROP COLUMN IF EXISTS "ownedByCompany";',

                    # PurchaseOrders Table (Redundant snake_case)
                    'ALTER TABLE purchase_orders DROP COLUMN IF EXISTS "customer_location_file";',
                    'ALTER TABLE purchase_orders DROP COLUMN IF EXISTS "customer_location_file_url";',
                    'ALTER TABLE purchase_orders DROP COLUMN IF EXISTS "customer_location_uploaded_at";',
                    'ALTER TABLE purchase_orders DROP COLUMN IF EXISTS "customer_location_uploaded_by";',
                    'ALTER TABLE purchase_orders DROP COLUMN IF EXISTS "customer_po_file";',
                    'ALTER TABLE purchase_orders DROP COLUMN IF EXISTS "customer_po_file_url";',
                    'ALTER TABLE purchase_orders DROP COLUMN IF EXISTS "customer_po_uploaded_at";',
                    'ALTER TABLE purchase_orders DROP COLUMN IF EXISTS "customer_po_uploaded_by";'
                ]
                
                print("Starting cleanup of unused/redundant columns...")
                for stmt in drop_statements:
                    try:
                        conn.execute(text(stmt))
                        print(f"Executed: {stmt}")
                    except Exception as inner_e:
                        print(f"Error executing {stmt}: {inner_e}")
                
                conn.commit()
                print("\nSUCCESS: Database cleanup completed.")
                
        except Exception as e:
            print(f"CRITICAL ERROR during cleanup: {e}")

if __name__ == "__main__":
    drop_unused_columns()
