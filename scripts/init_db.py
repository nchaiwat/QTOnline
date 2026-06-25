from app import app, db, User
from flask_bcrypt import Bcrypt
import sys
import time
from sqlalchemy import text

bcrypt = Bcrypt(app)

def init_database():
    print("--- Starting Database Initialization ---")
    
    # รอให้ Database พร้อมจริงๆ (Retry logic)
    retries = 5
    while retries > 0:
        try:
            with app.app_context():
                # 1. Force drop everything using SQL (More robust than db.drop_all for broken schemas)
                print("1. Dropping all tables (Clean Slate)...")
                try:
                    # บังคับล้าง Schema public ทิ้งแล้วสร้างใหม่
                    db.session.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
                    db.session.commit()
                    print("   Schema reset successful.")
                except Exception as e:
                    print(f"   Warning: Schema reset failed ({e}), trying db.drop_all()...")
                    db.drop_all()
                
                # 2. Create tables
                print("2. Creating all tables...")
                db.create_all()
                print("--- Database Tables Created ---")

                # 3. Create Users
                print("3. Creating default users...")
                
                if not User.query.filter_by(username='admin').first():
                    hashed_password_admin = bcrypt.generate_password_hash('admin').decode('utf-8')
                    admin = User(
                        username='admin',
                        password=hashed_password_admin,
                        role='Administrator',
                        fullName='System Administrator'
                    )
                    db.session.add(admin)

                if not User.query.filter_by(username='sale').first():
                    hashed_password_sale = bcrypt.generate_password_hash('sale').decode('utf-8')
                    sale = User(
                        username='sale',
                        password=hashed_password_sale,
                        role='Sale',
                        fullName='Sale Representative 1',
                        target_amount=300000
                    )
                    db.session.add(sale)

                db.session.commit()
                
                print("--- SUCCESS: Default Users Created ---")
                print("   User: admin / Pass: admin")
                print("   User: sale  / Pass: sale")
                return # จบการทำงานเมื่อสำเร็จ

        except Exception as e:
            print(f"!!! Database connection/init failed: {e}")
            retries -= 1
            print(f"Retrying in 5 seconds... ({retries} attempts left)")
            time.sleep(5)
    
    print("!!! Failed to initialize database after multiple attempts.")
    sys.exit(1)

if __name__ == '__main__':
    init_database()
