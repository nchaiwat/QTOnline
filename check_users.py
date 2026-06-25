from app import app, db
from models import User
import json

with app.app_context():
    count = User.query.count()
    users = [u.to_dict() for u in User.query.all()]
    print(json.dumps({"count": count, "users": users}, indent=2))
