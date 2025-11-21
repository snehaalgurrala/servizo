# helpers.py
import mysql.connector
import bcrypt
import base64
import os

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASS", "Snehaal@123"),
        database=os.getenv("DB_NAME", "vcube")
    )

def hash_password(plain_password: str) -> str:
    """Return base64-encoded bcrypt hash (string) ready to store in VARCHAR."""
    hashed = bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt())
    return base64.b64encode(hashed).decode('utf-8')

def check_password(plain_password: str, hashed_base64: str) -> bool:
    """Verify plain password against base64-encoded bcrypt hash from DB."""
    try:
        hashed_bytes = base64.b64decode(hashed_base64)
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_bytes)
    except Exception:
        return False
