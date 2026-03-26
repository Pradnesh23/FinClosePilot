import sqlite3
from passlib.context import CryptContext
from datetime import datetime
import os

# Database path
DB_PATH = "d:/Projects/Personal/FinClosePilot/data/finclosepilot.db"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def create_demo_users():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Ensure users table exists with manager_id
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN manager_id INTEGER REFERENCES users(id)")
    except Exception:
        pass

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'EMPLOYEE',
            manager_id INTEGER REFERENCES users(id),
            created_at TEXT NOT NULL,
            last_login TEXT
        )
    """)
    
    try:
        # 1. Create/Update Manager
        manager_pwd = get_password_hash("password123")
        cursor.execute(
            """
            INSERT OR REPLACE INTO users (username, email, password_hash, role, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("manager_demo", "manager@finclose.ai", manager_pwd, "MANAGER", datetime.utcnow().isoformat())
        )
        
        # 2. Get Manager ID
        cursor.execute("SELECT id FROM users WHERE username = 'manager_demo'")
        manager_id = cursor.fetchone()[0]
        
        # 3. Create/Update Employee linked to Manager
        employee_pwd = get_password_hash("password123")
        cursor.execute(
            """
            INSERT OR REPLACE INTO users (username, email, password_hash, role, manager_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("employee_demo", "employee@finclose.ai", employee_pwd, "EMPLOYEE", manager_id, datetime.utcnow().isoformat())
        )
        conn.commit()
        print("Demo users created successfully.")
    except Exception as e:
        print(f"Error creating demo users: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    if not os.path.exists(os.path.dirname(DB_PATH)):
        os.makedirs(os.path.dirname(DB_PATH))
    create_demo_users()
