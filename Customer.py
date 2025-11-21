from helpers import get_db_connection, hash_password, check_password
from Admin import admin_view_services
from tabulate import tabulate
import mysql.connector
import base64 ,bcrypt

def register_customer():
    conn = get_db_connection()
    cursor = conn.cursor()

    print("\n--- Customer Registration ---")
    name = input("Enter your name: ").strip()
    phone = input("Enter your phone number: ").strip()

    # make sure phone is digits only
    if not phone.isdigit():
        print("❌ Invalid phone number. Digits only.")
        return

    email = input("Enter your email: ").strip()

    # use getpass for hidden password entry
    try:
        password = input("Enter your password: ").strip()
        confirm_password = input("Confirm your password: ").strip()
    except Exception as e:
        print("Error while entering password:", e)
        return

    if password != confirm_password:
        print("❌ Passwords do not match. Please try again.")
        return

    address = input("Enter your address: ").strip()

      # bytes
    hashed_str = hash_password(password)  # store string in DB

    gated_input = input("Do you live in a gated community? (yes/no): ").strip().lower()

    if gated_input == "yes":
        community_type = "gated"
        community_name = input("Enter your community name: ").strip()
        block_or_house = input("Enter your block/house number: ").strip()
    else:
        community_type = "non-gated"
        # Apartment name is optional, can be NULL
        community_name_input = input("Enter your apartment name (optional): ").strip()
        community_name = community_name_input if community_name_input else None
        block_or_house = input("Enter your flat/house number: ").strip()

    try:
        # Insert into MySQL
        cursor.execute("""
                INSERT INTO customers
                (name, email, phone, password, address, community_type, community_name, block_or_house)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (name, email, phone, hashed_str, address, community_type, community_name, block_or_house))

        conn.commit()  # ✅ Very important: commit the transaction

        print(f"✅ Registration successful! You can now log in as {name}.")

    except mysql.connector.Error as err:
        print(f"❌ Error while registering customer: {err}")

    finally:
        cursor.close()
        conn.close()

    print(f"✅ Customer {name} registered successfully!\n")

# Customer Login
def login_customer():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)


    identifier = input("Enter your Email or Phone Number: ").strip()
    password = input("Enter your password: ").strip()

    if "@" in identifier and "." in identifier:
        cursor.execute("SELECT * FROM customers WHERE email=%s", (identifier,))
    else:
        cursor.execute("SELECT * FROM customers WHERE phone=%s", (identifier,))

    row = cursor.fetchone()
    conn.close()

    stored_hash_str = row['password']  # string from DB
    stored_hash_bytes = base64.b64decode(stored_hash_str)

    if bcrypt.checkpw(password.encode('utf-8'), stored_hash_bytes):
        print(f"✅ Login successful! Welcome, {row['name']}.")
        return row
    else:
        print("❌ Invalid email/phone or password.")



#Customer Menu
def customer_menu(customer):
    while True:
        print(f"\n--- Customer Menu ({customer['name']}) ---")
        print("1. View Services")
        print("2. Book Service")
        print("3. View My Orders")
        print("4. Edit Profile")
        print("5. Logout")

        choice = input("Enter your choice: ").strip()
        if choice == "1":
            admin_view_services()
        elif choice == "2":
            book_service(customer)
        elif choice == '3':
            view_my_orders(customer['id'])
        elif choice == "4":
            edit_customer_details(customer)
        elif choice == "5":
            print("Logging out...")
            break
        else:
            print("Invalid choice. Try again.")

#Book Service
def book_service(customer):
    admin_view_services()

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        service_id = int(input("Enter Service ID to book: ").strip())  # ✅ convert to int
    except ValueError:
        print("❌ Invalid service ID.")
        return

    customer_id = customer['id']

    try:
        cursor.execute(
            "INSERT INTO orders (customer_id, service_id) VALUES (%s, %s)",
            (customer_id, service_id)
        )
        conn.commit()
        print("✅ Service booked successfully!")
    except Exception as e:
        print("❌ Error booking service:", e)
    finally:
        cursor.close()
        conn.close()
# View My Orders
def view_my_orders(customer_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
            SELECT o.id AS order_id,
                   o.customer_id,
                   o.service_id,
                   o.order_date,
                   o.status,
                   s.name AS service_name
            FROM orders o
            JOIN services s ON o.service_id = s.id
            WHERE o.customer_id = %s
        """, (customer_id,))
    orders = cursor.fetchall()
    conn.close()

    if orders:
        # Prepare data for tabulate
        table_data = []
        for order in orders:
            table_data.append([
                order['order_id'],
                order['service_name'],
                order['order_date'].strftime("%Y-%m-%d %H:%M:%S"),
                order['status']
            ])

        headers = ["Order ID", "Service", "Order Date", "Status"]
        print("\n--- My Orders ---")
        print(tabulate(table_data, headers=headers, tablefmt="fancy_grid"))
    else:
        print("No orders found.")

#Edit Customer Profile
def edit_customer_details(customer):
    conn = get_db_connection()
    cursor = conn.cursor()

    print("\n--- Edit My Details ---")
    print("1. Update Phone Number")
    print("2. Update Address")
    print("3. Update Password")
    print("4. Go Back")

    choice = input("Enter your choice: ")

    if choice == '1':
        new_phone = input("Enter new phone number: ")
        cursor.execute("UPDATE customers SET phone=%s WHERE id=%s", (new_phone, customer['id']))
        conn.commit()
        print("Phone number updated successfully.")
        customer['phone'] = new_phone  # update local session data

    elif choice == '2':
        new_address = input("Enter new address: ")
        cursor.execute("UPDATE customers SET address=%s WHERE id=%s", (new_address, customer['id']))
        conn.commit()
        print("Address updated successfully.")
        customer['address'] = new_address  # update local session data

    elif choice == '3':
        new_password = input("Enter new password: ")
        cursor.execute("UPDATE customers SET password=%s WHERE id=%s", (new_password, customer['id']))
        conn.commit()
        print("Password updated successfully.")

    elif choice == '4':
        print("Returning to menu...")
    else:
        print("Invalid choice.")

    conn.close()