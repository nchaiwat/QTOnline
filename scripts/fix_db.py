from app import app, db, PurchaseOrder
from sqlalchemy import text
import uuid

def update_schema():
    with app.app_context():
        print("Updating database schema...")
        
        # Helper to run single command
        def run_command(cmd, description):
            with db.engine.connect() as conn:
                trans = conn.begin()
                try:
                    conn.execute(text(cmd))
                    trans.commit()
                    print(f"- Success: {description}")
                except Exception as e:
                    trans.rollback()
                    # print(f"- Skipped (probably exists): {description} | Error: {e}")
                    print(f"- Skipped: {description}")

        # PO Table
        run_command('ALTER TABLE purchase_orders ADD COLUMN "accessToken" VARCHAR(36)', "Add accessToken")
        run_command('ALTER TABLE purchase_orders ADD COLUMN "signatureImage" VARCHAR(500)', "Add signatureImage")
        run_command('ALTER TABLE purchase_orders ADD COLUMN "signedAt" TIMESTAMP WITHOUT TIME ZONE', "Add signedAt")

        # Users Table
        run_command('ALTER TABLE users ADD COLUMN "signatureImage" VARCHAR(500)', "Add users.signatureImage")
        run_command('ALTER TABLE users ADD COLUMN "createdAt" TIMESTAMP WITHOUT TIME ZONE', "Add users.createdAt")
        run_command('ALTER TABLE users ADD COLUMN "lastLogin" TIMESTAMP WITHOUT TIME ZONE', "Add users.lastLogin")
        
        # 2. Generate Access Tokens for existing POs
        print("Generating access tokens for existing POs...")
        try:
            pos = PurchaseOrder.query.filter(PurchaseOrder.accessToken == None).all()
            count = 0
            for po in pos:
                po.accessToken = str(uuid.uuid4())
                count += 1
            
            db.session.commit()
            print(f"Updated {count} POs with new access tokens.")
        except Exception as e:
            db.session.rollback()
            print(f"Error generating tokens: {e}")

        # Drop and recreate notifications table
        db.session.execute(db.text('DROP TABLE IF EXISTS notifications CASCADE'))
        db.session.execute(db.text('''
            CREATE TABLE notifications (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                text VARCHAR(255) NOT NULL,
                link_id INTEGER,
                is_read BOOLEAN DEFAULT FALSE,
                created TIMESTAMP WITHOUT TIME ZONE NOT NULL
            )
        '''))
        db.session.commit()
        print("✓ Table 'notifications' created successfully!")

if __name__ == "__main__":
    update_schema()
