import subprocess
import sys
from app import app, db

def run_psql_cmd(sql):
    cmd = ['sudo', '-u', 'postgres', 'psql', '-c', sql]
    return subprocess.run(cmd, capture_output=True, text=True)

def setup():
    print("--- Starting Database Setup ---")
    
    # 1. Create Database and User
    commands = [
        "CREATE DATABASE po_online_db;",
        "CREATE USER WAUser WITH PASSWORD 'Wa@!0302$';",
        "GRANT ALL PRIVILEGES ON DATABASE po_online_db TO WAUser;",
        "ALTER DATABASE po_online_db OWNER TO WAUser;"
    ]
    
    for cmd in commands:
        res = run_psql_cmd(cmd)
        if res.returncode == 0:
            print(f"Success: {cmd}")
        else:
            print(f"Note: {res.stderr.strip()}")

    # 2. Initialize Tables
    print("\n--- Creating Tables ---")
    try:
        with app.app_context():
            db.create_all()
        print("Success: All tables created in po_online_db")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    setup()
