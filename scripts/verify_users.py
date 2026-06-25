from app import app, db, User, bcrypt

def verify():
    with app.app_context():
        print("--- Checking Users in Database ---")
        users = User.query.all()
        if not users:
            print("No users found! Please run 'flask init-db' again.")
            return

        for u in users:
            # ทดสอบเช็ครหัสผ่าน (สมมติว่ารหัสผ่านเหมือน username ตามที่ seed ไว้)
            is_pass_ok = bcrypt.check_password_hash(u.password, u.username.replace('_', ''))
            if u.username == 'sale_admin': # พิเศษสำหรับ sale_admin ที่ใช้รหัส saleadmin
                is_pass_ok = bcrypt.check_password_hash(u.password, 'saleadmin')
                
            print(f"Username: {u.username} | Role: {u.role} | Status: {u.status} | Password OK: {is_pass_ok}")

if __name__ == "__main__":
    verify()
