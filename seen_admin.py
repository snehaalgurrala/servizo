# seed_admin.py
from helpers import get_db_connection, hash_password
conn = get_db_connection()
cur = conn.cursor()
name = "Gurrala Venkata Snehaal"
email = "snehaalgv@gmail.com"
password = "Snehaal@123"
hashed = hash_password(password)
cur.execute("INSERT INTO admins (name, email, password) VALUES (%s,%s,%s)", (name,email,hashed))
conn.commit()
cur.close(); conn.close()
print("Admin created.")
