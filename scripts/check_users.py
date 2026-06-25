from app import app, db, User

with app.app_context():
    users = User.query.all()
    print(f"{'ID':<5} {'Username':<15} {'Role':<15} {'Target':<15}")
    print("-" * 50)
    for u in users:
        print(f"{u.id:<5} {u.username:<15} {u.role:<15} {u.targetAmount}")
